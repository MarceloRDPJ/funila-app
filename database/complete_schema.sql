-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. CLIENTS (Tenants)
create table if not exists public.clients (
    id uuid default gen_random_uuid() primary key,
    name text not null,
    email text unique,
    plan text default 'solo', -- 'solo', 'pro', 'agency', 'enterprise'
    active boolean default true,
    whatsapp text,
    zapi_instance text,
    zapi_token text,
    brand_logo_url text,
    brand_primary_color text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. USERS (Linked to Auth)
create table if not exists public.users (
    id uuid primary key, -- references auth.users
    email text,
    role text default 'client', -- 'master', 'client', 'admin'
    client_id uuid references public.clients(id),
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. CAMPAIGNS & CREATIVES (Meta Ads Structure)
create table if not exists public.campaigns (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    external_id text unique, -- Meta Campaign ID
    name text,
    status text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.creatives (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    campaign_id uuid references public.campaigns(id),
    external_id text unique, -- Meta Ad ID
    name text,
    thumbnail_url text,
    status text,
    clicks integer default 0,
    leads integer default 0,
    conversions integer default 0,
    cost_cents integer default 0,
    utm_content text, -- Key for matching
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
create index if not exists idx_creatives_utm on public.creatives(client_id, utm_content);

-- 4. LEADS
create table if not exists public.leads (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    link_id uuid, -- references links(id) defined below
    creative_id uuid references public.creatives(id),
    name text,
    phone text,
    email text,
    cpf_encrypted text,
    status text default 'started', -- 'hot', 'warm', 'cold', 'started', 'abandoned', 'converted', 'trash'
    internal_score integer default 0,
    external_score integer default 0,
    serasa_score integer,
    step_reached integer default 0,
    consent_given boolean default false,
    device_type text,
    utm_source text,
    utm_medium text,
    utm_campaign text,
    utm_content text,
    whatsapp_meta jsonb default '{}'::jsonb,
    public_api_data jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);
create index if not exists idx_leads_client on public.leads(client_id);
create index if not exists idx_leads_status on public.leads(status);

-- 5. EVENTS & LOGS
create table if not exists public.events (
    id uuid default gen_random_uuid() primary key,
    lead_id uuid references public.leads(id),
    event_type text not null, -- 'form_submit', 'step_update', 'lead_started', etc.
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.logs (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id), -- Nullable if system log
    lead_id uuid references public.leads(id),
    level text not null, -- 'info', 'warning', 'error'
    source text not null, -- 'webhook', 'brasil_api', 'system'
    message text not null,
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
create index if not exists idx_logs_client on public.logs(client_id);

-- 6. LINKS & TRACKING
create table if not exists public.links (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    name text not null,
    slug text unique not null,
    destination text not null,
    funnel_type text default 'form', -- 'form', 'landing', 'capture'
    active boolean default true,
    utm_source text,
    utm_campaign text,
    capture_url text,
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.clicks (
    id uuid default gen_random_uuid() primary key,
    link_id uuid references public.links(id),
    client_id uuid references public.clients(id),
    ip_hash text,
    user_agent text,
    device_type text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.visitor_sessions (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id),
    link_id uuid references public.links(id),
    visitor_id text, -- fingerprint
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.funnel_events (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id),
    link_id uuid references public.links(id),
    event_name text, -- 'view', 'click', 'submit'
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 7. FORMS
create table if not exists public.form_fields (
    id uuid default gen_random_uuid() primary key,
    field_key text unique not null, -- 'full_name', 'phone', 'cpf'
    label_default text not null,
    type text not null default 'text'
);

create table if not exists public.client_form_config (
    client_id uuid references public.clients(id) not null,
    field_id uuid references public.form_fields(id) not null,
    label_custom text,
    required boolean default false,
    active boolean default true,
    "order" integer default 0,
    primary key (client_id, field_id)
);

create table if not exists public.lead_responses (
    id uuid default gen_random_uuid() primary key,
    lead_id uuid references public.leads(id) not null,
    field_id uuid references public.form_fields(id) not null,
    response_value text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 8. INTEGRATIONS & BILLING
create table if not exists public.ad_accounts (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    platform text not null, -- 'meta', 'google'
    account_id text,
    access_token text, -- Encrypted
    pixel_id text,
    active boolean default true,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    unique(client_id, platform)
);

create table if not exists public.subscriptions (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    asaas_sub_id text unique,
    status text, -- 'active', 'cancelled'
    mrr_cents integer default 0,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.webhooks (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    url text not null,
    active boolean default true,
    events text[] default '{lead_created}',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table if not exists public.feature_flags (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id),
    flag_name text not null,
    enabled boolean default false,
    unique(client_id, flag_name)
);

-- 9. RPC Functions
create or replace function public.increment_creative_metric(
    p_client_id uuid,
    p_utm_content text,
    p_step integer,
    p_is_click boolean default false,
    p_is_conversion boolean default false
)
returns void as $$
begin
    -- Tenta atualizar o criativo existente
    update public.creatives
    set
        clicks = clicks + (case when p_is_click then 1 else 0 end),
        leads = leads + (case when p_step = 1 then 1 else 0 end),
        conversions = conversions + (case when p_is_conversion then 1 else 0 end)
    where client_id = p_client_id and utm_content = p_utm_content;

    -- Se não existir (row count 0), não faz nada (o sync deve criar)
    -- Ou poderíamos criar um placeholder se quiséssemos
end;
$$ language plpgsql security definer;

-- 10. Default Data (Form Fields)
insert into public.form_fields (field_key, label_default, type) values
('full_name', 'Nome Completo', 'text'),
('phone', 'WhatsApp', 'tel'),
('cpf', 'CPF', 'text'),
('email', 'E-mail', 'email'),
('has_clt', 'Possui Carteira Assinada?', 'select'),
('clt_years', 'Tempo de Registro', 'number'),
('income_range', 'Renda Mensal', 'select'),
('tried_financing', 'Já tentou financiar?', 'select')
on conflict (field_key) do nothing;

-- 11. RLS (Row Level Security) - Basic Setup
-- Allows backend (service role) to do everything.
-- Restricts public access.
alter table public.clients enable row level security;
alter table public.leads enable row level security;
alter table public.users enable row level security;

-- Policy: Service Role bypasses RLS automatically in Supabase.
-- Policy: Anon users can INSERT leads (for public forms) but not SELECT.
create policy "Public can insert leads" on public.leads for insert with check (true);
create policy "Public can insert clicks" on public.clicks for insert with check (true);
create policy "Public can insert events" on public.events for insert with check (true);

-- Policy: Clients can view own data (requires auth.uid() matching users table)
-- (Complex to implement perfectly in SQL only without app context, relying on Backend Logic primarily)
-- Backend uses Service Role for Admin Panel, so RLS is a safety net.
