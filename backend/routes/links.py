from fastapi import APIRouter, Depends, HTTPException
from database import get_supabase
from dependencies import require_client
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter(tags=["Links"])

class LinkCreate(BaseModel):
    name: str
    destination: str
    slug: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None

@router.get("/links")
def list_links(user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase = get_supabase()
    return supabase.table("links").select("*").eq("client_id", client_id).order("created_at", desc=True).execute().data

@router.post("/links")
def create_link(link: LinkCreate, user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    slug = link.slug
    if not slug:
        base = link.name.lower().replace(" ", "-")
        base = "".join(c for c in base if c.isalnum() or c == "-")
        slug = f"{base}-{str(uuid.uuid4())[:4]}"

    existing = supabase.table("links").select("id").eq("slug", slug).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Slug já existe")

    data = link.dict()
    data["slug"] = slug
    data["client_id"] = client_id

    return supabase.table("links").insert(data).execute().data[0]

@router.delete("/links/{link_id}")
def delete_link(link_id: str, user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    supabase = get_supabase()
    supabase.table("links").delete().eq("id", link_id).eq("client_id", client_id).execute()
    return {"status": "deleted"}
