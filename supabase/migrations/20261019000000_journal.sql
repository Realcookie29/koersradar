-- Koersradar: handelsjournaal voor paper trading (zonder echt geld).
-- Elk lid legt eigen trades vast; de groep ziet elkaars trades, zodat je van elkaar leert.
-- Alleen de eigenaar mag een trade wijzigen of verwijderen.

create table public.journal_trades (
  id            bigint generated always as identity primary key,
  user_id       uuid not null default auth.uid() references auth.users (id) on delete cascade,
  instrument_id bigint not null references public.instruments (id),
  signal_id     bigint references public.signals (id) on delete set null, -- optioneel: trade naar aanleiding van een signaal
  direction     text not null default 'long' check (direction in ('long', 'short')),
  opened_at     timestamptz not null default now(),
  entry_price   double precision not null check (entry_price > 0),
  stop_loss     double precision not null check (stop_loss > 0),
  target        double precision check (target > 0),
  quantity      double precision not null check (quantity > 0),
  -- Kosten per kant als fractie (fee + halve spread + slippage), vastgelegd bij openen,
  -- zodat een latere wijziging van config/costs.yaml oude trades niet verandert.
  cost_pct      double precision not null default 0.0016 check (cost_pct >= 0 and cost_pct < 0.05),
  reason        text check (char_length(reason) <= 1000),
  closed_at     timestamptz,
  exit_price    double precision check (exit_price > 0),
  exit_note     text check (char_length(exit_note) <= 1000),
  created_at    timestamptz not null default now(),
  check ((direction = 'long' and stop_loss < entry_price) or (direction = 'short' and stop_loss > entry_price)),
  check (target is null or (direction = 'long' and target > entry_price) or (direction = 'short' and target < entry_price)),
  check ((closed_at is null) = (exit_price is null)),
  check (closed_at is null or closed_at >= opened_at)
);
create index journal_trades_user_opened on public.journal_trades (user_id, opened_at desc);
create index journal_trades_opened on public.journal_trades (opened_at desc);

alter table public.journal_trades enable row level security;

grant select, insert, update, delete on public.journal_trades to authenticated;
grant usage on sequence public.journal_trades_id_seq to authenticated;

create policy "read journal" on public.journal_trades for select to authenticated using (true);
create policy "add own trade" on public.journal_trades for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy "edit own trade" on public.journal_trades for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "delete own trade" on public.journal_trades for delete to authenticated
  using (user_id = (select auth.uid()));
