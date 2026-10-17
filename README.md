# Koersradar

Gedeeld analyse- en testplatform voor crypto en AEX-aandelen, voor een kleine vriendengroep.

> **Beslisondersteuning, geen beleggingsadvies.** Signalen zijn geen zekerheden en beloven geen
> winst. *Geen trade* is een volwaardige uitkomst: bij een zwak signaal, ontbrekende of verouderde
> data, of te veel risico. Dit prototype plaatst **geen echte orders**.

Het volledige ontwerp, met bronnen, kosten en het bouwplan, staat in [`docs/plan.md`](docs/plan.md).
De gebruiksvoorwaarden van de databronnen staan in [`docs/data-voorwaarden.md`](docs/data-voorwaarden.md).

## Architectuur

```
[Browser] ── Next.js (web/, Vercel) ── Supabase (Postgres + Auth + RLS)
                                             ▲
                         Python worker (worker/, Docker op kleine VPS)
                         ├─ ingest   elke 15 min, alleen gesloten candles, kwaliteitscheck
                         ├─ engine   indicatoren → signalen, versheidspoort   (fase 3)
                         ├─ backtest walk-forward na kosten                    (fase 3)
                         ├─ paper    ledger + risicolimieten                   (fase 4)
                         └─ explain  LLM-uitleg van berekende uitkomsten       (fase 5)
```

- **Berekeningen** gebeuren in controleerbare Python-code met tests. Een taalmodel legt alleen uit.
- **GitHub** bevat de code en is de plek waar we samenwerken. **Vercel** host de website,
  **Supabase** de database en accounts, en de **VPS** draait de worker.
- **Secrets** staan alleen in `.env` (lokaal of op de VPS) en in de Vercel-instellingen, nooit in git.

## Status

| Fase | Wat | Status |
|---|---|---|
| 0 | Repo, CI, schema met RLS, Next.js met invite-login | ✅ klaar (Supabase-project nog aanmaken) |
| 1 | Data-ingest crypto (Binance + Coinbase-fallback), AEX (yfinance), kwaliteitscheck, gap-herstel | ✅ kern klaar en getest tegen live data |
| 2 | Portaal: scanner, markten, grafiek met signaalniveaus, signalenlog | ✅ (watchlist-UI nog niet) |
| 3 | Signal engine (trend-pullback, long) + scanner + "Scan nu" | ✅ engine; ⏳ backtest |
| 5 | AI-uitleg (Claude Haiku) met getallencontrole | ✅ gebouwd, vult `ANTHROPIC_API_KEY` in om aan te zetten |
| 4, 6 | Paper trading, evaluatie | ⏳ |

### Hoe de scanner werkt
1. Elke 15 minuten (en bij **Scan nu** in het portaal) haalt de worker verse candles op.
2. Per instrument en interval controleert hij of de data vers en compleet is. Zo niet, dan volgt `NO_TRADE`.
3. De strategie `trend-pullback-0.1` (`worker/koersradar/strategies/trend_pullback.py`) kijkt naar
   trend (EMA 50/200), pullback en keerpunt (RSI 14), volume, en stop/doel (ATR 14, 2R).
   Daarna rekent hij de R/R **na kosten** uit.
4. Is er een kans, dan schrijft Claude een korte uitleg. Een uitleg met een getal dat niet uit de
   berekening komt, wordt afgewezen (`worker/koersradar/explain/number_check.py`).
5. Alles wordt gelogd in `signals`, ook *geen trade*, zodat we achteraf kunnen evalueren.

⚠️ De strategie is **nog niet gebacktest**. Behandel signalen als ongetest tot fase 3 af is.

## Lokaal starten

Vereisten: Git, Docker (bv. OrbStack of Docker Desktop), Node 22+, Python 3.12+,
de [Supabase CLI](https://supabase.com/docs/guides/local-development) en bij voorkeur
[uv](https://docs.astral.sh/uv/).

```bash
# 1. Secrets
cp .env.example .env              # vul in na stap 2
cp web/.env.example web/.env.local

# 2. Database + Auth lokaal (geeft URL en keys terug)
supabase init                     # alleen de allereerste keer; commit supabase/config.toml
supabase start
supabase db reset                 # past supabase/migrations/ toe (of plak ze op volgorde in de SQL Editor)

# 3. Worker
cd worker
uv venv && uv pip install -e ".[dev,aex]"     # of: python -m venv .venv && .venv/bin/pip install -e ".[dev,aex]"
uv run pytest
uv run python -m koersradar.ingest.backfill --days 30   # alleen Parquet, geen DB nodig
uv run python -m koersradar.ingest.run --days 45        # eerste keer: 45 dagen historie (nodig voor EMA 200 op 1h)
uv run python -m koersradar.scanner.run                 # één scan
uv run python -m koersradar.ingest.scheduler            # elke 15 min ingest+scan, plus 'Scan nu'-aanvragen

# 4. Web
cd ../web
npm install
npm run dev                       # http://localhost:3000
```

Of start de worker in Docker: `docker compose up --build`.

**Inloggen:** er is geen open registratie. Nodig vrienden uit via Supabase Studio
(Authentication → Users → *Invite user*). Lokaal komen de mails binnen in Inbucket/Mailpit;
de URL staat in de output van `supabase start`.

## Configuratie

- `config/instruments.yaml`: welke coins en aandelen we volgen, met bron, fallback en intervallen.
  Uitbreiden doe je door een regel toe te voegen en daarna een backfill te draaien.
- `config/costs.yaml`: fee, spread en slippage per bron. **Vul de actuele tarieven in en zet
  de controledatum erbij.** Zonder realistische kosten zeggen de backtests niets.

## Meedoen

Zie [CONTRIBUTING.md](CONTRIBUTING.md).

## Licenties van gebruikte onderdelen

- Charts: [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) (Apache-2.0, het TradingView-logo in de grafiek is verplicht).
- Exchange-data: [CCXT](https://github.com/ccxt/ccxt) (MIT).
- AEX: [yfinance](https://github.com/ranaroussi/yfinance) (Apache-2.0, onofficieel).
