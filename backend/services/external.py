import httpx
import os
import random

async def validate_cpf(cpf: str) -> bool:
    """
    Validates CPF using BrasilAPI (Public/Free).
    """
    if not cpf:
        return False

    clean_cpf = "".join(filter(str.isdigit, cpf))
    if len(clean_cpf) != 11:
        return False

    url = f"https://brasilapi.com.br/api/cpf/v1/{clean_cpf}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                return True
            else:
                return False
    except Exception as e:
        print(f"BrasilAPI Error: {e}")
        # Fail safe: if API is down, assume valid if length is correct to not block lead?
        # Or return False to be safe? Prompt says "Nunca bloquear salvamento do lead se API falhar."
        # So maybe return None (unknown) or False.
        # But if validation fails, we just don't give the 'valid cpf' points.
        return False

async def get_serasa_score(cpf: str) -> int:
    """
    Stub for Serasa Score API (SOAWebServices).
    """
    token = os.getenv("SOAWS_TOKEN")
    if not token or token == "example_token":
        # Mock for dev
        return random.randint(300, 900)

    # Implementation for real API would go here
    # async with httpx.AsyncClient() as client: ...
    return 0
