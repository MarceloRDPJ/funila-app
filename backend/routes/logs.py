from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_supabase
from dependencies import require_client
from typing import Optional

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("")
def list_logs(
    page: int = 1,
    limit: int = 50,
    source: Optional[str] = None,
    level: Optional[str] = None,
    lead_id: Optional[str] = None,
    user_profile: dict = Depends(require_client)
):
    """
    Fetch system logs for the authenticated client.
    Supports filtering by source (webhook, api) and level (error, info).
    """
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    query = supabase.table("logs").select("*", count="exact").eq("client_id", client_id).order("created_at", desc=True)

    if source:
        query = query.eq("source", source)
    if level:
        query = query.eq("level", level)
    if lead_id:
        query = query.eq("lead_id", lead_id)

    start = (page - 1) * limit
    end = start + limit - 1
    query = query.range(start, end)

    try:
        res = query.execute()
        return {
            "data": res.data,
            "total": res.count,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        print(f"Error fetching logs: {e}")
        # Return empty list instead of crashing if table doesn't exist yet
        return {"data": [], "total": 0, "page": page, "limit": limit}
