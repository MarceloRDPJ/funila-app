import hashlib
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from database import get_supabase
from ua_parser import user_agent_parser
from datetime import datetime

router = APIRouter(tags=["Tracker"])

@router.get("/t/{slug}")
def track_and_redirect(slug: str, request: Request):
    supabase = get_supabase()

    # 1. Fetch Link
    response = supabase.table("links").select("*").eq("slug", slug).eq("active", True).single().execute()

    if not response.data:
        # Fallback or 404
        raise HTTPException(status_code=404, detail="Link not found or inactive")

    link = response.data

    # 2. Capture Analytics Data
    ip = request.client.host or "0.0.0.0"
    # Anonymize IP (SHA-256)
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()

    ua_string = request.headers.get("user-agent", "")
    parsed_ua = user_agent_parser.Parse(ua_string)

    device_type = "desktop"
    if parsed_ua['device']['family'] != 'Other':
        device_type = "mobile" # Simplified check, can be improved

    os_family = parsed_ua['os']['family']
    referrer = request.headers.get("referer", "")

    # 3. Insert Click Record (Async ideally, but blocking here for simplicity)
    try:
        supabase.table("clicks").insert({
            "link_id": link['id'],
            "ip_hash": ip_hash,
            "device_type": device_type,
            "os": os_family,
            "referrer": referrer,
            # 'city' would require GeoIP lookup, skipping for now as per instructions (or use a service later)
        }).execute()
    except Exception as e:
        print(f"Error logging click: {e}")
        # Don't block redirect if logging fails

    # 4. Redirect
    destination = link['destination']

    # Append UTMs if present in link config but not in destination
    # Simplified logic: If destination has no query params, add ?. Else &
    # Actually, the frontend squeeze page captures UTMs from the URL it is visited with.
    # The tracker redirects TO the squeeze page. So we should pass the UTMs from the link config to the destination URL.

    params = []
    # Pass Link ID and Client ID for the frontend to capture
    params.append(f"l={link['id']}")
    params.append(f"c={link['client_id']}")

    if link.get('utm_source'):
        params.append(f"utm_source={link['utm_source']}")
    if link.get('utm_campaign'):
        params.append(f"utm_campaign={link['utm_campaign']}")

    if params:
        separator = "&" if "?" in destination else "?"
        destination = f"{destination}{separator}{'&'.join(params)}"

    return RedirectResponse(url=destination, status_code=302)
