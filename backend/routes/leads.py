from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from database import get_supabase
from utils.security import encrypt_cpf
from services.scorer import calculate_score
from services.email import send_lead_alert

router = APIRouter(tags=["Leads"])

class LeadSubmit(BaseModel):
    client_id: str
    link_id: Optional[str] = None
    form_data: Dict[str, Any] # {field_key: value}
    utm_data: Optional[Dict[str, str]] = None

@router.post("/leads")
async def submit_lead(payload: LeadSubmit, background_tasks: BackgroundTasks, request: Request):
    supabase = get_supabase()

    # 1. Fetch Client Plan & Config
    client_res = supabase.table("clients").select("plan, email").eq("id", payload.client_id).single().execute()
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Client not found")

    client_plan = client_res.data['plan']
    client_email = client_res.data['email']

    # 2. Process Data
    form_data = payload.form_data

    # Encrypt CPF
    cpf = form_data.get('cpf')
    cpf_encrypted = encrypt_cpf(cpf) if cpf else None

    # Calculate Score
    # We need the form config to know which fields affect score, but our scorer currently hardcodes standard logic
    # In a full dynamic system, we'd pass the config rules.
    # For now, pass form_data directly.
    internal_score, external_score = await calculate_score(form_data, [], client_plan)
    final_score = internal_score + external_score

    # Determine Status
    status = "cold"
    if final_score >= 70:
        status = "hot"
    elif final_score >= 40:
        status = "warm"

    # 3. Save Lead
    lead_insert = {
        "client_id": payload.client_id,
        "link_id": payload.link_id,
        "name": form_data.get('full_name', 'Unknown'),
        "phone": form_data.get('phone', ''),
        "cpf_encrypted": cpf_encrypted,
        "internal_score": internal_score,
        "external_score": external_score,
        "status": status,
        "utm_source": payload.utm_data.get('utm_source') if payload.utm_data else None,
        "utm_campaign": payload.utm_data.get('utm_campaign') if payload.utm_data else None,
        "device_type": "mobile", # Can parse UA here too if needed
        "consent_given": True # Assumed from form submission
    }

    try:
        lead_res = supabase.table("leads").insert(lead_insert).execute()
        lead_id = lead_res.data[0]['id']

        # 4. Save Responses
        # We need field_ids. Fetch form_fields map.
        # This is a bit expensive per lead, caching would be good.
        fields_res = supabase.table("form_fields").select("id, field_key").execute()
        field_map = {f['field_key']: f['id'] for f in fields_res.data}

        responses = []
        for key, value in form_data.items():
            if key in field_map:
                responses.append({
                    "lead_id": lead_id,
                    "field_id": field_map[key],
                    "response_value": str(value)
                })

        if responses:
            supabase.table("lead_responses").insert(responses).execute()

        # 5. Background Tasks (Email Alert)
        if status == "hot":
            background_tasks.add_task(send_lead_alert, client_email, lead_insert['name'], lead_insert['phone'], final_score)

        return {
            "status": "success",
            "score": final_score,
            "lead_id": lead_id,
            "whatsapp_link": f"https://wa.me/55{lead_insert['phone']}" # Placeholder, frontend generates the real link
        }

    except Exception as e:
        print(f"Error saving lead: {e}")
        raise HTTPException(status_code=500, detail="Could not save lead")
