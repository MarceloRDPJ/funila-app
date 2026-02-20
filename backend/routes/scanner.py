from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from database import get_supabase
from dependencies import require_client

router = APIRouter(tags=["Scanner"])

class ScannerEvent(BaseModel):
    client_id: str
    event_type: str
    page_url: str
    metadata: Optional[Dict[str, Any]] = None

@router.post("/scanner/event")
async def track_scanner_event(event: ScannerEvent):
    """
    Recebe eventos do scanner JS (Beacon Mode).
    Registra page_view, scroll, cliques, etc.
    """
    supabase = get_supabase()

    try:
        # Validar client_id?
        # O scanner roda publicamente, então não podemos exigir token JWT do client.
        # Mas podemos verificar se o client existe se quisermos ser rigorosos.
        # Por performance (beacon), vamos direto ao insert.
        # RLS deve permitir insert público ou função service role?
        # Normalmente, events são public insert, client select.
        # Como estamos usando service role no backend, não tem problema.

        data = {
            "client_id": event.client_id,
            "event_type": event.event_type,
            "page_url": event.page_url,
            "metadata": event.metadata or {}
        }

        supabase.table("external_events").insert(data).execute()

        return {"status": "ok"}

    except Exception as e:
        print(f"Erro no scanner: {e}")
        # Beacon não espera resposta, mas retornamos 200/500 por padrão.
        # Evitar 500 para não sujar logs do cliente.
        return {"status": "error", "detail": str(e)}
