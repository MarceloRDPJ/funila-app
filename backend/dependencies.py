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
    try:
        supabase = get_supabase()
    except RuntimeError:
         # Log specifically that database is not configured
         print("ERROR: Database credentials missing in get_current_user")
         raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de banco de dados indisponível."
        )

    # 1. Try Supabase Auth (GoTrue)
    try:
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            return user_response.user
    except Exception:
        pass

    # 2. Try Custom Impersonation Token (signed by backend)
    try:
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
             # Fallback key generated in utils/security.py might be needed here but we import os.getenv
             # If strictly missing here, impersonation fails.
             pass
        else:
            payload = jwt.decode(token, encryption_key, algorithms=["HS256"])
            # Return a mock user object compatible with what get_current_user_role expects
            class MockUser:
                id = payload.get("sub")
                email = "impersonator@funila.com" # Placeholder
            return MockUser()
    except JWTError:
        pass
    except Exception:
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
    try:
        supabase = get_supabase()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de banco de dados indisponível."
        )

    try:
        response = supabase.table("users").select("role, client_id").eq("id", user.id).single().execute()

        # If response.data is None, user not found. supabase-py single() might raise error if no rows.
        # But if it returns empty data:
        if not response.data:
            print(f"User ID {user.id} not found in public.users table.")
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
        # Check if it's a "Row not found" error from Supabase/Postgrest
        error_str = str(e)
        if "JSON object requested, multiple (or no) rows returned" in error_str or "Results contain 0 rows" in error_str:
             print(f"User ID {user.id} not found in public.users table (Postgrest error).")
             raise HTTPException(status_code=403, detail="Perfil de usuário não encontrado.")

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
