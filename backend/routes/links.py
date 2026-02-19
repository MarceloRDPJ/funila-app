from fastapi import APIRouter, Depends, HTTPException, Body
from database import get_supabase
from dependencies import require_client
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter(tags=["Links"])

class LinkCreate(BaseModel):
    name: str
    destination: str
    slug: Optional[str] = None # If empty, auto-generate
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None

@router.get("/links")
def list_links(user_profile: dict = Depends(require_client)):
    client_id = user_profile['client_id']
    supabase = get_supabase()

    # Get links with click count (using a subquery or separate query since Supabase-py is limited)
    # Simple fetch for now
    links = supabase.table("links").select("*").eq("client_id", client_id).order("created_at", desc=True).execute()

    return links.data

@router.post("/links")
def create_link(link: LinkCreate, user_profile: dict = Depends(require_client)):
    client_id = user_profile['client_id']
    supabase = get_supabase()

    slug = link.slug
    if not slug:
        # Auto generate slug based on name or UUID
        slug = link.name.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:4]

    # Check uniqueness
    existing = supabase.table("links").select("id").eq("slug", slug).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Slug already exists")

    data = link.dict()
    data['slug'] = slug
    data['client_id'] = client_id

    res = supabase.table("links").insert(data).execute()
    return res.data[0]

@router.delete("/links/{link_id}")
def delete_link(link_id: str, user_profile: dict = Depends(require_client)):
    client_id = user_profile['client_id']
    supabase = get_supabase()

    # Verify ownership via RLS or explicit check
    # RLS should handle it, but explicit check returns 404/403 nicely
    res = supabase.table("links").delete().eq("id", link_id).eq("client_id", client_id).execute()
    return {"status": "deleted"}
