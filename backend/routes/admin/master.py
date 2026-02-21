from fastapi import APIRouter, Depends, HTTPException
from database import get_supabase
from dependencies import require_master
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from jose import jwt
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/admin/master", tags=["Master Admin"])

class ClientCreate(BaseModel):
    name: str
    email: str
    plan: str = "solo"
    password: str
    whatsapp: Optional[str] = None

class ClientUpdate(BaseModel):
    plan: Optional[str] = None
    active: Optional[bool] = None
    whatsapp: Optional[str] = None

@router.get("/metrics")
def get_master_metrics(user_profile: dict = Depends(require_master)):
    supabase = get_supabase()

    # Fetch active subscriptions for MRR/ARR
    subs_res = supabase.table("subscriptions").select("mrr_cents").eq("status", "active").execute()
    active_subs = subs_res.data or []

    mrr = sum(sub['mrr_cents'] for sub in active_subs) / 100
    arr = mrr * 12

    # Calculate Churn (Cancelled last 30 days / Active 30 days ago)
    # Active 30 days ago approx = current active + cancelled last 30 days - new last 30 days.
    # Simplified: Base = Active + Cancelled (assuming all cancelled were active 30 days ago).
    # Precise formula: cancelled_last_30_days / active_at_start_of_period

    # Fetch cancelled in last 30 days
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

    cancelled_res = supabase.table("subscriptions")\
        .select("id", count="exact")\
        .eq("status", "cancelled")\
        .gte("updated_at", thirty_days_ago)\
        .execute()
    cancelled_count = cancelled_res.count or 0

    # Active count
    active_count = len(active_subs)

    # Base active 30 days ago ~ active_count + cancelled_count (ignoring new subs for simplicity or fetching creation date)
    # Let's use strict formula: cancelled / (active + cancelled)
    base = active_count + cancelled_count
    churn_rate = round((cancelled_count / base) * 100, 2) if base > 0 else 0

    return {
        "mrr": mrr,
        "arr": arr,
        "churn_rate": churn_rate,
        "total_clients": active_count # Active clients paying
    }

@router.get("/clients")
def list_clients(user_profile: dict = Depends(require_master)):
    supabase = get_supabase()
    # Also fetch total leads count per client? Might be heavy.
    # Just basic client list for now.
    return supabase.table("clients").select("*").order("created_at", desc=True).execute().data

