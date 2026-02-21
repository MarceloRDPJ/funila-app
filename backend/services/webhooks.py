import httpx
import asyncio
import time
from database import get_supabase
from typing import Dict, Any
from services.logger import log_system_event

async def send_webhook(url: str, payload: Dict[str, Any], client_id: str, lead_id: str = None):
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            duration = round((time.time() - start_time) * 1000, 2)

            status = "success" if resp.status_code < 400 else "error"
            level = "info" if status == "success" else "error"

            await log_system_event(
                client_id=client_id,
                level=level,
                source="webhook",
                message=f"Webhook {status} ({resp.status_code})",
                lead_id=lead_id,
                metadata={
                    "url": url,
                    "status_code": resp.status_code,
                    "duration_ms": duration,
                    "payload": payload,
                    "response": resp.text[:1000] # Truncate response
                }
            )

    except Exception as e:
        duration = round((time.time() - start_time) * 1000, 2)
        await log_system_event(
            client_id=client_id,
            level="error",
            source="webhook",
            message=f"Webhook failed: {str(e)}",
            lead_id=lead_id,
            metadata={
                "url": url,
                "duration_ms": duration,
                "payload": payload,
                "error": str(e)
            }
        )

async def trigger_webhooks(event_type: str, lead_data: Dict[str, Any], client_id: str):
    """
    Triggers webhooks for a specific client and event.
    Designed to be run as a background task.
    """
    supabase = get_supabase()

    # Fetch active webhooks for the client
    try:
        res = supabase.table("webhooks").select("url").eq("client_id", client_id).eq("active", True).execute()
        webhooks = res.data
    except Exception as e:
        print(f"Error fetching webhooks for client {client_id}: {e}")
        return

    if not webhooks:
        return

    # Construct payload
    # Payload format required: { lead_id, name, phone, status, internal_score, serasa_score }
    # We add event_type for context
    payload = {
        "event": event_type,
        "lead_id": lead_data.get("id"),
        "name": lead_data.get("name"),
        "phone": lead_data.get("phone"),
        "status": lead_data.get("status"),
        "internal_score": lead_data.get("internal_score"),
        "serasa_score": lead_data.get("serasa_score")
    }

    # Send to all webhooks
    # We can run them concurrently
    lead_id = lead_data.get("id")
    tasks = [send_webhook(wh["url"], payload, client_id, lead_id) for wh in webhooks]
    if tasks:
        await asyncio.gather(*tasks)
