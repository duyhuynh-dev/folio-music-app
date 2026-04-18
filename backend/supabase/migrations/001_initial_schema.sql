-- Folio Phase 2.2: initial schema
-- Run this in Supabase SQL Editor or via supabase db push

-- Users (extends Supabase Auth)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz default now()
);

alter table public.profiles enable row level security;

create policy "Users can read own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- Trips
create table if not exists public.trips (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null default 'Untitled Trip',
  start_date date,
  end_date date,
  members text[] default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.trips enable row level security;

create policy "Users can CRUD own trips"
  on public.trips for all
  using (auth.uid() = user_id);

-- Moments (a photo + its matched song within a trip)
create table if not exists public.moments (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  photo_url text not null,
  scene_json jsonb,
  chosen_track_id text,
  chosen_track_name text,
  chosen_track_artist text,
  chosen_track_reason text,
  chosen_track_apple_url text,
  chosen_track_preview_url text,
  latitude double precision,
  longitude double precision,
  taken_at timestamptz,
  created_at timestamptz default now()
);

alter table public.moments enable row level security;

create policy "Users can CRUD own moments"
  on public.moments for all
  using (auth.uid() = user_id);

-- Suggestions cache (avoid re-running pipeline for same photo)
create table if not exists public.suggestions (
  id uuid primary key default gen_random_uuid(),
  moment_id uuid not null references public.moments(id) on delete cascade,
  track_id text not null,
  track_name text not null,
  track_artist text not null,
  track_reason text,
  track_apple_url text,
  track_preview_url text,
  variation_seed int default 0,
  created_at timestamptz default now()
);

alter table public.suggestions enable row level security;

create policy "Users can read own suggestions"
  on public.suggestions for select
  using (
    exists (
      select 1 from public.moments m
      where m.id = moment_id and m.user_id = auth.uid()
    )
  );

-- Storage bucket for photo uploads
insert into storage.buckets (id, name, public)
values ('photos', 'photos', false)
on conflict (id) do nothing;

create policy "Users can upload own photos"
  on storage.objects for insert
  with check (
    bucket_id = 'photos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "Users can read own photos"
  on storage.objects for select
  using (
    bucket_id = 'photos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );
