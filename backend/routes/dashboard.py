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
