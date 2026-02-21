-- Sprint 1 Fixes

-- 1. Update Leads Status Constraint
ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_status_check;
ALTER TABLE leads ADD CONSTRAINT leads_status_check
  CHECK (status IN ('hot','warm','cold','abandoned','negotiation','converted','trash','started'));

-- 2. Add missing columns for Kanban Card Polish
ALTER TABLE leads ADD COLUMN IF NOT EXISTS device_type TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS step_reached INTEGER DEFAULT 1;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_content TEXT;
