import hashlib
import os
import uuid
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from database import get_supabase
from ua_parser import user_agent_parser

router = APIRouter(tags=["Tracker"])

# URLs base configuráveis via env
FORM_BASE_URL    = os.getenv("FORM_BASE_URL",    "https://app.funila.com.br/frontend/form/index.html")
LANDING_BASE_URL = os.getenv("LANDING_BASE_URL", "https://app.funila.com.br/frontend/landing/index.html")
PROXY_BASE_URL   = os.getenv("PROXY_BASE_URL",   "https://funila-app.onrender.com/proxy")


# ─── Modelo para evento de funil ───────────────────────────────────────────────
class FunnelEvent(BaseModel):
    session_id:  str
    link_id:     str
    event_type:  str           # page_view, step_start, field_focus, field_blur,
                               # step_complete, form_abandon, form_submit,
                               # capture_interact, capture_exit
    step:        Optional[int] = None
    field_key:   Optional[str] = None
    metadata:    Optional[dict] = None


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _parse_device(ua_string: str) -> tuple[str, str]:
    """Retorna (device_type, os_family)"""
    parsed = user_agent_parser.Parse(ua_string)
    family = parsed["device"]["family"]
    if family in ("iPhone", "Android", "iPad"):
        device = "mobile"
    elif family == "Other":
        device = "desktop"
    else:
        device = "mobile"
    return device, parsed["os"]["family"]


def _build_params(link: dict, extra: dict = {}) -> str:
    parts = [
        f"l={link['id']}",
        f"c={link['client_id']}",
    ]
    if link.get("utm_source"):
        parts.append(f"utm_source={link['utm_source']}")
    if link.get("utm_campaign"):
        parts.append(f"utm_campaign={link['utm_campaign']}")
    if link.get("utm_medium"):
        parts.append(f"utm_medium={link['utm_medium']}")
    if link.get("utm_content"):
        parts.append(f"utm_content={link['utm_content']}")
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    return "&".join(parts)


# ─── Rota principal do tracker ─────────────────────────────────────────────────
@router.get("/t/{slug}")
def track_and_redirect(slug: str, request: Request):
    supabase = get_supabase()

    res = supabase.table("links").select("*").eq("slug", slug).eq("active", True).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Link não encontrado")
    link = res.data

    # Anonimiza IP (LGPD)
    ip      = request.client.host or "0.0.0.0"
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()

    # Parse dispositivo
    ua_str = request.headers.get("user-agent", "")
    device_type, os_family = _parse_device(ua_str)
    referrer = request.headers.get("referer", "")

    # Gera session_id para rastreio ponta a ponta
    session_id = str(uuid.uuid4())

    # Registra o clique
    try:
        supabase.table("clicks").insert({
            "link_id":     link["id"],
            "ip_hash":     ip_hash,
            "device_type": device_type,
            "os":          os_family,
            "referrer":    referrer,
        }).execute()
    except Exception as e:
        print(f"Erro ao registrar clique: {e}")

    # Cria sessão de visitante para rastreio ponta a ponta
    try:
        supabase.table("visitor_sessions").insert({
            "session_id":   session_id,
            "link_id":      link["id"],
            "ip_hash":      ip_hash,
            "device_type":  device_type,
            "os":           os_family,
            "referrer":     referrer,
            "utm_source":   link.get("utm_source"),
            "utm_campaign": link.get("utm_campaign"),
        }).execute()
    except Exception as e:
        print(f"Erro ao criar sessão: {e}")

    # ── Decide o destino baseado no funnel_type ──────────────────────────────
    funnel_type = link.get("funnel_type", "form")
    params      = _build_params(link, {"sid": session_id})

    if funnel_type == "form":
        # → Formulário nativo Funila
        redirect_url = f"{FORM_BASE_URL}?{params}"

    elif funnel_type == "landing":
        # → Página padrão Funila (alta conversão, neuromarketing)
        redirect_url = f"{LANDING_BASE_URL}?{params}"

    elif funnel_type == "capture":
        # → Proxy/clonador da página própria do cliente
        # A página de captura é servida via /proxy/{slug}
        # que injeta o script de rastreio antes de servir o conteúdo clonado
        redirect_url = f"{PROXY_BASE_URL}/{slug}?{params}"

    else:
        # Fallback: formulário nativo
        redirect_url = f"{FORM_BASE_URL}?{params}"

    return RedirectResponse(url=redirect_url, status_code=302)


