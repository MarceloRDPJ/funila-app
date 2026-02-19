from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_supabase

security = HTTPBearer()
supabase = get_supabase()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return user.user
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

def get_current_user_role(user=Depends(get_current_user)):
    try:
        response = supabase.table("users").select("role, client_id").eq("id", user.id).single().execute()
        if not response.data:
            raise HTTPException(status_code=403, detail="Perfil de usuário não encontrado")
        return {
            "id": user.id,
            "email": user.email,
            "role": response.data["role"],
            "client_id": response.data.get("client_id")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Role Fetch Error: {e}")
        raise HTTPException(status_code=403, detail="Não foi possível verificar permissões")

def require_master(user_profile=Depends(get_current_user_role)):
    if user_profile["role"] != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito ao master")
    return user_profile

def require_client(user_profile=Depends(get_current_user_role)):
    if user_profile["role"] not in ["client", "master"]:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    return user_profile
