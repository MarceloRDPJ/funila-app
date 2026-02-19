from fastapi import APIRouter, HTTPException, Depends
from database import get_supabase

router = APIRouter(tags=["Public Forms"])

@router.get("/forms/config/{client_id}")
def get_public_form_config(client_id: str):
    """
    Fetches the active form configuration for a given client.
    Used by the Squeeze Page to render the form dynamically.
    """
    supabase = get_supabase()

    # 1. Verify Client Exists & Active
    client_res = supabase.table("clients").select("id, name, active, plan").eq("id", client_id).single().execute()
    if not client_res.data or not client_res.data['active']:
        raise HTTPException(status_code=404, detail="Client not found or inactive")

    client_data = client_res.data

    # 2. Fetch Form Config Joined with Form Fields
    # Supabase Join Syntax: client_form_config(..., form_fields(...))
    try:
        response = supabase.table("client_form_config")\
            .select("*, form_fields(*)")\
            .eq("client_id", client_id)\
            .eq("active", True)\
            .order("order_position")\
            .execute()

        fields = []
        for item in response.data:
            field_def = item['form_fields']
            fields.append({
                "field_id": field_def['id'],
                "field_key": field_def['field_key'],
                "type": field_def['type'],
                "label": item['label_custom'] or field_def['label_default'],
                "required": item['required'],
                "options": field_def.get('options'),
                "order": item['order_position']
            })

        return {
            "client_name": client_data['name'],
            "plan": client_data['plan'],
            "fields": fields
        }

    except Exception as e:
        print(f"Error fetching form config: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
