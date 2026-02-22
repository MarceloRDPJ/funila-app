-- ==============================================================================
-- FUNILA - Guia Definitivo de Correção 2026
-- Script de Migração de Banco de Dados (Schema Fixes)
-- Baseado no Capítulo 3 e 9 do documento.
-- Execute este script no SQL Editor do Supabase para corrigir a estrutura do banco.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. PASSO 1 — Colunas ausentes em leads (Capítulo 3.1)
-- ------------------------------------------------------------------------------
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_content    TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS device_type    TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS step_reached   INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS external_score INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS creative_id    UUID;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMPTZ DEFAULT NOW();

-- Atualizar constraint de status para incluir novos estados
ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_status_check;
ALTER TABLE leads ADD CONSTRAINT leads_status_check
  CHECK (status IN ('hot','warm','cold','abandoned',
                    'negotiation','converted','trash','started'));

-- ------------------------------------------------------------------------------
-- 2. PASSO 2 — Colunas ausentes em links (Capítulo 3.2)
-- ------------------------------------------------------------------------------
ALTER TABLE links ADD COLUMN IF NOT EXISTS funnel_type  TEXT DEFAULT 'form';
ALTER TABLE links ADD COLUMN IF NOT EXISTS capture_url  TEXT;
ALTER TABLE links ADD COLUMN IF NOT EXISTS utm_content  TEXT;
ALTER TABLE links ADD COLUMN IF NOT EXISTS utm_medium   TEXT;
ALTER TABLE links ADD COLUMN IF NOT EXISTS metadata     JSONB DEFAULT '{}';

-- ------------------------------------------------------------------------------
-- 3. PASSO 3 — Criar tabelas ausentes (Capítulo 3.3)
-- ------------------------------------------------------------------------------

-- funnel_events (telemetria do formulário)
CREATE TABLE IF NOT EXISTS public.funnel_events (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id  UUID REFERENCES clients(id),
    link_id    UUID REFERENCES links(id),
    session_id TEXT,
    event_name TEXT,
    event_type TEXT,
    step       INTEGER,
    field_key  TEXT,
    metadata   JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_funnel_link ON funnel_events(link_id);

-- logs (auditoria e erros)
CREATE TABLE IF NOT EXISTS public.logs (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id  UUID REFERENCES clients(id),
    lead_id    UUID REFERENCES leads(id),
    level      TEXT NOT NULL,
    source     TEXT NOT NULL,
    message    TEXT NOT NULL,
    metadata   JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- webhooks
CREATE TABLE IF NOT EXISTS public.webhooks (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id  UUID REFERENCES clients(id) NOT NULL,
    url        TEXT NOT NULL,
    active     BOOLEAN DEFAULT true,
    events     TEXT[] DEFAULT '{lead_created}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- subscriptions
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id         UUID REFERENCES clients(id) NOT NULL,
    asaas_customer_id TEXT,
    asaas_sub_id      TEXT UNIQUE,
    plan              TEXT,
    status            TEXT DEFAULT 'active',
    mrr_cents         INTEGER DEFAULT 0,
    next_billing_at   TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- feature_flags
CREATE TABLE IF NOT EXISTS public.feature_flags (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id  UUID REFERENCES clients(id),
    flag_name  TEXT NOT NULL,
    enabled    BOOLEAN DEFAULT false,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, flag_name)
);

-- ------------------------------------------------------------------------------
-- 4. PASSO 4 — Colunas extras em clients (Capítulo 3.4)
-- ------------------------------------------------------------------------------
ALTER TABLE clients ADD COLUMN IF NOT EXISTS brand_logo_url      TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS brand_primary_color TEXT DEFAULT '#2563EB';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS brand_name          TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS zapi_instance       TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS zapi_token          TEXT;

-- ------------------------------------------------------------------------------
-- 5. PASSO 5 — Função RPC increment_creative_metric (Capítulo 3.5)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION increment_creative_metric(
    p_client_id     UUID,
    p_utm_content   TEXT,
    p_step          INTEGER,
    p_is_click      BOOLEAN DEFAULT false,
    p_is_conversion BOOLEAN DEFAULT false
) RETURNS void AS $$
BEGIN
    -- Stub MVP: retorna sem erro se não houver criativos ou tabela de métricas
    -- Isso evita erros no frontend se a tabela de métricas ainda não existir
    RETURN;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ------------------------------------------------------------------------------
-- 6. Helper para Setup de Cliente (Capítulo 9)
-- ------------------------------------------------------------------------------
-- Execute este bloco SOMENTE quando criar um novo cliente, substituindo o UUID.
-- Exemplo de uso:
/*
DO $$
DECLARE
  v_client_id UUID := 'UUID-DO-CLIENTE-AQUI'; -- Substitua pelo ID real
  v_field     RECORD;
  v_order     INTEGER := 1;
BEGIN
  FOR v_field IN
    SELECT id FROM form_fields
    WHERE field_key IN ('full_name','phone','has_clt','clt_years','income_range',
                        'tried_financing','cpf')
    ORDER BY CASE field_key
      WHEN 'full_name'       THEN 1
      WHEN 'phone'           THEN 2
      WHEN 'has_clt'         THEN 3
      WHEN 'clt_years'       THEN 4
      WHEN 'income_range'    THEN 5
      WHEN 'tried_financing' THEN 6
      WHEN 'cpf'             THEN 7
    END
  LOOP
    INSERT INTO client_form_config
      (client_id, field_id, required, active, order_position)
    VALUES
      (v_client_id, v_field.id,
       v_field.id IN (SELECT id FROM form_fields WHERE field_key IN ('full_name','phone')),
       true, v_order)
    ON CONFLICT (client_id, field_id) DO NOTHING;
    v_order := v_order + 1;
  END LOOP;
END $$;
*/
