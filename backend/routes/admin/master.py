from fastapi import APIRouter, Depends, HTTPException
from database import get_supabase
from dependencies import require_master
from pydantic import BaseModel
from typing import Optional
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
        logger.error(f"Erro ao criar usuário Auth: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Erro ao criar login. Verifique se o e-mail é válido ou já está em uso.")

    # 2. Cria o registro do cliente
    try:
        client_data = client.dict(exclude={"password"})
        client_res = supabase.table("clients").insert(client_data).execute()
        new_client = client_res.data[0]
    except Exception as e:
        logger.error(f"Erro ao criar registro do cliente: {e}", exc_info=True)
        # Tenta remover o usuário Auth criado para evitar inconsistência
        try:
            supabase.auth.admin.delete_user(user.id)
        except Exception as delete_err:
            logger.error(f"Falha ao reverter criação de usuário Auth: {delete_err}")

        raise HTTPException(status_code=500, detail="Erro interno ao criar registro do cliente. Por favor, tente novamente.")

    # 3. Vincula o usuário Auth ao cliente na tabela public.users
    try:
        # Usando upsert para evitar conflito com trigger on_auth_user_created
        supabase.table("users").upsert({
            "id":        user.id,
            "email":     client.email,
            "role":      "client",
            "client_id": new_client["id"]
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao vincular permissões (users): {e}", exc_info=True)

        # Rollback: remove cliente e usuário auth
        try:
            supabase.table("clients").delete().eq("id", new_client["id"]).execute()
        except Exception as del_client_err:
            logger.error(f"Falha ao reverter criação de cliente: {del_client_err}")

        try:
            supabase.auth.admin.delete_user(user.id)
        except Exception as del_auth_err:
            logger.error(f"Falha ao reverter criação de usuário Auth: {del_auth_err}")

        raise HTTPException(status_code=500, detail="Erro ao configurar permissões do usuário. A operação foi cancelada.")

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
        logger.error(f"Erro ao atualizar cliente {client_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao atualizar cliente.")
