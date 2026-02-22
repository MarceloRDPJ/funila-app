from fastapi import APIRouter, Depends, HTTPException, Body
from database import get_supabase
from dependencies import require_client
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any
import uuid
import logging

# Configure logging
logger = logging.getLogger(__name__)

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

    logger.info(f"Listing links for client_id: {client_id}")

    try:
        res = supabase.table("links").select("*").eq("client_id", client_id).order("created_at", desc=True).execute()
        links = res.data
        logger.info(f"Found {len(links)} links")
        return links
    except Exception as e:
        logger.error(f"Error listing links: {e}")
        # Return empty list on error to prevent UI crash, but log it
        # Or re-raise 500
        raise HTTPException(status_code=500, detail="Erro ao carregar campanhas.")


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
            try:
                existing = supabase.table("links").select("id").eq("slug", candidate).execute()
                if not existing.data:
                    slug = candidate
                    break
            except Exception as e:
                logger.error(f"Error checking slug collision: {e}")
                # If table check fails, we might have bigger issues, but assume no collision for now or fail
                pass

        if not slug:
             raise HTTPException(status_code=500, detail="Erro ao gerar link único. Tente novamente.")
    else:
        # Check for slug uniqueness (Manual slug)
        try:
            existing = supabase.table("links").select("id").eq("slug", slug).execute()
            if existing.data:
                raise HTTPException(status_code=400, detail="Slug já existe")
        except Exception as e:
            logger.error(f"Error checking manual slug: {e}")
            pass

    data = link.model_dump()
    data["slug"]      = slug
    data["client_id"] = client_id

    # Ensure metadata is at least empty dict if None
    if data.get("metadata") is None:
        data["metadata"] = {}

    # Remove keys that are None to allow DB defaults
    # And specifically remove utm_medium/content if they are None to avoid issues if column missing?
    # No, if column is missing, even passing None might fail if Supabase is strict.
    # But usually insert payload should match columns.
    # We filter out None values generally.
    data = {k: v for k, v in data.items() if v is not None}

    logger.info(f"Creating link with data: {data}")

    try:
        res = supabase.table("links").insert(data).execute()
        if not res.data:
             raise HTTPException(status_code=500, detail="Erro interno ao criar link (sem dados retornados).")
        return res.data[0]
    except Exception as e:
        logger.error(f"Erro criando link: {e}")
        # Try to give a helpful error message
        msg = str(e)
        if "column" in msg.lower() and "does not exist" in msg.lower():
            raise HTTPException(status_code=500, detail="Erro de esquema no banco de dados. Coluna faltando.")
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
        logger.error(f"Erro atualizando link: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar link")


@router.delete("/links/{link_id}")
def delete_link(link_id: str, user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase  = get_supabase()
    try:
        supabase.table("links").delete().eq("id", link_id).eq("client_id", client_id).execute()
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Erro deletando link: {e}")
        raise HTTPException(status_code=500, detail="Erro ao deletar link")


@router.get("/links/{link_id}/analytics")
def link_analytics(link_id: str, user_profile: dict = Depends(require_client)):
    """
    Retorna funil de conversão completo do link
    """
    client_id = user_profile["client_id"]
    supabase  = get_supabase()

    try:
        # Verifica posse do link
        link_res = supabase.table("links").select("id, name, funnel_type")\
            .eq("id", link_id).eq("client_id", client_id).single().execute()
        if not link_res.data:
            raise HTTPException(status_code=404, detail="Link não encontrado")

        # Basic counts - trying to be robust
        # Supabase-py count implementation varies. Using execute(count='exact') usually helps.
        # But select(count='exact', head=True) is better for just count.

        clicks = supabase.table("clicks").select("id", count="exact").eq("link_id", link_id).execute()
        total_clicks = clicks.count or 0

        sessions = supabase.table("visitor_sessions").select("id", count="exact").eq("link_id", link_id).execute()
        total_sessions  = sessions.count or 0

        leads = supabase.table("leads").select("id", count="exact").eq("link_id", link_id).execute()
        total_converted = leads.count or 0

        # Eventos de funil
        events = supabase.table("funnel_events").select("*").eq("link_id", link_id).execute().data or []

        event_counts = {}
        field_abandons = {}
        step_completes = {}

        for e in events:
            t = e.get("event_type")
            if t:
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
            "step_completion":   step_completes,
            "field_abandons":    field_abandons,
            "event_breakdown":   event_counts,
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar analytics.")
