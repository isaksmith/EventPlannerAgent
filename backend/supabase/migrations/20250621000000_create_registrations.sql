-- Event registration submissions from generated Marquee sites
create table if not exists public.registrations (
  id uuid primary key default gen_random_uuid(),
  site_slug text not null,
  event_name text,
  name text,
  email text,
  form_data jsonb not null default '{}'::jsonb,
  registered_at timestamptz not null default now()
);

create index if not exists registrations_site_slug_idx
  on public.registrations (site_slug);

create index if not exists registrations_registered_at_idx
  on public.registrations (registered_at desc);

alter table public.registrations enable row level security;

-- Inserts happen server-side with the service role key (bypasses RLS).
-- No public policies — anon/authenticated clients cannot read or write directly.
