from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from database import get_supabase
from collections import defaultdict
import time

router = APIRouter(tags=["Scanner"])

# --- Simple in-memory rate limiter (per IP, max 60 events/min) ---
_rate_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT = 60
WINDOW = 60  # seconds

def check_rate_limit(ip: str) -> bool:
    now = time.time()
    hits = _rate_store[ip]
    # Remove old hits
    _rate_store[ip] = [t for t in hits if now - t < WINDOW]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True

class ScannerEvent(BaseModel):
    client_id: str
    event_type: str
    page_url: str
    metadata: Optional[Dict[str, Any]] = None

@router.post("/scanner/event")
async def track_scanner_event(event: ScannerEvent, request: Request):
    """
    Recebe eventos do scanner JS (Beacon Mode).
    Rate-limited: max 60 eventos/min por IP.
    """
    ip = request.client.host or "unknown"
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    supabase = get_supabase()

    try:
        # Validate client exists (lightweight check to avoid data pollution)
        client_check = supabase.table("clients").select("id").eq("id", event.client_id).eq("active", True).execute()
        if not client_check.data:
            return {"status": "ok"}  # Silent ignore for unknown clients

        data = {
            "client_id":  event.client_id,
            "event_type": event.event_type,
            "page_url":   event.page_url,
            "metadata":   event.metadata or {}
        }

        supabase.table("external_events").insert(data).execute()
        return {"status": "ok"}

    except Exception as e:
        print(f"Erro no scanner: {e}")
        return {"status": "ok"}  # Beacon mode — always return success to client
