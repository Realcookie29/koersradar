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
                         Python worker (worker/, Docker op NAS of kleine VPS)
                         ├─ ingest   elke 15 min, alleen gesloten candles, kwaliteitscheck
                         ├─ engine   indicatoren → signalen, versheidspoort
                         ├─ backtest walk-forward na kosten, onderzoek naar varianten
                         ├─ paper    automatisch paper trading + risicolimieten
                         └─ explain  LLM-uitleg van berekende uitkomsten
```

- **Berekeningen** gebeuren in controleerbare Python-code met tests. Een taalmodel legt alleen uit.
- **GitHub** bevat de code en is de plek waar we samenwerken. **Vercel** host de website,
  **Supabase** de database en accounts, en een **NAS of VPS** draait de worker.
- **Secrets** staan alleen in `.env` (lokaal of op de VPS) en in de Vercel-instellingen, nooit in git.

## Status

| Fase | Wat | Status |
|---|---|---|
| 0 | Repo, CI, schema met RLS, Next.js met invite-login | ✅ klaar |
| 1 | Data-ingest crypto (Binance + Coinbase-fallback), AEX (yfinance), kwaliteitscheck, gap-herstel | ✅ kern klaar en getest tegen live data |
| 2 | Portaal: scanner, markten met marktoverzicht, grafiek met signaalniveaus, signalenlog | ✅ (watchlist-UI nog niet) |
| 3 | Signal engine (trend-pullback, long) + scanner + "Scan nu" + backtest | ✅ backtest klaar: **de strategie verliest na kosten** |
| 4 | Paper trading: automatisch voor scannersignalen, en een journaal met risicocalculator | ✅ gebouwd; draait zodra de worker 24/7 aanstaat |
| 5 | AI-uitleg (Claude Haiku) met getallencontrole | ✅ gebouwd, vult `ANTHROPIC_API_KEY` in om aan te zetten |
| 6 | Evaluatie na minstens 4 weken paper trading | ⏳ |

### Hoe de scanner werkt
1. Elke 15 minuten (en bij **Scan nu** in het portaal) haalt de worker verse candles op.
2. Per instrument en interval controleert hij of de data vers en compleet is. Zo niet, dan volgt `NO_TRADE`.
3. De strategie `trend-pullback-0.1` (`worker/koersradar/strategies/trend_pullback.py`) kijkt naar
   trend (EMA 50/200), pullback en keerpunt (RSI 14), volume, en stop/doel (ATR 14, 2R).
   Daarna rekent hij de R/R **na kosten** uit.
4. Is er een kans, dan schrijft Claude een korte uitleg. Een uitleg met een getal dat niet uit de
   berekening komt, wordt afgewezen (`worker/koersradar/explain/number_check.py`).
5. Alles wordt gelogd in `signals`, ook *geen trade*, zodat we achteraf kunnen evalueren.
6. Elk koopsignaal wordt automatisch met nepgeld uitgevoerd (`worker/koersradar/paper/ledger.py`),
   met dezelfde regels als de backtest: 1% risico per trade, maximaal 5 posities, geen nieuwe trades
   na 3% dagverlies. Elk signaal krijgt één besluit (geopend of overgeslagen, met reden).

⚠️ **De strategie verliest in de backtest geld na kosten** (ongeveer −0,16R per trade op 1h, −0,19R
op 15m in 2021 t/m 2024). Volg de signalen niet met echt geld.

### Wat de backtests lieten zien
Alle onderzoeken zijn vooraf vastgelegd (spelregel in git vóór de uitkomsten), getest na kosten en
vergeleken met willekeurige instap. Geen enkel idee doorstond de controle op ongeziene data.

| Onderzoek | Uitkomst | Document |
|---|---|---|
| Trend-pullback (de scanner) | verliest na kosten; zonder kosten ongeveer 0R | `/backtest` in het portaal |
| Zes varianten (ruimere stop, kostenfilter, dagtrend, BTC-trend) | verlies kleiner, geen voorsprong | [`docs/backtest-varianten.md`](docs/backtest-varianten.md) |
| Breakout, momentum, terugval op 15m/1h | breakout heeft vóór kosten een voorsprong, maar kosten zijn groter | [`docs/nieuwe-instap.md`](docs/nieuwe-instap.md) |
| Turtle-breakout op 4 uur en dag (swing) | goed in 2021 t/m 2025, niet in 2026 | [`docs/swing-breakout.md`](docs/swing-breakout.md) |

Alle historische data tot en met 18 oktober 2026 is daarmee bekeken. Nieuwe ideeën kunnen alleen nog
eerlijk worden getoetst door ze vanaf nu vooruit te volgen (paper trading).

```bash
python -m koersradar.backtest.run --interval 1h                      # de scannerstrategie
python -m koersradar.backtest.research --interval 1h                 # varianten
python -m koersradar.backtest.ideas_research --interval 1h           # nieuwe instapideeën
python -m koersradar.backtest.ideas_research --interval 4h           # swing (4h en 1d)
```
Draai deze vanuit de hoofdmap van de repo, met de Python-omgeving van `worker/`.

### De worker 24/7
De worker moet altijd aan staan voor verse koersen, signalen en paper trading. Zie
[`docs/worker-draaien.md`](docs/worker-draaien.md) voor Synology NAS, VPS of je eigen pc.

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
uv run python -m koersradar.ingest.history_db --days 400 # eenmalig: 400 dagen 1h voor de 4h- en daggrafieken
uv run python -m koersradar.scanner.run                 # één scan
uv run python -m koersradar.ingest.scheduler            # elke 15 min ingest+scan, plus 'Scan nu'-aanvragen

# 4. Web
cd ../web
npm install
npm run dev                       # http://localhost:3000
```

Of start de worker in Docker: `docker compose up --build` (tegen de lokale Supabase CLI), of
`docker compose -f compose.server.yml up -d --build` tegen de online Supabase (zie [`docs/worker-draaien.md`](docs/worker-draaien.md)).

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
