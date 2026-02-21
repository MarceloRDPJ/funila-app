from fastapi import APIRouter, HTTPException, Depends, Body
from database import get_supabase
from dependencies import require_client

router = APIRouter(prefix="/admin/forms", tags=["Admin Forms"])

@router.get("/")
def get_form_config(user_profile: dict = Depends(require_client)):
    client_id = user_profile["client_id"]
    if not client_id:
        raise HTTPException(status_code=400, detail="Usuário sem cliente vinculado")

    supabase = get_supabase()

    all_fields = supabase.table("form_fields").select("*").execute().data
    client_config_res = supabase.table("client_form_config").select("*").eq("client_id", client_id).execute()
    client_config_map = {item["field_id"]: item for item in client_config_res.data}

    result = []
    for field in all_fields:
        config = client_config_map.get(field["id"], {})
        result.append({
            "field_id":      field["id"],
            "field_key":     field["field_key"],
            "label_default": field["label_default"],
            "label_custom":  config.get("label_custom"),
            "type":          field["type"],
            "required":      config.get("required", field["required_default"]),
            "active":        config.get("active", False),
            "order":         config.get("order_position", 99),
            "options":       field.get("options")
        })

    result.sort(key=lambda x: x["order"])
    return result

@router.post("/")
def update_form_config(
    user_profile: dict = Depends(require_client),
    config: list = Body(...)
):
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    upsert_data = [{
        "client_id":      client_id,
        "field_id":       item["field_id"],
        "label_custom":   item.get("label_custom"),
        "required":       item.get("required", False),
        "active":         item.get("active", False),
        "order_position": item.get("order", 99)
    } for item in config]

    try:
        supabase.table("client_form_config").upsert(upsert_data, on_conflict="client_id, field_id").execute()
        return {"status": "success"}
    except Exception as e:
        print(f"Erro ao salvar config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
