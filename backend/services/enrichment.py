import httpx
import time
import os
from database import get_supabase
from typing import Optional
from services.external import fetch_brasil_api_data

# Configuração de APIs Externas
SERASA_API_URL = "https://api.soawebservices.com.br/serasa"

def validate_whatsapp_background(lead_id: str, phone: str, client_id: str = None):
    """
    Camada 2: Validação de WhatsApp (Background Task) via Z-API.

    Verifica credenciais no nível do cliente (Enterprise) ou env vars globais.
    """
    supabase = get_supabase()
    clean_phone = "".join(filter(str.isdigit, phone))

    # 1. Obter credenciais Z-API
    z_instance = os.getenv("ZAPI_INSTANCE")
    z_token = os.getenv("ZAPI_TOKEN")

    # Se cliente for Enterprise/Agência com instância própria, usar dela
    if client_id:
        try:
            c_res = supabase.table("clients").select("zapi_instance, zapi_token").eq("id", client_id).single().execute()
            if c_res.data and c_res.data.get("zapi_instance"):
                z_instance = c_res.data["zapi_instance"]
                z_token = c_res.data["zapi_token"]
        except:
            pass

    if not z_instance or not z_token:
        print("Z-API não configurada.")
        return

    try:
        # 2. Chamada real à Z-API
        # Endpoint: /phone-exists/{phone}
        # Adicionar '55' se não tiver? Geralmente Z-API espera DDI+DDD+Num
        if len(clean_phone) <= 11: clean_phone = "55" + clean_phone

        url = f"https://api.z-api.io/instances/{z_instance}/token/{z_token}/phone-exists/{clean_phone}"

        # Como estamos em background task (threadpool ou async?), aqui é def sincrona.
        # Devemos usar requests ou httpx.Client sincrono?
        # Para evitar bloquear workers do FastAPI, melhor httpx async, mas a func é def.
        # Vamos rodar sync mesmo, é BG task.

        resp = httpx.get(url, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            # Z-API response: { "exists": true, "formattedPhone": "..." } or similar
            is_valid = data.get("exists", False)

            # Buscar foto se valido
            profile_pic = None
            if is_valid:
                # /profile-picture?phone=...
                pic_url = f"https://api.z-api.io/instances/{z_instance}/token/{z_token}/profile-picture?phone={clean_phone}"
                try:
                    p_resp = httpx.get(pic_url, timeout=5)
                    if p_resp.status_code == 200:
                        p_data = p_resp.json()
                        profile_pic = p_data.get("link")
                except:
                    pass

            whatsapp_meta = {
                "valid": is_valid,
                "profile_pic": profile_pic,
                "verified_at": str(time.time()),
                "provider": "z-api"
            }

            supabase.table("leads").update({"whatsapp_meta": whatsapp_meta}).eq("id", lead_id).execute()

    except Exception as e:
        print(f"Erro Z-API Validação Lead {lead_id}: {e}")

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
        background_tasks.add_task(validate_whatsapp_background, lead_id, phone, client_id)
