import httpx
from database import get_supabase
from typing import Dict, Any

async def send_webhook(url: str, payload: Dict[str, Any]):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Webhook Delivery Failed to {url}: {e}")

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
    import asyncio
    tasks = [send_webhook(wh["url"], payload) for wh in webhooks]
    if tasks:
        await asyncio.gather(*tasks)
