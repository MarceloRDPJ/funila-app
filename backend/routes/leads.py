import urllib.parse
import csv
import io
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import StreamingResponse
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
    lead_id: Optional[str] = None
    form_data: Dict[str, Any]
    utm_data: Optional[Dict[str, str]] = None
    consent_given: bool = False

class LeadPartialSubmit(BaseModel):
    client_id: str
    link_id: Optional[str] = None
    name: str
    phone: str
    utm_data: Optional[Dict[str, str]] = None

@router.post("/leads/partial")
async def submit_lead_partial(payload: LeadPartialSubmit):
    """
    Salva o lead parcialmente (após preencher nome e telefone na etapa 1).
    Garante que o lead não seja perdido caso abandone o formulário.
    """
    supabase = get_supabase()

    lead_insert = {
        "client_id":      payload.client_id,
        "link_id":        payload.link_id,
        "name":           payload.name,
        "phone":          payload.phone,
        "status":         "cold",  # Status inicial válido ('cold', 'warm', 'hot', 'converted')
        "utm_source":     payload.utm_data.get("utm_source")   if payload.utm_data else None,
        "utm_campaign":   payload.utm_data.get("utm_campaign") if payload.utm_data else None,
        "utm_medium":     payload.utm_data.get("utm_medium")   if payload.utm_data else None,
        "consent_given":  False,  # Ainda não aceitou explicitamente na etapa final
    }

    try:
        # Tenta inserir
        lead_res = supabase.table("leads").insert(lead_insert).execute()
        lead_id  = lead_res.data[0]["id"]

        # Registra evento de início
        supabase.table("events").insert({
            "lead_id":    lead_id,
            "event_type": "lead_started",
            "metadata":   {"partial": True}
        }).execute()

        return {"status": "success", "lead_id": lead_id}

    except Exception as e:
        print(f"Erro ao salvar lead parcial: {e}")
        # Não bloqueia o usuário, mas loga o erro
        raise HTTPException(status_code=500, detail="Erro ao iniciar lead")


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

    lead_data = {
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
        lead_id = payload.lead_id
        if lead_id:
            # Atualiza lead existente (convertido de parcial para completo)
            update_res = supabase.table("leads").update(lead_data).eq("id", lead_id).execute()
            # Se por algum motivo o update falhar (ex: lead apagado), cria novo?
            # Por enquanto, assumimos que se update retornar vazio, criamos novo.
            if not update_res.data:
                lead_res = supabase.table("leads").insert(lead_data).execute()
                lead_id  = lead_res.data[0]["id"]
        else:
            # Cria novo lead
            lead_res = supabase.table("leads").insert(lead_data).execute()
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


@router.get("/leads/export")
def export_leads(
    status: Optional[str] = None,
    search: Optional[str] = None,
    user_profile: dict = Depends(require_client)
):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    query = supabase.table("leads").select("*").eq("client_id", client_id).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    if search:
        query = query.or_(f"name.ilike.%{search}%,phone.ilike.%{search}%")

    leads = query.execute().data

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nome", "Telefone", "Status", "Score", "Origem", "Data"])

    for l in leads:
        score = (l.get("internal_score") or 0) + (l.get("external_score") or 0)
        writer.writerow([
            l["id"],
            l["name"],
            l["phone"],
            l["status"],
            score,
            l.get("utm_source", ""),
            l["created_at"]
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"}
    )

@router.get("/leads/{lead_id}")
def get_lead_details(
    lead_id: str,
    user_profile: dict = Depends(require_client)
):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    lead_res = supabase.table("leads").select("*").eq("id", lead_id).eq("client_id", client_id).single().execute()
    if not lead_res.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead = lead_res.data

    # Busca respostas (com join manual se necessário, ou select aninhado se configurado)
    # Supabase join syntax: select("*, form_fields(label)")
    responses_res = supabase.table("lead_responses")\
        .select("response_value, form_fields(label)")\
        .eq("lead_id", lead_id)\
        .execute()

    events_res = supabase.table("events").select("*").eq("lead_id", lead_id).order("created_at", desc=True).execute()

    return {
        "lead": lead,
        "responses": responses_res.data,
        "timeline": events_res.data
    }


@router.get("/leads")
def list_leads(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    user_profile: dict = Depends(require_client)
):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    query = supabase.table("leads").select("*", count="exact").eq("client_id", client_id).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    if search:
        query = query.or_(f"name.ilike.%{search}%,phone.ilike.%{search}%")

    start = (page - 1) * limit
    end   = start + limit - 1
    query = query.range(start, end)

    res = query.execute()

    return {
        "data": res.data,
        "total": res.count,
        "page": page,
        "limit": limit
    }
