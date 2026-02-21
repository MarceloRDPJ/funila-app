from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_supabase
from jose import jwt, JWTError
import os

# ─── MASTER EMAIL — defina aqui ou via variável de ambiente ───────────────────
# Usuários com este email recebem role=master automaticamente se não
# tiverem linha em public.users ainda.
MASTER_EMAILS = os.getenv("MASTER_EMAIL", "marcelorodriguesd017@gmail.com").split(",")

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica o token JWT enviado no header Authorization.
    Tenta primeiro via Supabase Auth (GoTrue).
    Fallback: token customizado de impersonação assinado pelo backend.
    """
    token = credentials.credentials

    try:
        supabase = get_supabase()
    except RuntimeError:
        print("ERROR: Database credentials missing in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de banco de dados indisponível.",
        )

    # 1. Tenta Supabase Auth (GoTrue) — caminho normal
    try:
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            return user_response.user
    except Exception:
        pass

    # 2. Fallback: token customizado de impersonação (assinado pelo backend)
    try:
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if encryption_key:
            payload = jwt.decode(token, encryption_key, algorithms=["HS256"])

            class MockUser:
                id    = payload.get("sub")
                email = payload.get("email", "impersonator@funila.com")

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
    Busca o perfil do usuário na tabela `public.users`.
    Se não encontrar, auto-cria a linha com:
      - role='master' se o email for o MASTER_EMAIL
      - role='client' para qualquer outro
    Isso resolve o erro 403 ao fazer login pela primeira vez
    antes de rodar as migrations manualmente.
    """
    try:
        supabase = get_supabase()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de banco de dados indisponível.",
        )

    try:
        response = (
            supabase.table("users")
            .select("role, client_id, email")
            .eq("id", user.id)
            .single()
            .execute()
        )

        # ─── AUTO-CORRECTION FOR MASTER ───
        # Se o email for MASTER_EMAIL mas a role não for 'master', força o update.
        user_email = getattr(user, "email", "") or ""
        db_role = response.data.get("role")

        if user_email in MASTER_EMAILS and db_role != "master":
            print(f"[Auth] Auto-promoting {user_email} to 'master'.")
            supabase.table("users").update({"role": "master"}).eq("id", user.id).execute()
            db_role = "master"

        return {
            "id":        user.id,
            "email":     user.email,
            "role":      db_role,
            "client_id": response.data.get("client_id"),
        }

    except Exception as e:
        error_str = str(e)

        # ── Linha não existe em public.users ──────────────────────────────────
        is_not_found = (
            "JSON object requested, multiple (or no) rows returned" in error_str
            or "Results contain 0 rows" in error_str
            or "PGRST116" in error_str          # PostgREST "row not found" code
        )

        if is_not_found:
            # Determina o role: master para o dono do sistema
            user_email = getattr(user, "email", "") or ""
            role = "master" if user_email in MASTER_EMAILS else "client"

            print(
                f"[Auth] Usuário {user.id} ({user_email}) não encontrado em public.users. "
                f"Auto-criando com role='{role}'."
            )

            try:
                supabase.table("users").upsert(
                    {
                        "id":        user.id,
                        "email":     user_email,
                        "role":      role,
                        "client_id": None,
                    },
                    on_conflict="id",
                ).execute()

                return {
                    "id":        user.id,
                    "email":     user_email,
                    "role":      role,
                    "client_id": None,
                }

            except Exception as upsert_err:
                print(f"[Auth] Erro ao auto-criar perfil: {upsert_err}")
                raise HTTPException(
                    status_code=403,
                    detail="Perfil de usuário não encontrado e não foi possível criá-lo automaticamente.",
                )

        # ── Outro erro (conexão, permissão, etc.) ─────────────────────────────
        print(f"[Auth] Role Fetch Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao verificar permissões.",
        )


def require_master(user_profile: dict = Depends(get_current_user_role)):
    """
    Dependência: exige role='master'.
    """
    if user_profile["role"] != "master":
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito ao administrador Master.",
        )
    return user_profile


def require_client(user_profile: dict = Depends(get_current_user_role)):
    """
    Dependência: exige role='client' ou 'master'.
    Clientes precisam ter client_id vinculado.
    Masters sem client_id (fora de impersonação) recebem 400 para operações que exigem tenant.
    """
    if user_profile["role"] not in ("client", "master"):
        raise HTTPException(
            status_code=403,
            detail="Acesso não autorizado para este perfil.",
        )

    # Clientes comuns precisam ter client_id vinculado
    if user_profile["role"] == "client" and not user_profile.get("client_id"):
        raise HTTPException(
            status_code=403,
            detail="Usuário não vinculado a nenhuma conta de cliente.",
        )

    # Masters sem impersonação ativa nao tem client_id — bloqueia operações tenant-scoped
    if user_profile["role"] == "master" and not user_profile.get("client_id"):
        raise HTTPException(
            status_code=400,
            detail="Master sem impersonação ativa. Use /admin/master/impersonate/{id} para acessar dados de um cliente.",
        )

    return user_profile
