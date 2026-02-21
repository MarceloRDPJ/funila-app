import httpx
import os
import time
from typing import Optional
from services.logger import log_system_event

BRASIL_API_URL = "https://brasilapi.com.br/api/cpf/v1"

async def fetch_brasil_api_data(cpf: str, client_id: str = None, lead_id: str = None) -> Optional[dict]:
    """
    Camada 1: Enriquecimento via BrasilAPI (Gratuito).

    Busca dados públicos vinculados ao CPF.
    - URL: https://brasilapi.com.br/api/cpf/v1/{cpf}
    - Timeout: 5 segundos
    - Retorno: JSON com dados ou None em caso de erro/404.
    """
    if not cpf:
        return None

    clean_cpf = "".join(filter(str.isdigit, cpf))

    if len(clean_cpf) != 11:
        return None

    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BRASIL_API_URL}/{clean_cpf}")

            # Log success/failure only if client_id is provided (context exists)
            if client_id:
                duration = round((time.time() - start_time) * 1000, 2)
                level = "info" if response.status_code == 200 else "warning"

                await log_system_event(
                    client_id=client_id,
                    level=level,
                    source="brasil_api",
                    message=f"BrasilAPI {response.status_code}",
                    lead_id=lead_id,
                    metadata={"cpf_prefix": clean_cpf[:3], "status": response.status_code, "duration_ms": duration}
                )

            if response.status_code == 200:
                return response.json()
    except Exception as e:
        if client_id:
            await log_system_event(
                client_id=client_id,
                level="error",
                source="brasil_api",
                message=f"BrasilAPI Error: {str(e)}",
                lead_id=lead_id,
                metadata={"error": str(e)}
            )
        print(f"BrasilAPI Erro: {e}")
    return None

async def validate_cpf(cpf: str) -> bool:
    data = await fetch_brasil_api_data(cpf)
    return data is not None

async def get_serasa_score(cpf: str) -> int | None:
    token = os.getenv("SOAWS_TOKEN", "")
    if not token or token in ("", "seu_token_soawebservices"):
        print("SOAWS_TOKEN não configurado — consulta Serasa ignorada.")
        return None
    clean = "".join(filter(str.isdigit, cpf))
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"https://api.soawebservices.com.br/serasa/{clean}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                return r.json().get("score")
            print(f"Serasa retornou {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"Serasa API erro: {e}")
        return None
