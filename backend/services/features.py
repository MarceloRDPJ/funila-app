from database import get_supabase

def check_feature(client_id: str, flag_name: str) -> bool:
    """
    Verifica se uma feature flag está ativa para o cliente.
    """
    supabase = get_supabase()

    # 1. Check Global Default / Plan Limits?
    # For now, just DB table check.

    try:
        res = supabase.table("feature_flags").select("enabled").eq("client_id", client_id).eq("flag_name", flag_name).single().execute()
        if res.data:
            return res.data["enabled"]
    except Exception:
        pass

    return False
