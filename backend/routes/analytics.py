import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from database import get_supabase
from dependencies import require_client

router = APIRouter(tags=["Analytics"])

@router.get("/metrics/retention")
def get_retention_metrics(user_profile: dict = Depends(require_client)):
    """
    Retorna métricas calculadas por criativo (utm_content).
    Fórmulas obrigatórias:
    - Retenção etapa 1: step_1 / total_clicks
    - Retenção etapa 2: step_2 / step_1
    - Retenção etapa 3: step_3 / step_2
    - Conversão final: completed / total_clicks
    - Taxa de venda: converted / completed
    """
    client_id = user_profile["client_id"]
    supabase = get_supabase()

    # Busca creative_metrics
    try:
        res = supabase.table("creative_metrics").select("*").eq("client_id", client_id).execute()
        metrics = res.data or []

        results = []
        for m in metrics:
            clicks = m.get("total_clicks", 0)
            step_1 = m.get("step_1", 0)
            step_2 = m.get("step_2", 0)
            step_3 = m.get("step_3", 0)
            completed = m.get("completed", 0)
            converted = m.get("converted", 0)

            # Cálculos (evitar divisão por zero)
            def safe_div(n, d):
                return round(n / d, 4) if d > 0 else 0.0

            retention_1 = safe_div(step_1, clicks)
            retention_2 = safe_div(step_2, step_1)
            retention_3 = safe_div(step_3, step_2)
            final_conversion = safe_div(completed, clicks)
            sales_rate = safe_div(converted, completed)

            results.append({
                "utm_content": m.get("utm_content", "N/A"),
                "clicks": clicks,
                "step_1": step_1,
                "step_2": step_2,
                "step_3": step_3,
                "completed": completed,
                "converted": converted,
                "retention_1": retention_1,
                "retention_2": retention_2,
                "retention_3": retention_3,
                "final_conversion": final_conversion,
                "sales_rate": sales_rate
            })

        return results

    except Exception as e:
        print(f"Erro retention metrics: {e}")
        return []

@router.get("/metrics/abandonment")
def get_abandonment_metrics(user_profile: dict = Depends(require_client)):
    """
    Taxa de abandono por etapa global.
    Calculado como inverso da retenção.
    """
    # Reuse logic from leads.py but based on creative_metrics aggregation if possible?
    # Or keep the simplified one from leads.py?
    # Module 5 says "Todos com cálculo explícito".
    # Let's aggregate creative_metrics for global view.

    client_id = user_profile["client_id"]
    supabase = get_supabase()

    try:
        res = supabase.table("creative_metrics").select("*").eq("client_id", client_id).execute()
        metrics = res.data or []

        total_clicks = sum(m.get("total_clicks", 0) for m in metrics)
        total_step_1 = sum(m.get("step_1", 0) for m in metrics)
        total_step_2 = sum(m.get("step_2", 0) for m in metrics)
        total_step_3 = sum(m.get("step_3", 0) for m in metrics)

        def drop_rate(curr, prev):
            if prev == 0: return 0.0
            return round((prev - curr) / prev, 4)

        return {
            "step_1_drop_rate": drop_rate(total_step_1, total_clicks),
            "step_2_drop_rate": drop_rate(total_step_2, total_step_1),
            "step_3_drop_rate": drop_rate(total_step_3, total_step_2)
        }

    except Exception as e:
        print(f"Erro abandonment metrics: {e}")
        return {
            "step_1_drop_rate": 0,
            "step_2_drop_rate": 0,
            "step_3_drop_rate": 0
        }
