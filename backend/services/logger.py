from datetime import datetime
from database import get_supabase
from typing import Dict, Any, Optional
import asyncio

async def log_system_event(
    client_id: str,
    level: str,  # 'info', 'warning', 'error', 'success'
    source: str, # 'webhook', 'brasil_api', 'serasa', 'system'
    message: str,
    lead_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Logs a system event to the 'logs' table for observability.
    This function is designed to be fire-and-forget (safe to await, handles its own errors).
    """
    try:
        supabase = get_supabase()

        payload = {
            "client_id": client_id,
            "level": level,
            "source": source,
            "message": message,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        if lead_id:
            payload["lead_id"] = lead_id

        # Insert asynchronously to avoid blocking critical paths if possible
        # Since Supabase-py is synchronous in many contexts, we just run it.
        # Ideally, this should run in a background task if called from a route.
        supabase.table("logs").insert(payload).execute()

    except Exception as e:
        # Failsafe: Don't crash the app if logging fails
        print(f"[LOGGER FAILURE] Could not log event: {e}")
