-- Koersradar: basisschema (fase 0)
-- Marktdata en signalen schrijft alleen de worker (service role, omzeilt RLS).
-- Ingelogde vrienden mogen marktdata lezen; watchlists zijn per gebruiker.

-- ---------- Profielen ----------
create table public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  created_at   timestamptz not null default now()
);

create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, split_part(new.email, '@', 1));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- Instrumenten & koersdata ----------
create table public.instruments (
  id            bigint generated always as identity primary key,
  symbol        text not null unique,          -- bv. BTC/USDT, ASML.AS
  market        text not null check (market in ('crypto', 'aex')),
  source        text not null,                 -- binance, coinbase, yfinance
  experimental  boolean not null default false,
  active        boolean not null default true,
  created_at    timestamptz not null default now()
);

-- Alleen recente vensters (± 90 dagen 15m, 2 jaar 1h). Lange historie = Parquet in de worker.
create table public.candles (
  instrument_id bigint not null references public.instruments (id) on delete cascade,
  interval      text   not null check (interval in ('15m', '1h')),
  open_time     timestamptz not null,          -- altijd UTC
  open          double precision not null,
  high          double precision not null,
  low           double precision not null,
  close         double precision not null,
  volume        double precision not null,
  source        text not null,
  ingested_at   timestamptz not null default now(),
  primary key (instrument_id, interval, open_time)
);
create index candles_open_time_brin on public.candles using brin (open_time);

-- Versheid per instrument+interval: de UI toont dit altijd naast de grafiek.
create table public.data_status (
  instrument_id   bigint not null references public.instruments (id) on delete cascade,
  interval        text   not null,
  source          text   not null,
  last_candle_at  timestamptz,                 -- open_time van laatste GESLOTEN candle
  last_checked_at timestamptz not null default now(),
  status          text not null check (status in ('ok', 'delayed', 'stale', 'gap', 'error')),
  detail          text,
  primary key (instrument_id, interval)
);

-- ---------- Signalen ----------
create table public.signals (
  id               bigint generated always as identity primary key,
  instrument_id    bigint not null references public.instruments (id),
  interval         text   not null,
  decision         text   not null check (decision in ('TRADE', 'NO_TRADE')),
  direction        text   check (direction in ('long', 'short')),
  entry            double precision,
  invalidation     text,                       -- koers of conditie waarbij signaal vervalt
  stop_loss        double precision,
  target           double precision,
  rr_ratio         double precision,           -- na geschatte kosten
  strength         text   check (strength in ('zwak', 'matig', 'sterk')),
  facts            jsonb  not null default '[]',   -- gemeten waarden
  assumptions      jsonb  not null default '[]',   -- aannames
  no_trade_reason  text,
  data_source      text   not null,
  last_candle_at   timestamptz not null,
  data_delay_s     integer not null,
  cost_assumptions jsonb  not null,
  liquidity_ok     boolean not null,
  strategy_version text   not null,
  created_at       timestamptz not null default now(),
  check (decision = 'NO_TRADE' or (direction is not null and entry is not null
                                   and stop_loss is not null and target is not null)),
  check (decision = 'TRADE' or no_trade_reason is not null)
);
create index signals_instrument_created on public.signals (instrument_id, created_at desc);

-- ---------- Paper trading ----------
create table public.paper_trades (
  id           bigint generated always as identity primary key,
  signal_id    bigint not null references public.signals (id),
  opened_at    timestamptz not null,
  entry_price  double precision not null,
  size         double precision not null,
  risk_amount  double precision not null,
  closed_at    timestamptz,
  exit_price   double precision,
  exit_reason  text check (exit_reason in ('stop', 'target', 'invalidated', 'manual', 'timeout')),
  pnl_after_costs double precision,
  r_multiple   double precision
);

-- ---------- Backtests ----------
create table public.backtest_runs (
  id               bigint generated always as identity primary key,
  strategy_version text not null,
  instrument_id    bigint references public.instruments (id),
  interval         text not null,
  params           jsonb not null,
  period_kind      text not null check (period_kind in ('train', 'test', 'walk_forward', 'holdout')),
  period_start     timestamptz not null,
  period_end       timestamptz not null,
  metrics          jsonb not null,             -- rendement na kosten, max DD, #trades, ...
  benchmarks       jsonb not null,             -- buy&hold, random entry
  created_at       timestamptz not null default now()
);

-- ---------- Watchlists ----------
create table public.watchlists (
  id         bigint generated always as identity primary key,
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name       text not null,
  created_at timestamptz not null default now()
);

create table public.watchlist_items (
  watchlist_id  bigint not null references public.watchlists (id) on delete cascade,
  instrument_id bigint not null references public.instruments (id) on delete cascade,
  added_at      timestamptz not null default now(),
  primary key (watchlist_id, instrument_id)
);

-- ---------- Row Level Security ----------
alter table public.profiles        enable row level security;
alter table public.instruments     enable row level security;
alter table public.candles         enable row level security;
alter table public.data_status     enable row level security;
alter table public.signals         enable row level security;
alter table public.paper_trades    enable row level security;
alter table public.backtest_runs   enable row level security;
alter table public.watchlists      enable row level security;
alter table public.watchlist_items enable row level security;

-- ---------- Expliciete rechten ----------
-- Niet vertrouwen op "automatically expose new tables": anon krijgt niets,
-- authenticated alleen wat nodig is. RLS-policies hieronder beperken het verder.
revoke all on all tables in schema public from anon, authenticated;
grant select on public.profiles, public.instruments, public.candles, public.data_status,
  public.signals, public.paper_trades, public.backtest_runs to authenticated;
grant update (display_name) on public.profiles to authenticated;
grant select, insert, update, delete on public.watchlists, public.watchlist_items to authenticated;
grant usage on sequence public.watchlists_id_seq to authenticated;

-- Gedeelde (read-only) data voor ingelogde groepsleden
create policy "read profiles"      on public.profiles      for select to authenticated using (true);
create policy "read instruments"   on public.instruments   for select to authenticated using (true);
create policy "read candles"       on public.candles       for select to authenticated using (true);
create policy "read data_status"   on public.data_status   for select to authenticated using (true);
create policy "read signals"       on public.signals       for select to authenticated using (true);
create policy "read paper_trades"  on public.paper_trades  for select to authenticated using (true);
create policy "read backtest_runs" on public.backtest_runs for select to authenticated using (true);

create policy "update own profile" on public.profiles for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));

-- Watchlists: alleen eigenaar
create policy "own watchlists" on public.watchlists for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

create policy "own watchlist items" on public.watchlist_items for all to authenticated
  using (exists (select 1 from public.watchlists w
                 where w.id = watchlist_id and w.user_id = (select auth.uid())))
  with check (exists (select 1 from public.watchlists w
                      where w.id = watchlist_id and w.user_id = (select auth.uid())));
