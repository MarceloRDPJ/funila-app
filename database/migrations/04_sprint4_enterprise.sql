-- Sprint 4: Enterprise Schema

CREATE TABLE IF NOT EXISTS subscriptions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
  asaas_customer_id TEXT,
  asaas_sub_id    TEXT,
  plan            TEXT CHECK (plan IN ('solo', 'pro', 'agency', 'enterprise')),
  status          TEXT DEFAULT 'active',
  mrr_cents       INTEGER DEFAULT 0,
  next_billing_at TIMESTAMP WITH TIME ZONE,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feature_flags (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   UUID REFERENCES clients(id) ON DELETE CASCADE,
  flag_name   TEXT NOT NULL,
  enabled     BOOLEAN DEFAULT false,
  updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(client_id, flag_name)
);

ALTER TABLE clients ADD COLUMN IF NOT EXISTS brand_logo_url TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS brand_primary_color TEXT DEFAULT '#2563EB';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS brand_name TEXT;
