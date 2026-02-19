from fastapi import APIRouter, Depends, HTTPException, Body
from database import get_supabase
from dependencies import require_master
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/admin/master", tags=["Master Admin"])

class ClientCreate(BaseModel):
    name: str
    email: str
    plan: str = "solo"
    whatsapp: Optional[str] = None

class ClientUpdate(BaseModel):
    plan: Optional[str] = None
    active: Optional[bool] = None

@router.get("/clients")
def list_clients(user_profile: dict = Depends(require_master)):
    supabase = get_supabase()
    res = supabase.table("clients").select("*").order("created_at", desc=True).execute()
    return res.data

@router.post("/clients")
def create_client(client: ClientCreate, user_profile: dict = Depends(require_master)):
    supabase = get_supabase()

    # Check if email exists
    existing = supabase.table("clients").select("id").eq("email", client.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Client with this email already exists")

    res = supabase.table("clients").insert(client.dict()).execute()

    # Ideally, we would also invite the user via Supabase Auth here or return instructions
    # For now, just create the client record.

    return res.data[0]

@router.patch("/clients/{client_id}")
def update_client(client_id: str, update: ClientUpdate, user_profile: dict = Depends(require_master)):
    supabase = get_supabase()

    data = {k: v for k, v in update.dict().items() if v is not None}
    if not data:
        return {"status": "no changes"}

    res = supabase.table("clients").update(data).eq("id", client_id).execute()
    return res.data
