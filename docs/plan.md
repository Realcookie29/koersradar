# Plan: Koersradar — gedeeld analyse- en testplatform voor crypto + AEX

## Context
Een vriendengroep wil een online dashboard om crypto en aandelen te analyseren voor daytrading: koersgrafieken, controleerbare signalen met uitleg door een taalmodel, en eerst veilig testen (backtest + paper trading) voordat er echt geld in gaat. Het doel is beslisondersteuning, geen winstbelofte. "Geen trade" is een geldige uitkomst.

Gekozen uitgangspunten:
- **Stack:** Python voor data en analyse, TypeScript/Next.js voor het dashboard.
- **Markten:** crypto (top ~20) en AEX-aandelen.
- **Budget:** €0–10 per maand.
- **Signalen:** op 15m- en 1h-candles; een paar minuten vertraging is acceptabel.

In de vault bestaat nog geen trading-project, dus dit wordt een nieuwe repo. Werknaam: `Koersradar`. Lokale clone in de vault-root, naast de andere projecten.

Alle bronnen, prijzen en licenties hieronder zijn gecontroleerd op 2026-10-17. Wat niet bevestigd kon worden, is gemarkeerd als *[onbevestigd]*.

---

## 1. Haalbaarheid: verwachtingen bijstellen
- **Crypto is goed haalbaar.** Gratis en diepe historie (15m/1h, jaren terug) via exchange-API's.
- **AEX-intraday is het knelpunt.** Er is geen gratis bron die juridisch schoon is.
  - yfinance werkt (`ASML.AS`), maar is onofficieel, alleen voor persoonlijk gebruik en kan zonder aankondiging breken.
  - Yahoo bewaart 15m-data maar 60 dagen en 1h-data 730 dagen.
  - De goedkoopste officiële optie is EODHD (€29,99 per maand): 5m/1h, bars pas na sluitingstijd definitief.
  - **Gevolg:** AEX in het MVP alleen op 1h-candles en als "experimenteel" gemarkeerd. Echte AEX-daytrading op 15m past niet in het budget.
- **Data delen telt als herdistributie.** Bijna alle persoonlijke datalicenties staan alleen gebruik door de abonnee toe; data tonen aan vier vrienden valt daar formeel buiten. Daarom: houd de groep klein en besloten, toon bij AEX vooral afgeleide signalen en indicatoren, en lees per bron de voorwaarden.
- **Daytrading-edge is zeldzaam.** Na kosten (fees, spread, slippage) verliezen de meeste eenvoudige indicatorstrategieën het van buy-and-hold. Verwacht dat de backtests dat laten zien. Dat het platform dit eerlijk laat zien, is precies de waarde ervan.
- **Kanspercentages** pas tonen als ze gekalibreerd zijn op out-of-sample data. Tot die tijd geldt "sterk, matig of zwak" op basis van regels, niet "72% kans".
- **Een LLM voorspelt niets.** Het vat alleen berekende uitkomsten samen en rekent zelf niet.

## 2. Bestaande voorbeelden: wat hergebruiken en wat zelf bouwen

