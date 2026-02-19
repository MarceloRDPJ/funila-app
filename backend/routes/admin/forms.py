from fastapi import APIRouter, HTTPException, Depends, Body
from database import get_supabase
from dependencies import get_current_user_role, require_client

router = APIRouter(prefix="/admin/forms", tags=["Admin Forms"])

@router.get("/")
def get_form_config(user_profile: dict = Depends(require_client)):
    """
    Get the current form configuration for the logged-in client.
    Includes all available fields (active and inactive).
    """
    client_id = user_profile['client_id']
    if not client_id:
        raise HTTPException(status_code=400, detail="User is not associated with a client")

    supabase = get_supabase()

    # 1. Get all master fields
    all_fields_res = supabase.table("form_fields").select("*").execute()
    all_fields = all_fields_res.data

    # 2. Get current client config
    client_config_res = supabase.table("client_form_config").select("*").eq("client_id", client_id).execute()
    client_config_map = {item['field_id']: item for item in client_config_res.data}

    # 3. Merge
    result = []
    for field in all_fields:
        config = client_config_map.get(field['id'], {})
        result.append({
            "field_id": field['id'],
            "field_key": field['field_key'],
            "label_default": field['label_default'],
            "label_custom": config.get('label_custom'),
            "type": field['type'],
            "required_default": field['required_default'],
            "required": config.get('required', field['required_default']), # default to master setting if not set
            "active": config.get('active', False),
            "order": config.get('order_position', 99),
            "options": field.get('options')
        })

    # Sort by order
    result.sort(key=lambda x: x['order'])

    return result

@router.post("/")
def update_form_config(
    user_profile: dict = Depends(require_client),
    config: list = Body(...)
):
    """
    Update the form configuration.
    Expects a list of field configs.
    """
    client_id = user_profile['client_id']
    supabase = get_supabase()

    # Upsert configs
    upsert_data = []
    for item in config:
        upsert_data.append({
            "client_id": client_id,
            "field_id": item['field_id'],
            "label_custom": item.get('label_custom'),
            "required": item.get('required', False),
            "active": item.get('active', False),
            "order_position": item.get('order', 99)
        })

    try:
        # Supabase upsert requires unique constraint on (client_id, field_id) which we have.
        supabase.table("client_form_config").upsert(upsert_data, on_conflict="client_id, field_id").execute()
        return {"status": "success", "message": "Form configuration updated"}
    except Exception as e:
        print(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
