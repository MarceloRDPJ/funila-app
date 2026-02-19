import urllib.parse
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from database import get_supabase
from utils.security import encrypt_cpf
from services.scorer import calculate_score
from services.email import send_lead_alert
from dependencies import require_client

router = APIRouter(tags=["Leads"])

class LeadSubmit(BaseModel):
    client_id: str
    link_id: Optional[str] = None
    form_data: Dict[str, Any]
    utm_data: Optional[Dict[str, str]] = None
    consent_given: bool = False

@router.post("/leads")
async def submit_lead(payload: LeadSubmit, background_tasks: BackgroundTasks, request: Request):
    if not payload.consent_given:
        raise HTTPException(status_code=400, detail="Consentimento LGPD obrigatório")

    supabase = get_supabase()

    client_res = supabase.table("clients").select("plan, email, whatsapp").eq("id", payload.client_id).single().execute()
    if not client_res.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    client_plan  = client_res.data["plan"]
    client_email = client_res.data["email"]
    client_whats = client_res.data.get("whatsapp", "")

    form_data = payload.form_data

    cpf = form_data.get("cpf")
    cpf_encrypted = encrypt_cpf(cpf) if cpf else None

    internal_score, external_score, serasa_score_raw = await calculate_score(form_data, [], client_plan)
    final_score = internal_score + external_score

    if final_score >= 70:
        status = "hot"
    elif final_score >= 40:
        status = "warm"
    else:
        status = "cold"

    name      = form_data.get("full_name", "")
    has_clt   = form_data.get("has_clt", "")
    clt_years = form_data.get("clt_years", "")
    income    = form_data.get("income_range", "")
    tried     = form_data.get("tried_financing", "")

    if has_clt == "Sim" and clt_years:
        clt_part = f"CLT há {clt_years}"
    elif has_clt == "Não":
        clt_part = "sem carteira assinada"
    else:
        clt_part = "situação profissional não informada"

    tried_part = "Nunca tentei financiar." if tried == "Não" else "Já tentei financiar antes."

    whatsapp_msg = (
        f"Olá! Me chamo {name}. "
        f"Tenho {clt_part}, renda aproximada de {income}. "
        f"{tried_part} "
        f"Gostaria de mais informações."
    )

    if client_whats:
        clean_whats = client_whats.replace("(","").replace(")","").replace("-","").replace(" ","")
        whatsapp_url = f"https://wa.me/55{clean_whats}?text={urllib.parse.quote(whatsapp_msg)}"
    else:
        whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(whatsapp_msg)}"

    lead_insert = {
        "client_id":      payload.client_id,
        "link_id":        payload.link_id,
        "name":           name,
        "phone":          form_data.get("phone", ""),
        "cpf_encrypted":  cpf_encrypted,
        "internal_score": internal_score,
        "external_score": external_score,
        "serasa_score":   serasa_score_raw,
        "status":         status,
        "utm_source":     payload.utm_data.get("utm_source")   if payload.utm_data else None,
        "utm_campaign":   payload.utm_data.get("utm_campaign") if payload.utm_data else None,
        "utm_medium":     payload.utm_data.get("utm_medium")   if payload.utm_data else None,
        "consent_given":  True,
    }

    try:
        lead_res = supabase.table("leads").insert(lead_insert).execute()
        lead_id  = lead_res.data[0]["id"]

        fields_res = supabase.table("form_fields").select("id, field_key").execute()
        field_map  = {f["field_key"]: f["id"] for f in fields_res.data}

        responses = [
            {"lead_id": lead_id, "field_id": field_map[k], "response_value": str(v)}
            for k, v in form_data.items()
            if k in field_map
        ]
        if responses:
            supabase.table("lead_responses").insert(responses).execute()

        supabase.table("events").insert({
            "lead_id":    lead_id,
            "event_type": "form_submit",
            "metadata":   {"score": final_score, "status": status}
        }).execute()

        if status == "hot":
            background_tasks.add_task(
                send_lead_alert, client_email, name,
                form_data.get("phone", ""), final_score
            )

        return {
            "status":        "success",
            "score":         final_score,
            "lead_id":       lead_id,
            "whatsapp_link": whatsapp_url,
        }

    except Exception as e:
        print(f"Erro ao salvar lead: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível salvar o lead")


@router.get("/leads")
def list_leads(
    status: Optional[str] = None,
    user_profile: dict = Depends(require_client)
):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    query = supabase.table("leads").select("*").eq("client_id", client_id).order("created_at", desc=True)
    if status:
        query = query.eq("status", status)

    return query.execute().data