# ─── Endpoint: registra evento de funil ────────────────────────────────────────
@router.post("/funnel/event")
async def register_funnel_event(event: FunnelEvent):
    """
    Recebe eventos do frontend em tempo real.
    Permite saber: onde o lead parou, qual campo abandonou, quanto tempo ficou.
    Sem autenticação — é chamado pelo formulário público.
    """
    supabase = get_supabase()

    try:
        supabase.table("funnel_events").insert({
            "link_id":    event.link_id,
            "session_id": event.session_id,
            "event_type": event.event_type,
            "step":       event.step,
            "field_key":  event.field_key,
            "metadata":   event.metadata or {},
        }).execute()

        # Atualiza last_seen da sessão
        supabase.table("visitor_sessions")\
            .update({"last_seen_at": "now()"})\
            .eq("session_id", event.session_id)\
            .execute()

        return {"ok": True}
    except Exception as e:
        print(f"Erro ao registrar evento: {e}")
        return JSONResponse(status_code=500, content={"ok": False})


# ─── Endpoint: proxy/clonador de página de captura ────────────────────────────
@router.get("/proxy/{slug}")
async def proxy_capture_page(slug: str, request: Request):
    """
    Serve a página de captura do cliente com script de rastreio injetado.
    Clona a URL configurada em links.capture_url e injeta o tracker JS.
    """
    supabase = get_supabase()

    res = supabase.table("links").select("*").eq("slug", slug).eq("active", True).single().execute()
    if not res.data or res.data.get("funnel_type") != "capture":
        raise HTTPException(status_code=404, detail="Página não encontrada")

    link        = res.data
    capture_url = link.get("capture_url")
    if not capture_url:
        raise HTTPException(status_code=400, detail="URL de captura não configurada")

    # Parâmetros passados pela URL (session_id, link_id, etc.)
    link_id    = request.query_params.get("l", link["id"])
    client_id  = request.query_params.get("c", link["client_id"])
    session_id = request.query_params.get("sid", str(uuid.uuid4()))

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.get(capture_url, headers={
                "User-Agent": request.headers.get("user-agent", "Mozilla/5.0")
            })
            html = r.text
    except Exception as e:
        print(f"Erro ao clonar página: {e}")
        raise HTTPException(status_code=502, detail="Não foi possível acessar a página de captura")

    # Script de rastreio injetado antes do </body>
    tracker_script = f"""
<script>
(function() {{
    var _fln = {{
        linkId:    "{link_id}",
        clientId:  "{client_id}",
        sessionId: "{session_id}",
        apiUrl:    "https://funila-app.onrender.com",
        startTime: Date.now(),
    }};

    function _send(type, meta) {{
        fetch(_fln.apiUrl + "/funnel/event", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{
                session_id: _fln.sessionId,
                link_id:    _fln.linkId,
                event_type: type,
                metadata:   Object.assign({{time_on_page: Date.now() - _fln.startTime}}, meta || {{}})
            }})
        }}).catch(function(){{}});
    }}

    // Rastreia visualização
    _send("capture_interact", {{url: window.location.href}});

    // Rastreia saída
    window.addEventListener("beforeunload", function() {{
        _send("capture_exit", {{time_spent: Date.now() - _fln.startTime}});
    }});

    // Rastreia cliques em formulários e botões (best-effort)
    document.addEventListener("submit", function(e) {{
        _send("form_submit", {{form_id: e.target.id || "unknown"}});
    }});

    // Rastreia cliques em links externos
    document.addEventListener("click", function(e) {{
        var a = e.target.closest("a");
        if (a && a.href) _send("capture_interact", {{clicked_href: a.href}});
    }});
}})();
</script>
"""

    # Injeta antes do </body>
    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        html = html[:idx] + tracker_script + html[idx:]
    else:
        html += tracker_script

    return HTMLResponse(content=html, status_code=200)
