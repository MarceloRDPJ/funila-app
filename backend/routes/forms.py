from fastapi import APIRouter, HTTPException
from database import get_supabase

router = APIRouter(tags=["Public Forms"])

@router.get("/forms/config/{client_id}")
def get_public_form_config(client_id: str):
    supabase = get_supabase()

    client_res = supabase.table("clients").select("id, name, active, plan").eq("id", client_id).single().execute()
    if not client_res.data or not client_res.data["active"]:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    client_data = client_res.data

    try:
        response = supabase.table("client_form_config")\
            .select("*, form_fields(*)")\
            .eq("client_id", client_id)\
            .eq("active", True)\
            .order("order_position")\
            .execute()

        fields = []
        for item in response.data:
            field_def = item["form_fields"]
            fields.append({
                "field_id":  field_def["id"],
                "field_key": field_def["field_key"],
                "type":      field_def["type"],
                "label":     item["label_custom"] or field_def["label_default"],
                "required":  item["required"],
                "options":   field_def.get("options"),
                "order":     item["order_position"]
            })

        return {
            "client_name": client_data["name"],
            "plan":        client_data["plan"],
            "fields":      fields
        }
    except Exception as e:
        print(f"Erro ao buscar config do formulário: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")
