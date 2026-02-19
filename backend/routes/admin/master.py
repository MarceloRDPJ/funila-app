from fastapi import APIRouter, Depends, HTTPException
from database import get_supabase
from dependencies import require_master
from pydantic import BaseModel
from typing import Optional

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

@router.get("/clients")
def list_clients(user_profile: dict = Depends(require_master)):
    supabase = get_supabase()
    return supabase.table("clients").select("*").order("created_at", desc=True).execute().data

@router.post("/clients")
def create_client(client: ClientCreate, user_profile: dict = Depends(require_master)):
    supabase = get_supabase()

    existing = supabase.table("clients").select("id").eq("email", client.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Já existe um cliente com esse e-mail")

    # 1. Cria o usuário no Supabase Auth
    try:
        auth_res = supabase.auth.admin.create_user({
            "email": client.email,
            "password": client.password,
            "email_confirm": True
        })
        user = auth_res.user if hasattr(auth_res, "user") else auth_res
    except Exception as e:
        print(f"Erro ao criar usuário Auth: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao criar login: {str(e)}")

    # 2. Cria o registro do cliente
    try:
        client_data = client.dict(exclude={"password"})
        client_res = supabase.table("clients").insert(client_data).execute()
        new_client = client_res.data[0]
    except Exception as e:
        print(f"Erro ao criar cliente: {e}")
        try:
            supabase.auth.admin.delete_user(user.id)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Erro ao criar registro do cliente: {str(e)}")

    # 3. Vincula o usuário Auth ao cliente na tabela public.users
    try:
        supabase.table("users").insert({
            "id":        user.id,
            "email":     client.email,
            "role":      "client",
            "client_id": new_client["id"]
        }).execute()
    except Exception as e:
        print(f"Erro ao vincular usuário: {e}")
        supabase.table("clients").delete().eq("id", new_client["id"]).execute()
        try:
            supabase.auth.admin.delete_user(user.id)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Erro ao vincular permissões: {str(e)}")

    return new_client

@router.patch("/clients/{client_id}")
def update_client(client_id: str, update: ClientUpdate, user_profile: dict = Depends(require_master)):
    supabase = get_supabase()
    data = {k: v for k, v in update.dict().items() if v is not None}
    if not data:
        return {"status": "sem alterações"}
    return supabase.table("clients").update(data).eq("id", client_id).execute().data
