import httpx
import os

async def validate_cpf(cpf: str) -> bool:
    if not cpf:
        return False
    clean_cpf = "".join(filter(str.isdigit, cpf))
    if len(clean_cpf) != 11:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"https://brasilapi.com.br/api/cpf/v1/{clean_cpf}")
            return r.status_code == 200
    except Exception as e:
        print(f"BrasilAPI erro (CPF): {e}")
        return False

async def get_serasa_score(cpf: str) -> int | None:
    token = os.getenv("SOAWS_TOKEN", "")
    if not token or token in ("example_token", "seu_token_soawebservices", ""):
        print("SOAWS_TOKEN não configurado — consulta Serasa pulada.")
        return None

    clean_cpf = "".join(filter(str.isdigit, cpf))
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"https://api.soawebservices.com.br/serasa/{clean_cpf}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                return r.json().get("score")
            else:
                print(f"Serasa retornou {r.status_code}: {r.text[:200]}")
                return None
    except Exception as e:
        print(f"Serasa API erro: {e}")
        return None
