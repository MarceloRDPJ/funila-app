from fastapi import APIRouter, Depends
from database import get_supabase
from dependencies import require_client
from datetime import datetime, timedelta

router = APIRouter(tags=["Dashboard"])

@router.get("/metrics")
def get_dashboard_metrics(
    period: str = "today",
    link_id: str = None,
    user_profile: dict = Depends(require_client)
):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    now = datetime.now()
    start_date = None
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)

    clicks_query = supabase.table("clicks")\
        .select("id, created_at, link_id, links!inner(client_id)")\
        .eq("links.client_id", client_id)

    leads_query = supabase.table("leads")\
        .select("id, status, created_at, link_id")\
        .eq("client_id", client_id)

    if link_id:
        clicks_query = clicks_query.eq("link_id", link_id)
        leads_query  = leads_query.eq("link_id", link_id)

    if start_date:
        clicks_query = clicks_query.gte("created_at", start_date.isoformat())
        leads_query  = leads_query.gte("created_at", start_date.isoformat())

    clicks = clicks_query.execute().data
    leads  = leads_query.execute().data

    total_clicks    = len(clicks)
    total_leads     = len(leads)
    hot_leads       = sum(1 for l in leads if l["status"] == "hot")
    warm_leads      = sum(1 for l in leads if l["status"] == "warm")
    cold_leads      = sum(1 for l in leads if l["status"] == "cold")
    converted       = sum(1 for l in leads if l["status"] == "converted")
    conversion_rate = round((total_leads / total_clicks) * 100, 2) if total_clicks > 0 else 0

    daily_leads = {}
    for l in leads:
        date_str = l["created_at"][:10]
        daily_leads[date_str] = daily_leads.get(date_str, 0) + 1

    chart_data = [{"date": k, "count": v} for k, v in sorted(daily_leads.items())]

    return {
        "metrics": {
            "clicks":          total_clicks,
            "leads":           total_leads,
            "hot_leads":       hot_leads,
            "conversion_rate": conversion_rate
        },
        "breakdown": {
            "hot":       hot_leads,
            "warm":      warm_leads,
            "cold":      cold_leads,
            "converted": converted
        },
        "chart_data": chart_data
    }


@router.get("/funnel")
def get_funnel_stats(
    period: str = "today",
    link_id: str = None,
    user_profile: dict = Depends(require_client)
):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    now = datetime.now()
    start_date = None
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)

    # Buscar eventos de funil
    # Filtrar por link_id se fornecido, ou links do cliente
    # Como não temos client_id direto em funnel_events, precisamos filtrar pelos links do cliente

    # 1. Buscar IDs dos links do cliente
    links_query = supabase.table("links").select("id").eq("client_id", client_id)
    if link_id:
        links_query = links_query.eq("id", link_id)

    links_res = links_query.execute()
    client_link_ids = [l["id"] for l in links_res.data]

    if not client_link_ids:
        return {"step_1": 0, "step_2": 0, "step_3": 0, "converted": 0}

    # 2. Buscar eventos para esses links
    events_query = supabase.table("funnel_events")\
        .select("session_id, event_type, step")\
        .in_("link_id", client_link_ids)

    if start_date:
        events_query = events_query.gte("created_at", start_date.isoformat())

    events_data = events_query.execute().data

    # 3. Processar contagem única por sessão
    # step_1: step_start (step=1)
    # step_2: step_start (step=2)
    # step_3: step_start (step=3)
    # converted: form_submit

    sessions_s1 = set()
    sessions_s2 = set()
    sessions_s3 = set()
    sessions_conv = set()

    for e in events_data:
        etype = e["event_type"]
        step  = e.get("step")
        sid   = e["session_id"]

        if etype == "step_start":
            if step == 1: sessions_s1.add(sid)
            elif step == 2: sessions_s2.add(sid)
            elif step == 3: sessions_s3.add(sid)
        elif etype == "form_submit":
            sessions_conv.add(sid)

    count_s1 = len(sessions_s1)
    count_s2 = len(sessions_s2)
    count_s3 = len(sessions_s3)
    count_cv = len(sessions_conv)

    # Taxas de conversão relativas ao passo anterior
    rate_s1_s2 = round((count_s2 / count_s1 * 100), 1) if count_s1 > 0 else 0
    rate_s2_s3 = round((count_s3 / count_s2 * 100), 1) if count_s2 > 0 else 0
    rate_s3_cv = round((count_cv / count_s3 * 100), 1) if count_s3 > 0 else 0

    return {
        "counts": {
            "step_1": count_s1,
            "step_2": count_s2,
            "step_3": count_s3,
            "converted": count_cv
        },
        "rates": {
            "step_1_to_2": rate_s1_s2,
            "step_2_to_3": rate_s2_s3,
            "step_3_to_conv": rate_s3_cv
        }
    }
