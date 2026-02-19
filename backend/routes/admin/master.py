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
    password: str  # Required for account creation
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

    # 1. Check if client email already exists in our table
    existing = supabase.table("clients").select("id").eq("email", client.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Client with this email already exists")

    # 2. Create Supabase Auth User
    try:
        # Use admin API to create user without confirmation email for now (auto-confirm)
        # Note: supabase-py v2 syntax might differ slightly for admin.create_user
        # Checking if create_user accepts a dict or kwargs.
        # Based on typical usage: create_user(params)
        auth_res = supabase.auth.admin.create_user({
            "email": client.email,
            "password": client.password,
            "email_confirm": True
        })
        # The result object structure depends on the library version.
        # Assuming auth_res has a 'user' attribute or is the user object.
        user = auth_res.user if hasattr(auth_res, 'user') else auth_res
    except Exception as e:
        print(f"Auth creation error: {e}")
        # If user already exists in Auth but not in clients table, we proceed?
        # Or fail? Let's fail for simplicity to avoid state mismatch.
        raise HTTPException(status_code=400, detail=f"Failed to create Auth user: {str(e)}")

    # 3. Create Client Record
    try:
        # Exclude password from DB insert
        client_data = client.dict(exclude={"password"})
        client_res = supabase.table("clients").insert(client_data).execute()
        new_client = client_res.data[0]
    except Exception as e:
        print(f"Client DB error: {e}")
        # Clean up the auth user if client creation fails
        if user:
            try:
                supabase.auth.admin.delete_user(user.id)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to create client record: {e}")

    # 4. Link Auth User to Client (public.users table)
    try:
        user_record = {
            "id": user.id,
            "role": "client",  # Default role for new clients
            "client_id": new_client['id']
        }
        # In case 'role' is an enum, pass as string.
        # If 'public.users' doesn't exist, this will fail.
        supabase.table("users").insert(user_record).execute()
    except Exception as e:
        print(f"User Link error: {e}")
        # Rollback everything? Ideally yes.
        # Clean up client record
        supabase.table("clients").delete().eq("id", new_client['id']).execute()
        # Clean up auth user
        supabase.auth.admin.delete_user(user.id)
        raise HTTPException(status_code=500, detail=f"Failed to link user permissions: {e}")

    return new_client

@router.patch("/clients/{client_id}")
def update_client(client_id: str, update: ClientUpdate, user_profile: dict = Depends(require_master)):
    supabase = get_supabase()

    data = {k: v for k, v in update.dict().items() if v is not None}
    if not data:
        return {"status": "no changes"}

    res = supabase.table("clients").update(data).eq("id", client_id).execute()
    return res.data
