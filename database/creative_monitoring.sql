-- ==========================================
-- ESTRUTURA COMPLETA DO SISTEMA ENTERPRISE
-- ==========================================

-- Extensão necessária
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Ajuste Leads
ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS utm_content TEXT;
ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS step_reached INTEGER DEFAULT 0;

-- Tabela de Métricas de Criativos
CREATE TABLE IF NOT EXISTS public.creative_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
    utm_content TEXT NOT NULL,
    total_clicks INTEGER DEFAULT 0,
    step_1 INTEGER DEFAULT 0,
    step_2 INTEGER DEFAULT 0,
    step_3 INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    converted INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(client_id, utm_content)
);

CREATE INDEX IF NOT EXISTS idx_creative_metrics_client
ON public.creative_metrics (client_id);

-- Tabela Scanner
CREATE TABLE IF NOT EXISTS public.external_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    page_url TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS
ALTER TABLE public.creative_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.external_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "client_creative_metrics" ON public.creative_metrics;
CREATE POLICY "client_creative_metrics"
ON public.creative_metrics
FOR ALL
USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));

DROP POLICY IF EXISTS "client_external_events" ON public.external_events;
CREATE POLICY "client_external_events"
ON public.external_events
FOR ALL
USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));

-- Função RPC Transacional
CREATE OR REPLACE FUNCTION increment_creative_metric(
    p_client_id UUID,
    p_utm_content TEXT,
    p_step INTEGER,
    p_is_click BOOLEAN DEFAULT FALSE,
    p_is_conversion BOOLEAN DEFAULT FALSE
)
RETURNS void AS $$
BEGIN
    INSERT INTO public.creative_metrics (
        client_id,
        utm_content,
        total_clicks,
        step_1,
        step_2,
        step_3,
        completed,
        converted
    )
    VALUES (
        p_client_id,
        p_utm_content,
        CASE WHEN p_is_click THEN 1 ELSE 0 END,
        CASE WHEN p_step >= 1 THEN 1 ELSE 0 END,
        CASE WHEN p_step >= 2 THEN 1 ELSE 0 END,
        CASE WHEN p_step >= 3 THEN 1 ELSE 0 END,
        CASE WHEN p_step = 99 THEN 1 ELSE 0 END,
        CASE WHEN p_is_conversion THEN 1 ELSE 0 END
    )
    ON CONFLICT (client_id, utm_content)
    DO UPDATE SET
        total_clicks = creative_metrics.total_clicks + CASE WHEN p_is_click THEN 1 ELSE 0 END,
        step_1 = creative_metrics.step_1 + CASE WHEN p_step >= 1 THEN 1 ELSE 0 END,
        step_2 = creative_metrics.step_2 + CASE WHEN p_step >= 2 THEN 1 ELSE 0 END,
        step_3 = creative_metrics.step_3 + CASE WHEN p_step >= 3 THEN 1 ELSE 0 END,
        completed = creative_metrics.completed + CASE WHEN p_step = 99 THEN 1 ELSE 0 END,
        converted = creative_metrics.converted + CASE WHEN p_is_conversion THEN 1 ELSE 0 END;
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public;
