-- ============================================================
-- FUNILA — Schema completo
-- Execute no SQL Editor do Supabase na ordem abaixo
-- ============================================================

-- 1. Tabela de usuários do sistema (vincula auth.users ao cliente)
CREATE TABLE IF NOT EXISTS public.users (
    id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email      TEXT NOT NULL,
    role       TEXT NOT NULL DEFAULT 'client' CHECK (role IN ('master', 'client')),
    client_id  UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Clientes (corretores / empresas)
CREATE TABLE IF NOT EXISTS clients (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    plan       TEXT DEFAULT 'solo' CHECK (plan IN ('solo', 'pro', 'agency')),
    whatsapp   TEXT,
    active     BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Links de rastreamento
CREATE TABLE IF NOT EXISTS links (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id    UUID REFERENCES clients(id) ON DELETE CASCADE,
    slug         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    destination  TEXT NOT NULL,
    utm_source   TEXT,
    utm_campaign TEXT,
    active       BOOLEAN DEFAULT true,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_links_slug   ON links(slug);
CREATE INDEX IF NOT EXISTS idx_links_client ON links(client_id);

-- 4. Cliques (anonimizados)
CREATE TABLE IF NOT EXISTS clicks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    link_id     UUID REFERENCES links(id) ON DELETE CASCADE,
    ip_hash     TEXT,
    device_type TEXT CHECK (device_type IN ('mobile', 'desktop', 'tablet')),
    os          TEXT,
    referrer    TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_clicks_link ON clicks(link_id);
CREATE INDEX IF NOT EXISTS idx_clicks_date ON clicks(created_at);

-- 5. Leads qualificados
CREATE TABLE IF NOT EXISTS leads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
    link_id         UUID REFERENCES links(id),
    name            TEXT NOT NULL,
    phone           TEXT NOT NULL,
    cpf_encrypted   TEXT,
    internal_score  INTEGER DEFAULT 0,
    external_score  INTEGER DEFAULT 0,
    serasa_score    INTEGER,
    status          TEXT DEFAULT 'warm' CHECK (status IN ('hot','warm','cold','converted')),
    utm_source      TEXT,
    utm_campaign    TEXT,
    utm_medium      TEXT,
    consent_given   BOOLEAN DEFAULT false,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_leads_client ON leads(client_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_date   ON leads(created_at);

-- 6. Campos disponíveis para formulários
CREATE TABLE IF NOT EXISTS form_fields (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_key       TEXT UNIQUE NOT NULL,
    label_default   TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN ('text','phone','select','checkbox','cpf')),
    required_default BOOLEAN DEFAULT false,
    options         JSONB,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Configuração do formulário por cliente
CREATE TABLE IF NOT EXISTS client_form_config (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id      UUID REFERENCES clients(id) ON DELETE CASCADE,
    field_id       UUID REFERENCES form_fields(id) ON DELETE CASCADE,
    label_custom   TEXT,
    required       BOOLEAN DEFAULT false,
    active         BOOLEAN DEFAULT true,
    order_position INTEGER DEFAULT 0,
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(client_id, field_id)
);

-- 8. Respostas individuais por lead
CREATE TABLE IF NOT EXISTS lead_responses (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id        UUID REFERENCES leads(id) ON DELETE CASCADE,
    field_id       UUID REFERENCES form_fields(id),
    response_value TEXT,
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Eventos / timeline do lead
CREATE TABLE IF NOT EXISTS events (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id    UUID REFERENCES leads(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    metadata   JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_events_lead ON events(lead_id);

-- ============================================================
-- RLS — Row Level Security
-- ============================================================
ALTER TABLE leads  ENABLE ROW LEVEL SECURITY;
ALTER TABLE links  ENABLE ROW LEVEL SECURITY;
ALTER TABLE clicks ENABLE ROW LEVEL SECURITY;

-- Clientes veem apenas seus próprios dados
CREATE POLICY "client_leads" ON leads FOR ALL
    USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));

CREATE POLICY "client_links" ON links FOR ALL
    USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));

-- ============================================================
-- Dados iniciais — campos padrão do formulário
-- ============================================================
INSERT INTO form_fields (field_key, label_default, type, required_default, options) VALUES
    ('full_name',       'Nome completo',            'text',     true,  NULL),
    ('phone',           'WhatsApp com DDD',          'phone',    true,  NULL),
    ('has_clt',         'Tem carteira assinada (CLT)?','select', false, '["Sim","Não"]'),
    ('clt_years',       'Há quanto tempo?',          'select',   false, '["Menos de 1 ano","1 a 2 anos","2 a 3 anos","Mais de 3 anos"]'),
    ('income_range',    'Renda mensal aproximada',   'select',   false, '["Abaixo de R$ 1.500","R$ 1.500 - R$ 3.000","R$ 3.000 - R$ 5.000","Acima de R$ 5.000"]'),
    ('tried_financing', 'Já tentou financiamento?',  'select',   false, '["Sim","Não"]'),
    ('cpf',             'CPF (opcional)',             'cpf',      false, NULL)
ON CONFLICT (field_key) DO NOTHING;

-- ============================================================
-- Trigger — popula public.users ao criar auth user
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.users (id, email, role, client_id)
    VALUES (NEW.id, NEW.email, 'client', NULL)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