@router.post("/clients")
def create_client(client: ClientCreate, user_profile: dict = Depends(require_master)):
    supabase = get_supabase()

    # 0. Check if client already exists (email) in clients table
    existing = supabase.table("clients").select("id").eq("email", client.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Já existe um cliente com esse e-mail")

    # 1. Check if Auth User exists?
    # supabase.auth.admin.create_user will fail if exists.

    # 2. Cria o usuário no Supabase Auth
    user = None
    try:
        auth_res = supabase.auth.admin.create_user({
            "email": client.email,
            "password": client.password,
            "email_confirm": True
        })
        user = auth_res.user if hasattr(auth_res, "user") else auth_res
    except Exception as e:
        logger.error(f"Erro ao criar usuário Auth: {e}")
        # Could be "User already registered" error from GoTrue
        raise HTTPException(status_code=400, detail="Erro ao criar login (Auth). E-mail pode já estar em uso.")

    # 3. Cria o registro do cliente
    new_client = None
    try:
        # Exclude password from DB insert
        client_dict = client.dict()
        del client_dict["password"]

        client_res = supabase.table("clients").insert(client_dict).execute()
        new_client = client_res.data[0]
    except Exception as e:
        logger.error(f"Erro ao criar registro do cliente: {e}")
        # Rollback Auth User
        if user:
            try:
                supabase.auth.admin.delete_user(user.id)
            except:
                pass
        raise HTTPException(status_code=500, detail="Erro interno ao criar registro do cliente.")

    # 4. Vincula o usuário Auth ao cliente na tabela public.users
    try:
        # Usando upsert para garantir
        supabase.table("users").upsert({
            "id":        user.id,
            "email":     client.email,
            "role":      "client",
            "client_id": new_client["id"]
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao vincular permissões (users): {e}")

        # Rollback Client Record
        if new_client:
            try:
                supabase.table("clients").delete().eq("id", new_client["id"]).execute()
            except:
                pass

        # Rollback Auth User
        if user:
            try:
                supabase.auth.admin.delete_user(user.id)
            except:
                pass

        raise HTTPException(status_code=500, detail="Erro ao configurar permissões do usuário.")

    return new_client

@router.patch("/clients/{client_id}")
def update_client(client_id: str, update: ClientUpdate, user_profile: dict = Depends(require_master)):
    supabase = get_supabase()
    data = {k: v for k, v in update.dict().items() if v is not None}
    if not data:
        return {"status": "sem alterações"}
    try:
        return supabase.table("clients").update(data).eq("id", client_id).execute().data
    except Exception as e:
        logger.error(f"Erro ao atualizar cliente {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar cliente.")

@router.post("/impersonate/{client_id}")
def impersonate_client(client_id: str, user_profile: dict = Depends(require_master)):
    # 1. Verify client exists
    supabase = get_supabase()
    res = supabase.table("clients").select("email").eq("id", client_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # 2. Generate temporary token
    # We create a custom JWT that mimics the structure Supabase Auth expects or uses?
    # Actually, we rely on our `get_current_user_role` dependency.
    # But `get_current_user` validates against Supabase Auth via `supabase.auth.get_user(token)`.
    # We CANNOT easily forge a Supabase Auth token accepted by `get_user` without the service role signing key matching GoTrue's.
    # However, if we use a custom dependency or if `supabase-py` allows creating tokens?
    # Standard way: Use `supabase.auth.admin.generate_link` (magic link) or just return a token if we can sign it?
    # `supabase.auth.get_user` calls GoTrue.
    # If we want to impersonate, we might need to bypass `get_current_user` or have it accept our custom signed token.

    # Alternative: The frontend uses the token to call APIs.
    # Our API `dependencies.py` uses `supabase.auth.get_user(token)`.
    # GoTrue (Supabase Auth) tokens are signed with `SUPABASE_JWT_SECRET`.
    # If we have that secret, we can sign a token.
    # In Supabase projects, usually `SUPABASE_SERVICE_KEY` is not the JWT secret.
    # Env var `SUPABASE_JWT_SECRET` is needed.

    # If we don't have the JWT Secret, we can't forge a token that `get_user` accepts.
    # BUT, we can use `supabase.auth.admin.sign_in_with_id_token`? No.

    # Let's assume we have SUPABASE_JWT_SECRET or ENCRYPTION_KEY is used (unlikely for GoTrue).
    # If we cannot generate a valid Auth token, we can't do true impersonation on frontend that calls `get_user`.

    # HACK / WORKAROUND for "Impersonation":
    # Since we are Master, we can just return a custom token signed by US (backend)
    # and update `dependencies.py` to verify this custom token IF `get_user` fails.

    # Let's use `ENCRYPTION_KEY` as secret for our custom impersonation token.

    payload = {
        "client_id": client_id,
        "role": "client", # Impersonated role
        "impersonated_by": user_profile["id"],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "aud": "authenticated", # Mimic Supabase
        "sub": client_id # Usually user_id, but here client_id or we need to find the user_id of the client owner.
    }

    # Find user_id for this client (first user found)
    u_res = supabase.table("users").select("id").eq("client_id", client_id).limit(1).execute()
    if u_res.data:
        payload["sub"] = u_res.data[0]["id"]
    else:
        # No user linked?
        payload["sub"] = client_id # Fallback

    encoded_token = jwt.encode(payload, os.getenv("ENCRYPTION_KEY"), algorithm='HS256')

    # Log Audit
    logger.info(f"Master {user_profile['id']} impersonating Client {client_id}")
    supabase.table("events").insert({
        "event_type": "impersonation_start",
        "metadata": {"master_id": user_profile["id"], "target_client": client_id}
    }).execute() # Assuming events table can hold system events or we add relation later. For now it works if leads FK is optional?
    # Events table has lead_id FK. It might fail if lead_id is required.
    # Schema: lead_id UUID REFERENCES leads...
    # If lead_id is NOT NULL, we can't insert system event.
    # Checked schema: lead_id UUID REFERENCES... (nullable by default in SQL unless NOT NULL specified).
    # Schema says: lead_id UUID REFERENCES leads... (Implies nullable).

    return {"access_token": encoded_token, "redirect": "/frontend/admin/dashboard.html"}
