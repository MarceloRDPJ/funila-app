import httpx
import time
import os
from database import get_supabase
from typing import Optional

# Configuração de APIs Externas
BRASIL_API_URL = "https://brasilapi.com.br/api/cpf/v1"
SERASA_API_URL = "https://api.soawebservices.com.br/serasa"

async def fetch_brasil_api_data(cpf: str) -> Optional[dict]:
    """
    Camada 1: Enriquecimento via BrasilAPI (Gratuito).

    Busca dados públicos vinculados ao CPF.
    - URL: https://brasilapi.com.br/api/cpf/v1/{cpf}
    - Timeout: 5 segundos
    - Retorno: JSON com dados ou None em caso de erro/404.
    """
    clean_cpf = "".join(filter(str.isdigit, cpf))
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BRASIL_API_URL}/{clean_cpf}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"BrasilAPI Erro: {e}")
    return None

def validate_whatsapp_background(lead_id: str, phone: str):
    """
    Camada 2: Validação de WhatsApp (Background Task).

    Verifica se o número possui conta no WhatsApp.
    - Integração: Evolution API / Z-API (Placeholder Mockado).
    - Execução: Síncrona mas rodada em threadpool via BackgroundTasks do FastAPI.
    - Ação: Atualiza a coluna `whatsapp_meta` no lead.
    """
    supabase = get_supabase()
    clean_phone = "".join(filter(str.isdigit, phone))

    # Lógica Mockada / Placeholder
    # Em produção, substituir por chamada real à Evolution API
    try:
        # Simula latência de rede
        time.sleep(1)

        # Mock: Números terminados em 00 são inválidos
        is_valid = not clean_phone.endswith("00")
        profile_pic = f"https://ui-avatars.com/api/?name={clean_phone}&background=25D366&color=fff" if is_valid else None

        whatsapp_meta = {
            "valid": is_valid,
            "profile_pic": profile_pic,
            "verified_at": str(time.time()),
            "provider": "evolution_api_mock"
        }

        # Atualiza lead no banco
        supabase.table("leads").update({"whatsapp_meta": whatsapp_meta}).eq("id", lead_id).execute()

    except Exception as e:
        print(f"Erro Validação WhatsApp Lead {lead_id}: {e}")

async def get_serasa_score(cpf: str, token: str) -> Optional[int]:
    """
    Camada 3: Consulta Serasa (SOAWebServices).

    - Requisito: Cliente deve ter plano 'pro' ou 'agency'.
    - Custo: Consome créditos da API externa.
    - Retorno: Score (0-1000) ou None.
    """
    clean_cpf = "".join(filter(str.isdigit, cpf))
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{SERASA_API_URL}/{clean_cpf}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return data.get("score")
    except Exception as e:
        print(f"Serasa API Erro: {e}")
    return None

async def enrich_lead_data(lead_id: str, cpf: str, client_id: str, background_tasks):
    """
    Motor de Enriquecimento em Cascata.

    Acionado via BackgroundTasks no submit parcial ou total.
    1. Busca dados na BrasilAPI (Nome, Região).
    2. Atualiza nome do lead se estiver vazio.
    3. Verifica plano do cliente para consulta Serasa.
    4. Agenda validação de WhatsApp em background.
    5. Salva enriquecimentos no banco (public_api_data, serasa_score).
    """
    supabase = get_supabase()

    # Busca dados atuais para evitar sobreescrita
    try:
        lead_res = supabase.table("leads").select("name, phone").eq("id", lead_id).single().execute()
        if not lead_res.data:
            return
        lead = lead_res.data
        current_name = lead.get("name")
        phone = lead.get("phone")
    except Exception:
        return

    updates = {}

    # Camada 1: BrasilAPI (Async)
    if cpf:
        api_data = await fetch_brasil_api_data(cpf)
        if api_data:
            updates["public_api_data"] = api_data
            # Se nome vier vazio do form, tenta preencher via API
            if not current_name or (isinstance(current_name, str) and not current_name.strip()):
                name_from_api = api_data.get("nome") or api_data.get("name")
                if name_from_api:
                    updates["name"] = name_from_api

    # Camada 3: Serasa (Async Check)
    # Verificar permissão do plano
    try:
        client_res = supabase.table("clients").select("plan").eq("id", client_id).single().execute()
        client_plan = client_res.data["plan"] if client_res.data else "solo"
    except:
        client_plan = "solo"

    if cpf and client_plan in ('pro', 'agency'):
        token = os.getenv("SOAWS_TOKEN")
        if token:
            score = await get_serasa_score(cpf, token)
            if score is not None:
                updates["serasa_score"] = score

    # Aplicar atualizações no banco
    if updates:
        try:
            supabase.table("leads").update(updates).eq("id", lead_id).execute()
        except Exception as e:
            print(f"Erro Update Enriquecimento: {e}")

    # Camada 2: WhatsApp (Agenda Task Síncrona)
    if phone:
        background_tasks.add_task(validate_whatsapp_background, lead_id, phone)
