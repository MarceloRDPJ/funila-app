import httpx
import time
import os
from database import get_supabase
from typing import Optional

# Configuration
BRASIL_API_URL = "https://brasilapi.com.br/api/cpf/v1"
SERASA_API_URL = "https://api.soawebservices.com.br/serasa"

async def fetch_brasil_api_data(cpf: str) -> Optional[dict]:
    """
    Layer 1: BrasilAPI Enrichment (Free)
    """
    clean_cpf = "".join(filter(str.isdigit, cpf))
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BRASIL_API_URL}/{clean_cpf}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"BrasilAPI Error: {e}")
    return None

def validate_whatsapp_background(lead_id: str, phone: str):
    """
    Layer 2: WhatsApp Validation (Background Task)
    Placeholder for Evolution API / Z-API integration.
    """
    supabase = get_supabase()
    clean_phone = "".join(filter(str.isdigit, phone))

    # Mock/Placeholder Logic
    # In production, this would make an API call to Evolution API
    try:
        # Simulate work
        time.sleep(1)

        # Mock result based on phone ending
        is_valid = not clean_phone.endswith("00")
        profile_pic = f"https://ui-avatars.com/api/?name={clean_phone}&background=25D366&color=fff" if is_valid else None

        whatsapp_meta = {
            "valid": is_valid,
            "profile_pic": profile_pic,
            "verified_at": str(time.time()), # simple timestamp
            "provider": "evolution_api_mock"
        }

        # Update lead
        supabase.table("leads").update({"whatsapp_meta": whatsapp_meta}).eq("id", lead_id).execute()

    except Exception as e:
        print(f"WhatsApp Validation Error for lead {lead_id}: {e}")

async def get_serasa_score(cpf: str, token: str) -> Optional[int]:
    clean_cpf = "".join(filter(str.isdigit, cpf))
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{SERASA_API_URL}/{clean_cpf}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                data = response.json()
                # Adjust based on actual API response structure
                if isinstance(data, dict):
                    return data.get("score")
    except Exception as e:
        print(f"Serasa API Error: {e}")
    return None

async def enrich_lead_data(lead_id: str, cpf: str, client_id: str, background_tasks):
    """
    Main Enrichment Engine
    Triggered on partial submit (with CPF) or full submit.
    """
    supabase = get_supabase()

    # Get current lead data
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

    # Layer 1: BrasilAPI (Async)
    if cpf:
        api_data = await fetch_brasil_api_data(cpf)
        if api_data:
            updates["public_api_data"] = api_data
            # If name is empty/placeholder, update from API
            if not current_name or (isinstance(current_name, str) and not current_name.strip()):
                name_from_api = api_data.get("nome") or api_data.get("name")
                if name_from_api:
                    updates["name"] = name_from_api

    # Layer 3: Serasa (Async Check)
    # Check plan first
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

    # Apply updates
    if updates:
        try:
            supabase.table("leads").update(updates).eq("id", lead_id).execute()
        except Exception as e:
            print(f"Enrichment Update Error: {e}")

    # Layer 2: WhatsApp (Background Task - Sync Function)
    if phone:
        background_tasks.add_task(validate_whatsapp_background, lead_id, phone)
