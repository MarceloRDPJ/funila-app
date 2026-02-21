from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_current_user_role
from database import get_supabase
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    whatsapp: Optional[str] = None

@router.get("/me")
def get_me(user_profile: dict = Depends(get_current_user_role)):
    supabase = get_supabase()

    # Base response
    response = {
        "id": user_profile["id"],
        "email": user_profile["email"],
        "role": user_profile["role"],
        "client_id": user_profile.get("client_id"),
        "name": "Usuário",
        "plan": "Free",
        "avatar_initials": "US"
    }

    if user_profile["role"] == "master":
        response["name"] = "Administrador"
        response["plan"] = "Master"
        response["avatar_initials"] = "AD"

    elif user_profile["role"] == "client":
        client_id = user_profile.get("client_id")
        if client_id:
            try:
                client_res = supabase.table("clients").select("name, plan, whatsapp").eq("id", client_id).single().execute()
                if client_res.data:
                    data = client_res.data
                    response["name"] = data.get("name", "Cliente")
                    response["plan"] = data.get("plan", "Free").capitalize()
                    response["whatsapp"] = data.get("whatsapp")

                    # Generate Initials
                    name_parts = response["name"].split()
                    if len(name_parts) > 1:
                        response["avatar_initials"] = (name_parts[0][0] + name_parts[1][0]).upper()
                    elif name_parts:
                        response["avatar_initials"] = name_parts[0][:2].upper()
                    else:
                        response["avatar_initials"] = "CL"
            except Exception as e:
                logger.error(f"Error fetching client profile: {e}")
                # Fallback to default
                pass

    return response

@router.patch("/me")
def update_profile(update: ProfileUpdate, user_profile: dict = Depends(get_current_user_role)):
    supabase = get_supabase()

    if user_profile["role"] == "client":
        client_id = user_profile.get("client_id")
        if not client_id:
            raise HTTPException(status_code=400, detail="Client ID missing")

        data = {k: v for k, v in update.dict().items() if v is not None}
        if not data:
            return {"status": "ok", "msg": "No changes"}

        try:
            supabase.table("clients").update(data).eq("id", client_id).execute()
        except Exception as e:
            logger.error(f"Error updating client profile: {e}")
            raise HTTPException(status_code=500, detail="Error updating profile")

    return {"status": "success"}
