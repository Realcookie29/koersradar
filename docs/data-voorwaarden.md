# Databronnen en voorwaarden

Gecontroleerd op 2026-10-17. Controleer dit opnieuw voordat je iets aan de opzet verandert.

| Bron | Gebruik | Belangrijkste beperking |
|---|---|---|
| Binance (`data-api.binance.vision`, via CCXT) | Primaire crypto-bron | Werkt vanaf een NL-IP (getest op 2026-10-17). Publieke herdistributie valt niet onder de [Vision-voorwaarden](https://data.binance.vision/Binance_Vision-Terms_of_Use.pdf). |
| Coinbase Exchange (via CCXT) | Crypto-fallback | Noteert in USD in plaats van USDT, dus koersen kunnen licht afwijken. 300 candles per request. |
| yfinance (Yahoo) | AEX, **experimenteel** | Onofficieel en Yahoo is "personal use only". 15m-data maximaal 60 dagen terug, 1h maximaal 730 dagen. Kan zonder aankondiging breken. |
| Bitvavo | **Niet gebruiken** | De [Developer Agreement](https://bitvavo.com/en/developer-agreement) verbiedt opslaan en cachen. |
| Kraken | **Niet gebruiken als hoofdbron** | Maximaal 720 candles historie via de API. |

## Delen met de groep
Bijna alle persoonlijke datalicenties staan alleen gebruik door de abonnee zelf toe. Ruwe koersdata
tonen aan anderen geldt formeel als herdistributie. Daarom:
- houden we de groep klein en besloten (alleen op uitnodiging, geen publieke pagina's);
- tonen we bij AEX vooral afgeleide signalen en indicatoren;
- lezen we bij een betaalde bron (bv. EODHD) eerst de voorwaarden over delen.

## Upgradepad AEX
De goedkoopste officiële bron met intraday-data van Amsterdam is [EODHD](https://eodhd.com/pricing),
het "Active trader"-plan (€29,99 per maand). Die levert 5m- en 1h-bars die pas na sluitingstijd
definitief zijn. Besluit hierover na fase 6.
