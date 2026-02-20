-- Sprint 2: Meta Ads Schema

CREATE TABLE IF NOT EXISTS ad_accounts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
  platform        TEXT CHECK (platform IN ('meta', 'google')),
  account_id      TEXT NOT NULL,
  account_name    TEXT,
  access_token    TEXT NOT NULL,
  refresh_token   TEXT,
  token_expires_at TIMESTAMP WITH TIME ZONE,
  status          TEXT DEFAULT 'active',
  last_sync_at    TIMESTAMP WITH TIME ZONE,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ad_accounts_client ON ad_accounts(client_id);

CREATE TABLE IF NOT EXISTS campaigns (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ad_account_id   UUID REFERENCES ad_accounts(id) ON DELETE CASCADE,
  client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
  external_id     TEXT NOT NULL,
  name            TEXT,
  status          TEXT,
  objective       TEXT,
  daily_budget_cents INTEGER DEFAULT 0,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS creatives (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id          UUID REFERENCES campaigns(id),
  client_id            UUID REFERENCES clients(id) ON DELETE CASCADE,
  external_id          TEXT NOT NULL,
  name                 TEXT,
  creative_type        TEXT, -- image, video, carousel
  thumbnail_url        TEXT,
  headline             TEXT,
  body                 TEXT,
  spend_cents          INTEGER DEFAULT 0,
  impressions          INTEGER DEFAULT 0,
  clicks               INTEGER DEFAULT 0,
  leads_generated      INTEGER DEFAULT 0,
  cpl_cents            INTEGER DEFAULT 0,
  ctr                  DECIMAL(5,2) DEFAULT 0,
  last_metrics_sync    TIMESTAMP WITH TIME ZONE,
  created_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_creatives_client ON creatives(client_id);

ALTER TABLE leads ADD COLUMN IF NOT EXISTS creative_id UUID REFERENCES creatives(id);
