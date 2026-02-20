ALTER TABLE public.links ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
