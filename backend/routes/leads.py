import urllib.parse
import csv
import io
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from database import get_supabase
from utils.security import encrypt_cpf
from services.scorer import calculate_score
from services.email import send_lead_alert
from dependencies import require_client
from services.enrichment import enrich_lead_data
from services.webhooks import trigger_webhooks

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
    lead_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    cpf: Optional[str] = None
    last_step: Optional[str] = None
    utm_data: Optional[Dict[str, str]] = None

class LeadStatusUpdate(BaseModel):
    status: str

# Helper to call RPC
def _increment_creative_metric(client_id, utm_content, step, is_click=False, is_conversion=False):
    if not utm_content:
        return
    supabase = get_supabase()
    try:
        supabase.rpc("increment_creative_metric", {
            "p_client_id": client_id,
            "p_utm_content": utm_content,
            "p_step": step,
            "p_is_click": is_click,
            "p_is_conversion": is_conversion
        }).execute()
    except Exception as e:
        print(f"Error updating creative metrics: {e}")

@router.post("/leads/partial")
async def submit_lead_partial(payload: LeadPartialSubmit, background_tasks: BackgroundTasks):
    """
    Salva o lead parcialmente (upsert).
    Garante que o lead não seja perdido caso abandone o formulário e permite telemetria em tempo real.
    """
    supabase = get_supabase()

    utm_content = payload.utm_data.get("utm_content") if payload.utm_data else None

    # Prepara dados para inserção/atualização
    lead_data = {
        "client_id":      payload.client_id,
        "link_id":        payload.link_id,
        "status":         "started",
        "utm_source":     payload.utm_data.get("utm_source")   if payload.utm_data else None,
        "utm_campaign":   payload.utm_data.get("utm_campaign") if payload.utm_data else None,
        "utm_medium":     payload.utm_data.get("utm_medium")   if payload.utm_data else None,
        "utm_content":    utm_content,
        "consent_given":  False
    }

    if payload.name:
        lead_data["name"] = payload.name
    if payload.phone:
        lead_data["phone"] = payload.phone

    # Check if CPF is provided in partial (Layer 1 enrichment trigger)
    cpf_val = payload.cpf
    if cpf_val:
        lead_data["cpf_encrypted"] = encrypt_cpf(cpf_val)

    step_val = 0
    if payload.last_step:
        # Tenta extrair numero do step se for string tipo 'step_2'
        try:
            if "step_" in payload.last_step:
                step_val = int(payload.last_step.replace("step_", ""))
            else:
                step_val = int(payload.last_step)
        except:
            step_val = 0
        lead_data["step_reached"] = step_val

    try:
        lead_id = payload.lead_id

        # Se tem ID, atualiza
        if lead_id:
            supabase.table("leads").update(lead_data).eq("id", lead_id).execute()
        else:
            if not (payload.name and payload.phone):
                raise HTTPException(status_code=400, detail="Nome e Telefone necessários para criar lead")

            lead_res = supabase.table("leads").insert(lead_data).execute()
            lead_id  = lead_res.data[0]["id"]

            supabase.table("events").insert({
                "lead_id":    lead_id,
                "event_type": "lead_started",
                "metadata":   {"partial": True}
            }).execute()

        # Telemetria do passo
        if payload.last_step:
            supabase.table("events").insert({
                "lead_id": lead_id,
                "event_type": "step_update",
                "metadata": {"step": payload.last_step}
            }).execute()

            # Atualiza métricas do criativo (background)
            if utm_content:
                background_tasks.add_task(_increment_creative_metric, payload.client_id, utm_content, step_val)

        # Enrichment Trigger
        if cpf_val:
             background_tasks.add_task(enrich_lead_data, lead_id, cpf_val, payload.client_id, background_tasks)

        return {"status": "success", "lead_id": lead_id}

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Erro ao salvar lead parcial: {e}")
        raise HTTPException(status_code=500, detail="Erro ao iniciar lead")


@router.post("/leads")
async def submit_lead(payload: LeadSubmit, background_tasks: BackgroundTasks, request: Request):
    if not payload.consent_given:
        raise HTTPException(status_code=400, detail="Consentimento LGPD obrigatório")

    supabase = get_supabase()

    utm_content = payload.utm_data.get("utm_content") if payload.utm_data else None

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
        "utm_content":    utm_content,
        "consent_given":  True,
        "step_reached":   99 # Completed
    }

    try:
        lead_id = payload.lead_id
        is_new = True

        if lead_id:
            update_res = supabase.table("leads").update(lead_data).eq("id", lead_id).execute()
            if update_res.data:
                is_new = False
            else:
                lead_res = supabase.table("leads").insert(lead_data).execute()
                lead_id  = lead_res.data[0]["id"]
        else:
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

        # Update Creative Metrics (Completed = 99)
        if utm_content:
            background_tasks.add_task(_increment_creative_metric, payload.client_id, utm_content, 99)

        if cpf:
             background_tasks.add_task(enrich_lead_data, lead_id, cpf, payload.client_id, background_tasks)

        event_type = "lead_created" if is_new else "lead_updated"
        lead_data_for_hook = lead_data.copy()
        lead_data_for_hook["id"] = lead_id
        background_tasks.add_task(trigger_webhooks, event_type, lead_data_for_hook, payload.client_id)

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


@router.patch("/leads/{lead_id}")
async def update_lead_status(
    lead_id: str,
    payload: LeadStatusUpdate,
    background_tasks: BackgroundTasks,
    user_profile: dict = Depends(require_client)
):
    """
    Atualiza status do lead (Kanban).
    """
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    try:
        res = supabase.table("leads").update({"status": payload.status}).eq("id", lead_id).eq("client_id", client_id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Lead não encontrado ou acesso negado")

        lead = res.data[0]

        # Check conversion for creative metrics
        if payload.status == "converted":
            utm_content = lead.get("utm_content")
            if utm_content:
                background_tasks.add_task(_increment_creative_metric, client_id, utm_content, 99, False, True)

        background_tasks.add_task(trigger_webhooks, "status_change", lead, client_id)

        return {"status": "success", "lead": lead}

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Erro ao atualizar lead: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar lead")


# Endpoints de exportação e listagem (mantidos mas simplificados no paste para brevidade se não houve alteração lógica, mas mantendo código original)
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

    # Select all columns to ensure new enrichment fields are returned
    lead_res = supabase.table("leads").select("*").eq("id", lead_id).eq("client_id", client_id).single().execute()
    if not lead_res.data:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    lead = lead_res.data

    # Robust handling for associated tables
    try:
        responses_res = supabase.table("lead_responses")\
            .select("response_value, form_fields(label)")\
            .eq("lead_id", lead_id)\
            .execute()
        responses = responses_res.data or []
    except Exception as e:
        print(f"Erro ao buscar respostas do lead {lead_id}: {e}")
        responses = []

    try:
        events_res = supabase.table("events").select("*").eq("lead_id", lead_id).order("created_at", desc=True).execute()
        timeline = events_res.data or []
    except Exception as e:
        print(f"Erro ao buscar timeline do lead {lead_id}: {e}")
        timeline = []

    return {
        "lead": lead,
        "responses": responses,
        "timeline": timeline
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
