-- Koersradar: automatisch paper trading van de scannersignalen (worker/koersradar/paper/ledger.py).
-- paper_trades bestond al; entry_price en exit_price zijn koersen zonder kosten,
-- pnl_after_costs en r_multiple zijn na kosten.

-- Hoogstens één paper trade per signaal.
create unique index paper_trades_signal on public.paper_trades (signal_id);

-- Eén besluit per koopsignaal: geopend, of overgeslagen met de reden.
create table public.paper_decisions (
  signal_id  bigint primary key references public.signals (id) on delete cascade,
  decided_at timestamptz not null default now(),
  outcome    text not null check (outcome in ('opened', 'skipped')),
  reason     text
);

alter table public.paper_decisions enable row level security;
grant select on public.paper_decisions to authenticated;
create policy "read paper_decisions" on public.paper_decisions for select to authenticated using (true);
