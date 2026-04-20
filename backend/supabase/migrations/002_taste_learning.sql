-- Phase 4.3: Taste learning — log accept/reject per suggestion

create table if not exists public.taste_signals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  moment_id uuid references public.moments(id) on delete set null,
  track_id text not null,
  track_name text not null,
  track_artist text not null,
  action text not null check (action in ('accept', 'reject', 'try_different')),
  scene_json jsonb,
  created_at timestamptz default now()
);

alter table public.taste_signals enable row level security;

create policy "Users can insert own taste signals"
  on public.taste_signals for insert
  with check (auth.uid() = user_id);

create policy "Users can read own taste signals"
  on public.taste_signals for select
  using (auth.uid() = user_id);

create index idx_taste_signals_user on public.taste_signals(user_id, created_at desc);
