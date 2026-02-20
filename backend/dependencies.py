from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_supabase

# Instância de segurança Bearer Token
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica o token JWT enviado no header Authorization.
    Retorna o objeto usuário do Supabase Auth se válido.
    """
    token = credentials.credentials
    supabase = get_supabase()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticação inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_response.user
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
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
            # Usuário autenticado mas sem registro na tabela users (inconsistência)
            raise HTTPException(status_code=403, detail="Perfil de usuário não encontrado. Contate o suporte.")

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
