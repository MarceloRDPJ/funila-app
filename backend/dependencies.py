from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_supabase
from jose import jwt, JWTError
import os

# Instância de segurança Bearer Token
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica o token JWT enviado no header Authorization.
    Retorna o objeto usuário do Supabase Auth se válido.
    """
    token = credentials.credentials
    supabase = get_supabase()

    # 1. Try Supabase Auth (GoTrue)
    try:
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            return user_response.user
    except Exception:
        pass

    # 2. Try Custom Impersonation Token (signed by backend)
    try:
        payload = jwt.decode(token, os.getenv("ENCRYPTION_KEY"), algorithms=["HS256"])
        # Return a mock user object compatible with what get_current_user_role expects
        class MockUser:
            id = payload.get("sub")
            email = "impersonator@funila.com" # Placeholder

        # We attach impersonation info to the mock user if needed, or rely on payload check in next step
        # But get_current_user_role queries DB.
        # If ID matches a real user in DB, it works.
        # Impersonation token payload["sub"] SHOULD be the user_id of the client.
        return MockUser()
    except JWTError:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user_role(user=Depends(get_current_user)):
    """
    Busca o perfil do usuário na tabela `public.users` para determinar role e client_id.
    Retorna um dicionário com: id, email, role, client_id.
    """
    supabase = get_supabase()
    try:
        response = supabase.table("users").select("role, client_id").eq("id", user.id).single().execute()
        if not response.data:
            # Fallback if impersonation used ID that is not in users table (e.g. client_id as user_id)
            # We can check if 'user' object has special attributes from our mock?
            # Or just trust the token?
            # If we returned MockUser(id=client_id), query fails if client_id != user_id.
            # Let's fix Impersonation logic to try to use Real User ID.
            # If fail, we handle here?
            raise HTTPException(status_code=403, detail="Perfil de usuário não encontrado.")

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
        raise HTTPException(status_code=500, detail="Erro interno ao verificar permissões")

def require_master(user_profile=Depends(get_current_user_role)):
    """
    Dependência: Exige que o usuário tenha role='master'.
    """
    if user_profile["role"] != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador Master")
    return user_profile

def require_client(user_profile=Depends(get_current_user_role)):
    """
    Dependência: Exige que o usuário seja 'client' ou 'master'.
    Garante que `client_id` esteja presente para operações tenant-scoped.
    """
    if user_profile["role"] not in ["client", "master"]:
        raise HTTPException(status_code=403, detail="Acesso não autorizado para este perfil")

    if not user_profile.get("client_id") and user_profile["role"] != "master":
         # Clientes devem ter um client_id associado
         raise HTTPException(status_code=403, detail="Usuário não vinculado a uma conta de cliente")

    return user_profile
