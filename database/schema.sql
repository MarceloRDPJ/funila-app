-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Clients (Tenants)
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'solo' CHECK (plan IN ('solo', 'pro', 'agency')),
    whatsapp TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Users (Role Management - Linked to auth.users)
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT DEFAULT 'client' CHECK (role IN ('master', 'client')),
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Form Fields (Master Definition)
CREATE TABLE form_fields (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_key TEXT UNIQUE NOT NULL, -- e.g., 'full_name', 'cpf', 'income'
    label_default TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('text', 'email', 'phone', 'cpf', 'select', 'radio', 'number', 'date')),
    options JSONB, -- For select/radio (e.g., ["< 1500", "1500-3000"])
    required_default BOOLEAN DEFAULT false,
    used_for_score BOOLEAN DEFAULT false,
    used_for_external_lookup BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Client Form Config (Customization per Client)
CREATE TABLE client_form_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    field_id UUID REFERENCES form_fields(id) ON DELETE CASCADE,
    label_custom TEXT,
    required BOOLEAN DEFAULT false,
    order_position INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(client_id, field_id)
);

-- 5. Links (Campaigns)
CREATE TABLE links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    destination TEXT NOT NULL,
    utm_source TEXT,
    utm_campaign TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_links_slug ON links(slug);
CREATE INDEX idx_links_client ON links(client_id);

-- 6. Clicks (Analytics)
CREATE TABLE clicks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    link_id UUID REFERENCES links(id) ON DELETE CASCADE,
    ip_hash TEXT, -- SHA-256 Anonymized
    device_type TEXT,
    os TEXT,
    referrer TEXT,
    city TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_clicks_link ON clicks(link_id);

-- 7. Leads (Core Data)
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    link_id UUID REFERENCES links(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    cpf_encrypted TEXT, -- AES-256 Encrypted
    internal_score INTEGER DEFAULT 0,
    external_score INTEGER DEFAULT 0, -- From Serasa/Public APIs
    final_score INTEGER GENERATED ALWAYS AS (internal_score + external_score) STORED,
    status TEXT DEFAULT 'warm' CHECK (status IN ('hot', 'warm', 'cold', 'converted')),
    utm_source TEXT,
    utm_campaign TEXT,
    utm_medium TEXT,
    device_type TEXT,
    step_reached INTEGER DEFAULT 1,
    consent_given BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_leads_client ON leads(client_id);
CREATE INDEX idx_leads_status ON leads(status);

-- 8. Lead Responses (Dynamic Form Data)
CREATE TABLE lead_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    field_id UUID REFERENCES form_fields(id) ON DELETE CASCADE,
    response_value TEXT, -- Stored as text, parsed by application
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_lead_responses_lead ON lead_responses(lead_id);

-- 9. Events (Timeline)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, -- 'form_submit', 'whatsapp_click', 'email_alert'
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_events_lead ON events(lead_id);

-- 10. Score Rules (Configurable Scoring Logic)
CREATE TABLE score_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID REFERENCES form_fields(id) ON DELETE CASCADE,
    condition_operator TEXT CHECK (condition_operator IN ('equals', 'contains', 'greater_than', 'less_than')),
    condition_value TEXT NOT NULL,
    points INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Policies (Row Level Security)

-- Enable RLS
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE links ENABLE ROW LEVEL SECURITY;
ALTER TABLE clicks ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_form_config ENABLE ROW LEVEL SECURITY;

-- Helper function to get current user's client_id
CREATE OR REPLACE FUNCTION get_auth_client_id()
RETURNS UUID AS $$
BEGIN
  RETURN (SELECT client_id FROM public.users WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Policies

-- Clients: Master sees all, Client sees own
CREATE POLICY "clients_isolation" ON clients
    USING (id = get_auth_client_id() OR EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'master'));

-- Links: Client sees own
CREATE POLICY "links_isolation" ON links
    USING (client_id = get_auth_client_id() OR EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'master'));

-- Leads: Client sees own
CREATE POLICY "leads_isolation" ON leads
    USING (client_id = get_auth_client_id() OR EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'master'));

-- Client Form Config: Client sees own, Public read (for form rendering - handled via API usually, but if direct DB access needed)
-- Note: API will use service role to fetch config for public forms, so RLS mainly for Admin Panel
CREATE POLICY "config_isolation" ON client_form_config
    USING (client_id = get_auth_client_id() OR EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'master'));

-- Initial Seed Data for Form Fields
INSERT INTO form_fields (field_key, label_default, type, required_default, used_for_score, used_for_external_lookup) VALUES
('full_name', 'Nome Completo', 'text', true, false, false),
('phone', 'WhatsApp', 'phone', true, true, false), -- +10 points for valid phone
('cpf', 'CPF', 'cpf', false, false, true), -- Critical for external lookup
('email', 'E-mail', 'email', false, false, false),
('income_range', 'Faixa de Renda', 'select', true, true, false),
('has_clt', 'Possui CLT?', 'radio', true, true, false),
('clt_years', 'Tempo de CLT', 'select', false, true, false),
('tried_financing', 'Já tentou financiar?', 'radio', true, true, false);

-- Update options for select fields
UPDATE form_fields SET options = '["Menos de R$1.500", "R$1.500 - R$3.000", "R$3.000 - R$5.000", "Acima de R$5.000"]' WHERE field_key = 'income_range';
UPDATE form_fields SET options = '["Sim", "Não"]' WHERE field_key = 'has_clt';
UPDATE form_fields SET options = '["Menos de 1 ano", "1 a 2 anos", "2 a 3 anos", "Mais de 3 anos"]' WHERE field_key = 'clt_years';
UPDATE form_fields SET options = '["Sim", "Não"]' WHERE field_key = 'tried_financing';

-- Seed Score Rules
INSERT INTO score_rules (field_id, condition_operator, condition_value, points)
SELECT id, 'equals', 'Mais de 3 anos', 30 FROM form_fields WHERE field_key = 'clt_years';

INSERT INTO score_rules (field_id, condition_operator, condition_value, points)
SELECT id, 'equals', '2 a 3 anos', 15 FROM form_fields WHERE field_key = 'clt_years';

INSERT INTO score_rules (field_id, condition_operator, condition_value, points)
SELECT id, 'equals', 'Acima de R$5.000', 25 FROM form_fields WHERE field_key = 'income_range';

INSERT INTO score_rules (field_id, condition_operator, condition_value, points)
SELECT id, 'equals', 'Não', 20 FROM form_fields WHERE field_key = 'tried_financing';
