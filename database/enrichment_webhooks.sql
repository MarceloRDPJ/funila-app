-- Migration: Enrichment & Webhooks
-- Run this in Supabase SQL Editor

-- 1. Add new columns to leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS public_api_data JSONB;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS whatsapp_meta JSONB;

-- 2. Update status check constraint to include new Kanban statuses
ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_status_check;
ALTER TABLE leads ADD CONSTRAINT leads_status_check
    CHECK (status IN ('hot', 'warm', 'cold', 'converted', 'negotiation', 'trash'));

-- 3. Create webhooks table
CREATE TABLE IF NOT EXISTS webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_webhooks_client ON webhooks(client_id);

-- Enable RLS
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;

-- Policy: Clients can only see their own webhooks
CREATE POLICY "client_webhooks" ON webhooks FOR ALL
    USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));
