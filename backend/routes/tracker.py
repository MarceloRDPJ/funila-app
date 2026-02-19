import hashlib
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from database import get_supabase
from ua_parser import user_agent_parser

router = APIRouter(tags=["Tracker"])

@router.get("/t/{slug}")
def track_and_redirect(slug: str, request: Request):
    supabase = get_supabase()

    response = supabase.table("links").select("*").eq("slug", slug).eq("active", True).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Link não encontrado")

    link = response.data

    ip = request.client.host or "0.0.0.0"
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()

    ua_string = request.headers.get("user-agent", "")
    parsed_ua = user_agent_parser.Parse(ua_string)

    device_family = parsed_ua["device"]["family"]
    if device_family in ("iPhone", "Android", "iPad"):
        device_type = "mobile"
    elif device_family == "Other":
        device_type = "desktop"
    else:
        device_type = "mobile"

    os_family = parsed_ua["os"]["family"]
    referrer = request.headers.get("referer", "")

    try:
        supabase.table("clicks").insert({
            "link_id": link["id"],
            "ip_hash": ip_hash,
            "device_type": device_type,
            "os": os_family,
            "referrer": referrer,
        }).execute()
    except Exception as e:
        print(f"Erro ao registrar clique: {e}")

    destination = link["destination"]
    params = [f"l={link['id']}", f"c={link['client_id']}"]

    if link.get("utm_source"):
        params.append(f"utm_source={link['utm_source']}")
    if link.get("utm_campaign"):
        params.append(f"utm_campaign={link['utm_campaign']}")

    separator = "&" if "?" in destination else "?"
    destination = f"{destination}{separator}{'&'.join(params)}"

    return RedirectResponse(url=destination, status_code=302)
