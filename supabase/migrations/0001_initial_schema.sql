create extension if not exists pgcrypto;

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null constraint uq_profiles_display_name unique,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_profiles_display_name_format check (display_name ~ '^[a-z0-9_]{3,20}$')
);

comment on table profiles is 'One row per authenticated user.';

create trigger trg_profiles_set_updated_at
before update on profiles
for each row
execute function set_updated_at();

create table artists (
  id uuid primary key default gen_random_uuid(),
  spotify_id text not null constraint uq_artists_spotify_id unique,
  name text not null,
  image_url text,
  genres text[] not null default '{}',
  opted_out boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table artists is 'The global catalog of tracked Spotify artists.';

create trigger trg_artists_set_updated_at
before update on artists
for each row
execute function set_updated_at();

create index idx_artists_opted_out_is_active
on artists (opted_out, is_active)
where opted_out = false and is_active = true;

create table listener_snapshots (
  id uuid primary key default gen_random_uuid(),
  artist_id uuid not null references artists(id) on delete cascade,
  monthly_listeners integer not null,
  captured_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint ck_listener_snapshots_monthly_listeners_nonnegative check (monthly_listeners >= 0)
);

comment on table listener_snapshots is
  'Append-only log of monthly listener measurements. Latest per artist is a window query.';

create index idx_listener_snapshots_artist_captured
on listener_snapshots (artist_id, captured_at desc);

create table seasons (
  id uuid primary key default gen_random_uuid(),
  season_number integer not null constraint uq_seasons_season_number unique,
  signing_opens_at timestamptz not null,
  signing_closes_at timestamptz not null,
  season_ends_at timestamptz not null,
  status text not null,
  artist_pool uuid[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_seasons_season_number_positive check (season_number > 0),
  constraint ck_seasons_status check (status in ('upcoming', 'signing', 'active', 'ended')),
  constraint ck_seasons_chronology check (
    signing_closes_at > signing_opens_at
    and season_ends_at > signing_closes_at
  )
);

create trigger trg_seasons_set_updated_at
before update on seasons
for each row
execute function set_updated_at();

create index idx_seasons_status
on seasons (status);

create table rosters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  season_id uuid not null references seasons(id) on delete cascade,
  locked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_rosters_user_season unique (user_id, season_id)
);

create trigger trg_rosters_set_updated_at
before update on rosters
for each row
execute function set_updated_at();

create index idx_rosters_season
on rosters (season_id);

create table signings (
  id uuid primary key default gen_random_uuid(),
  roster_id uuid not null references rosters(id) on delete cascade,
  artist_id uuid not null references artists(id) on delete restrict,
  slots integer not null,
  tier_at_signing text not null,
  listeners_at_signing integer not null,
  signed_at timestamptz not null default now(),
  dropped_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_signings_slots check (slots between 1 and 10),
  constraint ck_signings_tier_at_signing check (
    tier_at_signing in ('underground', 'rising', 'emerging', 'established')
  ),
  constraint ck_signings_listeners_at_signing_nonnegative check (listeners_at_signing >= 0),
  constraint ck_signings_dropped_after_signed check (dropped_at is null or dropped_at >= signed_at)
);

create trigger trg_signings_set_updated_at
before update on signings
for each row
execute function set_updated_at();

create unique index idx_signings_roster_artist_active
on signings (roster_id, artist_id)
where dropped_at is null;

create index idx_signings_roster
on signings (roster_id);

create index idx_signings_artist
on signings (artist_id);

create table season_scores (
  id uuid primary key default gen_random_uuid(),
  roster_id uuid not null references rosters(id) on delete cascade,
  score numeric(12, 6) not null,
  rank integer not null,
  computed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_season_scores_roster unique (roster_id),
  constraint ck_season_scores_rank_positive check (rank > 0)
);

create trigger trg_season_scores_set_updated_at
before update on season_scores
for each row
execute function set_updated_at();

create table badges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  artist_id uuid not null references artists(id) on delete restrict,
  season_id uuid not null references seasons(id) on delete cascade,
  badge_type text not null,
  earned_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint ck_badges_badge_type check (badge_type in ('first_believer', 'tier_jump')),
  constraint uq_badges_user_artist_season_type unique (user_id, artist_id, season_id, badge_type)
);

create index idx_badges_user
on badges (user_id);

create table opt_out_requests (
  id uuid primary key default gen_random_uuid(),
  spotify_artist_url text not null,
  contact_email text not null,
  verification_method text not null,
  status text not null default 'pending',
  notes text,
  reviewed_by uuid references profiles(id) on delete restrict,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_opt_out_requests_verification_method check (
    verification_method in ('email', 'domain', 'manual')
  ),
  constraint ck_opt_out_requests_status check (status in ('pending', 'approved', 'rejected'))
);

create trigger trg_opt_out_requests_set_updated_at
before update on opt_out_requests
for each row
execute function set_updated_at();

create index idx_opt_out_requests_status
on opt_out_requests (status);

create table audit_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete set null,
  action text not null,
  payload jsonb not null default '{}'::jsonb,
  ip_address inet,
  user_agent text,
  created_at timestamptz not null default now()
);

create index idx_audit_log_user_created
on audit_log (user_id, created_at desc);

create index idx_audit_log_action
on audit_log (action);

alter table profiles enable row level security;
alter table artists enable row level security;
alter table listener_snapshots enable row level security;
alter table seasons enable row level security;
alter table rosters enable row level security;
alter table signings enable row level security;
alter table season_scores enable row level security;
alter table badges enable row level security;
alter table opt_out_requests enable row level security;
alter table audit_log enable row level security;

create policy profiles_select_authenticated
on profiles
for select
to authenticated
using (true);

create policy profiles_insert_own
on profiles
for insert
to authenticated
with check (id = auth.uid());

create policy profiles_update_own
on profiles
for update
to authenticated
using (id = auth.uid())
with check (id = auth.uid());

create policy artists_select_authenticated
on artists
for select
to authenticated
using (true);

create policy listener_snapshots_select_authenticated
on listener_snapshots
for select
to authenticated
using (true);

create policy seasons_select_authenticated
on seasons
for select
to authenticated
using (true);

create policy season_scores_select_authenticated
on season_scores
for select
to authenticated
using (true);

create policy badges_select_authenticated
on badges
for select
to authenticated
using (true);

create policy rosters_select_authenticated
on rosters
for select
to authenticated
using (true);

create policy rosters_insert_own
on rosters
for insert
to authenticated
with check (user_id = auth.uid());

create policy rosters_update_own
on rosters
for update
to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

create policy signings_select_authenticated
on signings
for select
to authenticated
using (true);

create policy signings_insert_own_roster
on signings
for insert
to authenticated
with check (
  exists (
    select 1
    from rosters
    where rosters.id = roster_id
      and rosters.user_id = auth.uid()
  )
);

create policy signings_update_own_roster
on signings
for update
to authenticated
using (
  exists (
    select 1
    from rosters
    where rosters.id = roster_id
      and rosters.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from rosters
    where rosters.id = roster_id
      and rosters.user_id = auth.uid()
  )
);

create policy opt_out_requests_insert_public
on opt_out_requests
for insert
to anon, authenticated
with check (true);

-- Migration applied: run against Supabase SQL editor or via supabase db push
