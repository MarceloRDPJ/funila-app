from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
import os
from dotenv import load_dotenv
from database import get_supabase

load_dotenv()

security = HTTPBearer()
supabase = get_supabase()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the JWT token with Supabase Auth.
    Returns the user object if valid.
    """
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        if not user:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user.user
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_role(user = Depends(get_current_user)):
    """
    Fetches the user role from the public.users table.
    """
    try:
        # Assuming public.users table exists and has a 'role' column
        response = supabase.table("users").select("role, client_id").eq("id", user.id).single().execute()
        if not response.data:
             # Fallback or error if user not in public.users
             raise HTTPException(status_code=403, detail="User profile not found")

        return {
            "id": user.id,
            "email": user.email,
            "role": response.data['role'],
            "client_id": response.data.get('client_id')
        }
    except Exception as e:
        print(f"Role Fetch Error: {e}")
        raise HTTPException(status_code=403, detail="Could not verify user role")

def require_master(user_profile = Depends(get_current_user_role)):
    if user_profile["role"] != "master":
        raise HTTPException(status_code=403, detail="Master access required")
    return user_profile

def require_client(user_profile = Depends(get_current_user_role)):
    # Clients can access client routes. Master can too (usually).
    # If strictly client, check role == 'client'.
    # For now, allow master to impersonate or access client routes if needed,
    # but typically client routes rely on client_id.
    if user_profile["role"] not in ["client", "master"]:
        raise HTTPException(status_code=403, detail="Client access required")
    return user_profile
