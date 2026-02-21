from fastapi import APIRouter, Depends, HTTPException
from database import get_supabase
from dependencies import require_client
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
import uuid

router = APIRouter(tags=["Links"])


class LinkCreate(BaseModel):
    name:         str
    destination:  str                                   # Destino final (WhatsApp, site, etc.)
    funnel_type:  Literal["form","capture","landing"] = "form"
    capture_url:  Optional[str] = None                  # URL a clonar (modo capture)
    slug:         Optional[str] = None
    utm_source:   Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_medium:   Optional[str] = None
    utm_content:  Optional[str] = None
    metadata:     Optional[Dict[str, Any]] = None


class LinkUpdate(BaseModel):
    name:         Optional[str] = None
    destination:  Optional[str] = None
    funnel_type:  Optional[Literal["form","capture","landing"]] = None
    capture_url:  Optional[str] = None
    utm_source:   Optional[str] = None
    utm_campaign: Optional[str] = None
    active:       Optional[bool] = None
    metadata:     Optional[Dict[str, Any]] = None


@router.get("/links")
def list_links(user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase  = get_supabase()
    return supabase.table("links").select("*").eq("client_id", client_id).order("created_at", desc=True).execute().data


@router.post("/links")
def create_link(link: LinkCreate, user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase  = get_supabase()

    # Validação: modo capture exige capture_url
    if link.funnel_type == "capture" and not link.capture_url:
        raise HTTPException(status_code=400, detail="Modo 'Página própria' exige a URL da página de captura")

    # Gera slug se não informado (Retry logic)
    slug = link.slug
    if not slug:
        base = link.name.lower().replace(" ", "-")
        base = "".join(c for c in base if c.isalnum() or c == "-")
        if not base: base = "link"

        # Retry up to 3 times for collision
        for i in range(3):
            suffix = str(uuid.uuid4())[:4] if i == 0 else str(uuid.uuid4())[:6]
            candidate = f"{base}-{suffix}"
            existing = supabase.table("links").select("id").eq("slug", candidate).execute()
            if not existing.data:
                slug = candidate
                break

        if not slug:
             raise HTTPException(status_code=500, detail="Erro ao gerar link único. Tente novamente.")
    else:
        # Check for slug uniqueness (Manual slug)
        existing = supabase.table("links").select("id").eq("slug", slug).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Slug já existe")

    data = link.dict()
    data["slug"]      = slug
    data["client_id"] = client_id

    # Ensure metadata is at least empty dict if None
    if data.get("metadata") is None:
        data["metadata"] = {}

    # Remove keys that are None to allow DB defaults if any, though here we mostly have strings
    # But specifically 'active' defaults to true in DB, we didn't include it in Create model which is fine.

    try:
        res = supabase.table("links").insert(data).execute()
        if not res.data:
             raise HTTPException(status_code=500, detail="Erro interno ao criar link.")
        return res.data[0]
    except Exception as e:
        print(f"Erro criando link: {e}")
        # Hide internal DB errors
        raise HTTPException(status_code=500, detail="Erro interno ao criar link.")


@router.patch("/links/{link_id}")
def update_link(link_id: str, update: LinkUpdate, user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase  = get_supabase()

    # Filter out None values
    data = {k: v for k, v in update.dict().items() if v is not None}

    if not data:
        return {"status": "sem alterações"}

    try:
        res = supabase.table("links").update(data)\
            .eq("id", link_id).eq("client_id", client_id)\
            .execute()
        return res.data
    except Exception as e:
        print(f"Erro atualizando link: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar link")


@router.delete("/links/{link_id}")
def delete_link(link_id: str, user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase  = get_supabase()
    try:
        supabase.table("links").delete().eq("id", link_id).eq("client_id", client_id).execute()
        return {"status": "deleted"}
    except Exception as e:
        print(f"Erro deletando link: {e}")
        raise HTTPException(status_code=500, detail="Erro ao deletar link")


@router.get("/links/{link_id}/analytics")
def link_analytics(link_id: str, user_profile: dict = Depends(require_client)):
    """
    Retorna funil de conversão completo do link:
    cliques → sessões → etapas → submit
    Com breakdown por campo (onde abandonaram)
    """
    client_id = user_profile["client_id"]
    supabase  = get_supabase()

    # Verifica posse do link
    link_res = supabase.table("links").select("id, name, funnel_type")\
        .eq("id", link_id).eq("client_id", client_id).single().execute()
    if not link_res.data:
        raise HTTPException(status_code=404, detail="Link não encontrado")

    # Total de cliques
    # Using count='exact' requires head=True usually for just count, but with select it returns data too.
    # Supabase-py might handle count differently.
    clicks = supabase.table("clicks").select("id", count="exact")\
        .eq("link_id", link_id).execute()
    total_clicks = clicks.count or 0

    # Total de sessões
    sessions = supabase.table("visitor_sessions").select("id", count="exact")\
        .eq("link_id", link_id).execute()
    total_sessions  = sessions.count or 0

    # Converted (based on leads?)
    # Visitor sessions doesn't strictly track 'converted' flag unless updated.
    # Better to count leads table for conversions.
    leads = supabase.table("leads").select("id", count="exact")\
        .eq("link_id", link_id).execute()
    total_converted = leads.count or 0

    # Eventos de funil agrupados
    events = supabase.table("funnel_events").select("*")\
        .eq("link_id", link_id).execute().data or []

    # Conta por tipo
    event_counts = {}
    field_abandons = {}
    step_completes = {}

    for e in events:
        t = e["event_type"]
        event_counts[t] = event_counts.get(t, 0) + 1

        if t == "form_abandon" and e.get("field_key"):
            fk = e["field_key"]
            field_abandons[fk] = field_abandons.get(fk, 0) + 1

        if t == "step_complete" and e.get("step"):
            s = str(e["step"])
            step_completes[s] = step_completes.get(s, 0) + 1

    return {
        "link": link_res.data,
        "funnel": {
            "clicks":           total_clicks,
            "sessions":         total_sessions,
            "converted":        total_converted,
            "conversion_rate":  round((total_converted / total_sessions) * 100, 1) if total_sessions > 0 else 0,
        },
        "step_completion":   step_completes,   # {"1": 120, "2": 80, "3": 45}
        "field_abandons":    field_abandons,   # {"phone": 12, "income_range": 8}
        "event_breakdown":   event_counts,     # todos os tipos de evento
    }
