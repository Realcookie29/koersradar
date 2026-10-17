-- Koersradar: daytrade-scanner (scan-runs, AI-uitleg bij signalen)

-- Eén signaal per instrument/interval/strategie/candle: herhaald scannen maakt geen duplicaten.
create unique index signals_unique_per_candle
  on public.signals (instrument_id, interval, strategy_version, last_candle_at);

-- Uitleg door een taalmodel. Alleen gevuld als de getallencontrole slaagt.
alter table public.signals
  add column scan_run_id         bigint,
  add column explanation         text,
  add column explanation_model   text,
  add column explanation_status  text check (explanation_status in ('ok', 'rejected', 'skipped', 'error'));

-- Scan-runs: automatisch (na elke ingest) of op verzoek vanuit het portaal.
create table public.scan_runs (
  id            bigint generated always as identity primary key,
  trigger       text not null check (trigger in ('schedule', 'manual')),
  requested_by  uuid default auth.uid() references auth.users (id) on delete set null,
  requested_at  timestamptz not null default now(),
  started_at    timestamptz,
  finished_at   timestamptz,
  status        text not null default 'pending'
                check (status in ('pending', 'running', 'done', 'error')),
  instruments_scanned integer,
  trade_count   integer,
  error         text
);
create index scan_runs_requested_at on public.scan_runs (requested_at desc);

alter table public.signals
  add constraint signals_scan_run_fk foreign key (scan_run_id) references public.scan_runs (id);

alter table public.scan_runs enable row level security;

grant select on public.scan_runs to authenticated;
grant insert (trigger) on public.scan_runs to authenticated;
grant usage on sequence public.scan_runs_id_seq to authenticated;

create policy "read scan_runs" on public.scan_runs for select to authenticated using (true);
-- Ingelogde leden mogen alleen een handmatige scan aanvragen, op eigen naam.
create policy "request manual scan" on public.scan_runs for insert to authenticated
  with check (trigger = 'manual' and requested_by = (select auth.uid()) and status = 'pending');

-- Laatste beoordeling per instrument + interval (voor het scanner-dashboard).
-- security_invoker: de view respecteert de RLS/grants van de ingelogde gebruiker.
create view public.latest_signals with (security_invoker = true) as
select distinct on (s.instrument_id, s.interval)
  s.*, i.symbol, i.market, i.experimental
from public.signals s
join public.instruments i on i.id = s.instrument_id
order by s.instrument_id, s.interval, s.last_candle_at desc, s.id desc;

grant select on public.latest_signals to authenticated;