| Onderdeel | Keuze / voorbeeld | Licentie, prijs en beperkingen | Gebruik |
|---|---|---|---|
| Crypto-data | [Binance market data](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints) via host `data-api.binance.vision`, bulk via [data.binance.vision](https://data.binance.vision/) | Gratis, 1000 candles per request. Binance is sinds 2023 weg uit NL voor accounts; of publieke data vanaf een NL-IP werkt is *[onbevestigd]*, dus eerst testen. | Primaire bron |
| Crypto-fallback | [Coinbase Exchange candles](https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles) | Gratis, 300 candles per request, 10 requests per seconde | Fallback |
| Afgeraden | Kraken (maar 720 candles historie), Bitvavo ([voorwaarden](https://bitvavo.com/en/developer-agreement) verbieden opslaan en cachen) | – | Niet gebruiken |
| Exchange-abstractie | [CCXT](https://github.com/ccxt/ccxt) | MIT | Hergebruiken |
| AEX-data | [yfinance](https://github.com/ranaroussi/yfinance) | Apache-2.0, maar onofficieel; Yahoo is "personal use only" | Experimenteel. Upgradepad: [EODHD](https://eodhd.com/pricing) €29,99 per maand, te delen |
| AEX afgevallen | Twelve Data (AEX alleen EOD, vanaf $79), Massive/Polygon, Marketstack, Tiingo (alleen US; Tiingo verbiedt delen), Alpha Vantage (US-intraday) | – | Niet geschikt |
| Charts | [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) v5.2 | Apache-2.0, met verplichte TradingView-attributie (optie `attributionLogo`) | Hergebruiken |
| Analysegrafieken | [Apache ECharts](https://echarts.apache.org) 6 | Apache-2.0 | Equity-curve, drawdown, heatmaps |
| Afgeraden charts | TradingView Advanced Charts (alleen gratis voor publieke sites), Highcharts (commercieel) | – | Niet gebruiken |
| Indicatoren | [TA-Lib](https://pypi.org/project/TA-Lib/) 0.8 + [pandas-ta-classic](https://github.com/xgboosted/pandas-ta-classic) | BSD-2 / MIT. TA-Lib heeft nu wheels, dus geen C-build nodig. pandas-ta (origineel) is offline: niet gebruiken. | Hergebruiken |
| Backtesting | [vectorbt](https://github.com/polakowo/vectorbt) (open source) | Apache-2.0 + Commons Clause (niet doorverkopen als product). Snel, met fees en slippage als parameters en rolling splits voor walk-forward. | Hergebruiken |
| Ter inspiratie | [freqtrade](https://github.com/freqtrade/freqtrade) (GPL, crypto, dry-run), [NautilusTrader](https://pypi.org/project/nautilus_trader/) (LGPL, realistische fills), [OpenBB ODP](https://github.com/OpenBB-finance/OpenBB) (Apache-2.0) | GPL-code niet kopiëren | Ideeën en eventueel later |
| AI-patronen | [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Apache-2.0 | Promptstructuur (technisch, risico, samenvatting) als inspiratie |
| UX-referentie | [TradingView](https://www.tradingview.com/pricing/) (gratis: 2 indicatoren, 5000 bars), [TrendSpider](https://trendspider.com/pricing/) ($49+; AI-assistent bij de chart) | Commercieel | Alleen als voorbeeld |

**Zelf bouwen:**
- data-ingest met versheidscontrole
- signal engine
- signaalformaat en logboek
- walk-forward orchestratie en rapporten
- paper-trading-ledger met risicolimieten
- LLM-uitleglaag met cijfercontrole
- het dashboard zelf

## 3. MVP: de kleinste versie die echt test

**Scope MVP (fase 0–4):**
1. **Instrumenten:** 10 crypto-pairs (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOGE, DOT tegen USDT) op 15m en 1h, plus later 5 AEX-aandelen (ASML, Shell, ING, Adyen, Philips) op 1h als experimenteel.
2. **Grafieken:** candlesticks, volume, EMA-overlays en een RSI-paneel; intervalkeuze; per account een watchlist; altijd zichtbaar: bron, laatste candle-tijd en vertraging.
3. **Signal engine:** één strategie-familie met alle signaalvelden (zie hieronder) en een versheidspoort.
4. **Backtest-rapport:** per strategie en instrument, walk-forward, na kosten, tegenover benchmarks.
5. **Paper trading:** signalen automatisch "virtueel uitvoeren" met risicolimieten; alles gelogd.
6. **Accounts:** voor de groep, via invite; geen open registratie.

**Uitbreiden:**
- Meer instrumenten: alleen configuratie (`instruments.yaml`) en backfill erbij.
- Meer markten: een nieuwe `DataSource`-adapter.
- Meer methoden: een nieuwe strategy-module die eerst door dezelfde testpijplijn moet.

## 4. Technische opzet (voorkeur)

```
[Browser] ── Next.js (Vercel Hobby) ── Supabase (Postgres + Auth + RLS)
                                             ▲
              Python worker (Docker, Hetzner VPS ~€5,49/mnd)
              ├─ ingest  (cron, elke 15 min: CCXT/Binance, yfinance)
              ├─ engine  (indicatoren → signalen, versheidspoort)
              ├─ backtest(vectorbt, offline/handmatig, Parquet-historie op VPS)
              ├─ paper   (ledger + risicolimieten)
              └─ explain (LLM-uitleg, alleen op berekende JSON)
```

- **Frontend:** Next.js (App Router, TypeScript), Lightweight Charts en ECharts, Tailwind. Leest direct uit Supabase met de user-JWT; RLS zorgt dat watchlists per gebruiker blijven. Er is geen aparte API-server nodig, wat minder onderdelen betekent.
- **Database: Supabase Free** (500 MB, Auth inbegrepen).
  - Tabellen: `instruments`, `candles` (alleen recente vensters: ongeveer 90 dagen 15m en 2 jaar 1h), `data_status`, `signals`, `paper_trades`, `backtest_runs`, `watchlists`, `profiles`.
  - Lange historie voor backtests staat als Parquet op de VPS, niet in Postgres.
  - Geen TimescaleDB: Supabase heeft dat deprecated op PG17.
  - Schatting: 10 coins × 90 dagen 15m is ongeveer 86k rijen; ruim binnen de limiet.
- **Worker: Python 3.12, uv, Docker Compose** op één kleine VPS. Waarom een VPS:
  - De 15-minuten-cron via GitHub Actions kost bij een private repo meer dan de 2000 gratis minuten (ongeveer 2900 per maand).
  - Render Free valt in slaap.
  - Hetzner CX23 kost ongeveer €5,49 per maand; die prijs komt uit bronnen van derden, dus eerst op de Hetzner-site controleren.
  - Gratis start: tijdens fase 0–2 draait alles lokaal met `docker compose`.
- **AI: Claude Haiku 5.5** ($0,10 / $0,50 per miljoen tokens). Bij ongeveer 200 uitleggen per dag is dat circa $2 per maand. Alternatief: Gemini Flash-Lite free tier, maar die traint op je prompts.
- **Secrets:**
  - API-keys (LLM, Supabase service role) alleen in `.env` op de VPS en in Vercel env vars.
  - In de repo staat alleen `.env.example`.
  - `gitleaks` in CI en pre-commit.
  - De frontend krijgt alleen de anon key; RLS beschermt de data.

### Signal engine: methoden beperkt houden
Start met één samenhangende set waarin elke component een andere rol heeft:

| Rol | Methode | Overlap en opmerking |
|---|---|---|
| Trendrichting / filter | EMA 50 versus EMA 200 (op 1h) | MA-crossover en MACD meten bijna hetzelfde: kies er één |
| Timing / momentum | RSI(14) pullback in de trendrichting | RSI en Stochastic overlappen: alleen RSI |
| Volume-bevestiging | Volume ten opzichte van het 20-periode gemiddelde | Onafhankelijk van prijsindicatoren |
| Risico / stops | ATR(14): stop op 1,5×ATR, sizing op ATR | Volatiliteit, geen richting |
| Doelen | Recente swing-high/-low (pivots) als steun/weerstand; anders een vaste R-multiple | Pas in fase 4 als variant testen |

MACD, Bollinger en patroonherkenning komen pas later, als losse varianten die tegen deze baseline worden getest. Een methode komt er alleen bij als die out-of-sample na kosten iets toevoegt.

**Signaalrecord (opgeslagen in `signals`):**
- `instrument`, `interval`, `direction`
- `entry`, `invalidation` (koers of conditie waarbij het signaal vervalt), `stop_loss`, `target`
- `rr_ratio` (berekend na geschatte kosten)
- `strength` (regelgebaseerd), `reasons[]`, gesplitst in "gemeten feit" (bijvoorbeeld "RSI = 34,2") en "aanname" (bijvoorbeeld "trend zet door")
- `data_source`, `last_candle_at`, `data_delay`
- `cost_assumptions` (fee, spread, slippage)
- `liquidity_ok`, `strategy_version`, `created_at`

**`NO_TRADE` met reden is een volwaardige uitkomst.** Redenen zijn bijvoorbeeld zwak signaal, te lage R/R, illiquide of data niet vers.

**Versheidspoort:** er wordt geen signaal gegenereerd als:
- de laatste candle niet gesloten is,
- de laatste candle ouder is dan interval plus tolerantie,
- er gaten in het venster zitten,
- of de bron als `delayed`/`stale` gemarkeerd staat.

De UI toont dan "geen analyse: data verouderd".

### Veilig testen
- **Look-ahead voorkomen:** alleen gesloten candles gebruiken; het signaal op candle *t* wordt uitgevoerd op de open van *t+1*. Een unittest controleert dat het verschuiven van toekomstige data de signalen tot *t* niet verandert.
- **Periodes:**
  - Train/test-split op tijd (bijvoorbeeld 2021–2024 train, 2025 test, 2026 als hold-out die pas aan het eind wordt aangeraakt).
  - Walk-forward via rolling splits in vectorbt.
  - Weinig parameters en grove grids, tegen overfitting.
- **Kosten:** fee en spread per bron in de configuratie (exchange-tarieven zelf opzoeken en invullen), slippage als percentage plus ATR-fractie, en een liquiditeitsfilter op minimaal volume.
- **Metrieken:** rendement na kosten, maximale drawdown, aantal trades, winrate, gemiddelde R, profit factor, exposure.
- **Benchmarks:** buy-and-hold, en random entry met dezelfde stops en targets.
- **Kalibratie:** kanspercentages pas tonen bij voldoende out-of-sample signalen (bijvoorbeeld ≥200), met een Brier-score en reliability-plot.
- **Paper trading:**
  - Maximaal 1% risico per trade.
  - Maximaal 3% dagverlies; daarna geen nieuwe paper trades die dag.
  - Maximaal N open posities.
  - Elke virtuele trade gekoppeld aan zijn signaal, voor evaluatie achteraf.
- **Geen echte orders in dit prototype.** De code bevat bewust geen exchange-keys met trade-rechten.

### LLM-laag (pas vanaf fase 5)
- **Input:** het signaal-JSON. **Output:** uitleg in het Nederlands met de vaste kopjes Feiten, Aannames, Risico's en Wanneer ongeldig.
- **Post-check:** elk getal in de tekst moet voorkomen in de input. Anders wordt de uitleg afgewezen en blijft alleen de regel-uitleg over.
- Een vaste disclaimer staat in de UI, niet in de prompt.
- **Waarde meten:** vrienden beoordelen de uitleg (duim omhoog of omlaag plus "begrijpelijk" en "klopt"). Pas uitbreiden (nieuws, sentiment, multi-agent) als dat aantoonbaar iets toevoegt.

## 5. Kosten

| Post | Kosten | Limiet / risico |
|---|---|---|
| GitHub | €0 | Een private repo op Free heeft geen afdwingbare branch protection en 2000 Actions-minuten. **Advies:** maak de repo publiek (er staan geen secrets in) voor branch protection en onbeperkte CI. Strategieën geheim houden? Dan een private repo, met PR-afspraken zonder harde afdwinging, of één lid op GitHub Pro. |
| Vercel Hobby | €0 | Alleen niet-commercieel gebruik. Bij overschrijding wordt de functie gepauzeerd. |
| Supabase Free | €0 | 500 MB DB. Pauze na een week inactiviteit; de worker houdt het actief. Pro kost $25. |
| VPS (Hetzner CX23) | ~€5,49 per maand | Prijs komt van derden, controleren. Tijdens fase 0–2: €0, lokaal. |
| Crypto-data | €0 | Binance-gewichtslimieten; publieke herdistributie valt niet onder de voorwaarden. |
| AEX-data | €0 (yfinance) | Kan breken; personal use. Officieel: EODHD €29,99 per maand. |
| LLM | ~€2 per maand | Haiku 5.5, met een budgetcap ingesteld in de console. |
| **Totaal** | **~€0 (fase 0–2) → ~€8 per maand (live)** | |

## 6. Bouwplan

Rollen in de groep:
- **A** — data/backend (Python)
- **B** — analyse/quant (Python)
- **C** — frontend (TypeScript)
- **D** — devops/QA
- **iedereen** — review van PR's

| Fase | Taken (rol) | Acceptatiecriteria |
|---|---|---|
| **0. Fundament** (week 1) | Repo, README, CONTRIBUTING, issue- en PR-templates, CI (ruff, mypy, pytest, eslint, tsc, gitleaks) en docker-compose (D). Supabase-project en schema-migraties (A). Next.js-skelet met Supabase Auth en invites (C). | `docker compose up` draait lokaal. CI is groen op een PR. Een vriend kan inloggen via invite. |
| **1. Data** | `DataSource`-interface plus een Binance/CCXT-adapter met Coinbase-fallback (A). Backfill naar Parquet en recente vensters naar Postgres (A). `data_status` per instrument en interval (A). Datakwaliteitstests: gaten, duplicaten, tijdzones in UTC (D). | 10 pairs × 2 intervallen zijn ingeladen en elke 15 minuten bijgewerkt. Een gat wordt gedetecteerd en gelogd. Er gaan geen ongesloten candles de DB in. |
| **2. Dashboard** | Chartpagina met candles, volume, EMA en RSI, intervalwissel en een bron/vertraging-badge (C). Watchlist CRUD met RLS (C+A). | Een gebruiker ziet alleen de eigen watchlist. De badge toont bron, laatste update en vertraging. Een verouderd instrument krijgt een duidelijke waarschuwing. |
| **3. Engine + backtest** | Indicatoren (TA-Lib) en baseline-strategie, plus een signaalrecord met `NO_TRADE` (B). Versheidspoort (A). Kostenmodel, walk-forward-runner, benchmarks en rapport naar `backtest_runs` (B). Look-ahead-test (D). | Een backtest-rapport per instrument met metrieken na kosten tegenover buy-and-hold en random. De look-ahead-test slaagt. Bij verouderde data wordt geen signaal gemaakt. |
| **4. Paper trading + signalenpagina** | Paper-ledger met risicolimieten (B). Signalenpagina met alle velden, filters en status (C). Evaluatie-view die signalen naast hun uitkomst toont (C). AEX experimenteel via yfinance-adapter op 1h (A). | Signalen verschijnen live en openen virtuele trades. De dagverlieslimiet blokkeert aantoonbaar. Elke trade linkt naar zijn signaal. |
| **5. AI-uitleg** | Explain-service met getallen-post-check en een feedbackknop (A+C). Promptversies in de repo (B). | Een uitleg bevat alleen getallen uit de input; een test met een gemanipuleerde output wordt afgewezen. De kosten per dag zijn zichtbaar in de logs. |
| **6. Evaluatie** (na ≥4 weken paper trading) | Review van wat werkte. Besluit over nieuwe methoden, een AEX-betaalbron en kalibratie. | Een geschreven evaluatie in `docs/`. Elke nieuwe methode heeft een out-of-sample-onderbouwing. |

**Werkwijze:**
- Branches `feat/…` en `fix/…`.
- Een PR vereist 1 review en groene CI.
- Issues met labels per rol en een "good first issue" voor de beginners.
- GitHub is voor code en samenwerking; de draaiende site staat op Vercel, de data en accounts op Supabase en de processen op de VPS.

## 7. Eerste stap: repositorystructuur

```
koersradar/
├─ README.md            # doel, disclaimer, architectuur, lokaal starten
├─ CONTRIBUTING.md      # branches, PR-regels, code style
├─ .env.example         # alleen namen, nooit waarden
├─ docker-compose.yml   # worker + lokale Postgres (of Supabase CLI)
├─ .github/
│  ├─ workflows/ci.yml  # ruff, mypy, pytest, eslint, tsc, gitleaks
│  ├─ ISSUE_TEMPLATE/   pull_request_template.md
├─ config/
│  ├─ instruments.yaml  # pairs/tickers, bron, intervallen
│  └─ costs.yaml        # fee/spread/slippage per bron
├─ supabase/migrations/ # SQL-schema + RLS-policies
├─ worker/              # Python (uv)
│  ├─ pyproject.toml
│  ├─ koersradar/
│  │  ├─ sources/       # base.py (DataSource), ccxt_source.py, yfinance_source.py
│  │  ├─ ingest/        # scheduler, backfill, quality checks
│  │  ├─ indicators/    # TA-Lib wrappers
│  │  ├─ strategies/    # baseline_trend_pullback.py
│  │  ├─ signals/       # model.py (signaalrecord), freshness.py
│  │  ├─ backtest/      # walkforward.py, costs.py, benchmarks.py, report.py
│  │  ├─ paper/         # ledger.py, risk.py
│  │  └─ explain/       # llm.py, number_check.py, prompts/
│  └─ tests/            # incl. test_no_lookahead.py
├─ web/                 # Next.js (App Router, TS)
│  ├─ app/(auth)/ app/chart/[symbol]/ app/signals/ app/backtests/
│  └─ lib/supabase.ts components/Chart.tsx
└─ docs/                # architectuur, datavoorwaarden, evaluaties
```

**Lokaal beginnen:**
1. Installeer Git, Docker Desktop, Node 20+ (pnpm), Python 3.12 en [uv](https://docs.astral.sh/uv/).
2. Maak een GitHub-organisatie met de repo `koersradar`, nodig de vrienden uit en clone de repo.
3. Kopieer `.env.example` naar `.env`. Maak een Supabase-project aan (of start lokaal met `supabase start`) en vul de URL en keys in.
4. Draai `supabase db push` voor de migraties.
5. Worker:
   - `cd worker && uv sync && uv run pytest`
   - `uv run python -m koersradar.ingest.backfill --days 30` (eerst testen of Binance vanaf een NL-IP werkt; anders Coinbase)
6. Web: `cd web && pnpm i && pnpm dev`, daarna http://localhost:3000.
7. Alles tegelijk: `docker compose up`.

## Verificatie (end-to-end, na fase 4)
- `uv run pytest`: dit omvat de look-ahead-test, de versheidspoort (verouderde data geeft `NO_TRADE`), het kostenmodel en de risicolimieten.
- Backfill draaien en de `data_status` controleren. Een gat simuleren (rij verwijderen) en kijken of de engine weigert te signaleren.
- Een backtest-rapport bekijken: metrieken na kosten staan naast buy-and-hold en random entry.
- Twee testaccounts: watchlists zijn gescheiden (RLS). De badge toont bron, laatste update en vertraging.
- In de repo staan geen secrets (gitleaks groen), en de frontend-bundle bevat alleen de anon key.

## Openstaande keuze (standaard gekozen)
- **Repo:** publiek (gratis branch protection en CI). Kan ook privé, met minder afdwinging.
- **AEX:** yfinance, experimenteel, op 1h. Na fase 6 beslissen over EODHD.
- **Projectmap:** `Atar IT Solutions/Koersradar/`. Uitvoering bouwt dit project op; het plan zelf wijzigt nog niets.
