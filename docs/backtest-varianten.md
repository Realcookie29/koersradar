# Strategievarianten: wat we hebben geprobeerd

Onderzoek naar verbeteringen van `trend-pullback-0.1`, gedaan op 18 oktober 2026. De live scanner is hierdoor **niet** veranderd.

## Waarom
De backtest (`python -m koersradar.backtest.run`) laat zien dat de strategie na kosten verliest: −0,16R per trade op 1h en −0,19R op 15m in 2021 t/m 2024, en nog meer in 2025.

De oorzaak is duidelijk uit de trades:
- Twee op de drie trades raken de stop, één op de drie haalt het doel van 2R. Zonder kosten komt dat neer op ongeveer 0R. Het instapsignaal voorspelt de richting dus niet beter dan toeval.
- De kosten maken er verlies van. Een geraakt doel levert na fee, spread en slippage ongeveer 1,5R op in plaats van 2R.

## Opzet (vooraf vastgelegd)
Om te voorkomen dat we de regels afstemmen op toevallige meevallers:
1. Een vaste lijst van zes varianten, elk met een eigen reden (zie hieronder). Er is niet gezocht naar de beste instellingen.
2. Alle varianten draaien alleen op de **ontwikkelperiode 2021 t/m 2024**.
3. Gekozen wordt de variant met de hoogste gemiddelde R na kosten, met minstens 100 trades.
4. Alleen die variant gaat **één keer** door 2025. 2026 blijft onaangeroerd als hold-out.

| Variant | Wat | Waarom |
|---|---|---|
| basis | de huidige regels | ter vergelijking |
| ruime-stop | stop op 2,5× ATR in plaats van 1,5× | kosten zijn een kleiner deel van het risico |
| kostenfilter | alleen trades waarbij de kosten hooguit 10% van de stopafstand zijn | trades met relatief hoge kosten overslaan |
| dagtrend | alleen kopen als EMA 50 > EMA 200 op de daggrafiek van de munt zelf | met de grotere trend mee |
| btc-trend | alleen kopen als BTC op de daggrafiek stijgt | altcoins bewegen vaak met BTC mee |
| combinatie | kostenfilter + dagtrend + btc-trend | alles samen |

De dagtrend telt pas mee als de dagcandle gesloten is. Een test bewaakt dat er niet vooruit wordt gekeken.

## Uitkomsten
10 crypto-paren van Binance, gemiddelde R per trade na kosten (tussen haakjes zonder kosten), en het aantal kwartalen met een positief resultaat.

**1h, 2021 t/m 2024**

| Variant | Trades | Winrate | Gem. R | Kwartalen positief |
|---|---|---|---|---|
| basis | 2.081 | 33,1% | −0,16 (−0,00) | 2 van 16 |
| **ruime-stop** | 1.831 | 32,9% | **−0,09** (+0,03) | 5 van 16 |
| kostenfilter | 614 | 31,8% | −0,16 (−0,04) | 5 van 16 |
| dagtrend | 797 | 33,2% | −0,16 (+0,00) | 2 van 13 |
| btc-trend | 998 | 30,6% | −0,23 (−0,08) | 0 van 11 |
| combinatie | 166 | 33,1% | −0,13 (+0,00) | 2 van 6 |

Controle op 2025: ruime-stop **−0,24R** (406 trades, 0 van 4 kwartalen positief), basis −0,36R.

**15m, 2021 t/m 2024**

| Variant | Trades | Winrate | Gem. R | Kwartalen positief |
|---|---|---|---|---|
| basis | 2.281 | 32,6% | −0,19 (−0,02) | 2 van 16 |
| ruime-stop | 3.975 | 32,5% | −0,14 (+0,01) | 1 van 16 |
| **kostenfilter** | 335 | 34,6% | **−0,08** (+0,05) | 6 van 12 |
| dagtrend | 736 | 32,3% | −0,20 (−0,02) | 1 van 12 |
| btc-trend | 777 | 31,1% | −0,23 (−0,06) | 1 van 11 |
| combinatie | 46 | 37,0% | −0,03 (+0,11) | 3 van 6, valt af (minder dan 100 trades) |

Controle op 2025: kostenfilter **−0,42R**, maar met maar 9 trades. Daaruit valt niets af te leiden, behalve dat het niets positiefs bevestigt. Basis: −0,29R.

## Conclusie
- Geen enkele variant is winstgevend na kosten, niet in de ontwikkelperiode en niet in 2025.
- Ook zonder kosten blijven alle varianten rond 0R. De filters veranderen wanneer er gehandeld wordt, maar geven de instap geen voorspellende waarde.
- Een ruimere stop of een kostenfilter maakt het verlies kleiner, omdat de kosten zwaarder wegen bij een krappe stop. Een voorsprong ontstaat daar niet door.
- Een betere strategie vraagt dus om een **ander idee voor de instap**, niet om extra filters op deze. Volgens het plan moet elk nieuw idee eerst dezelfde test doorstaan.

## Zelf herhalen
```bash
cd worker
python -m koersradar.backtest.research --interval 1h                          # alle varianten, alleen 2021 t/m 2024
python -m koersradar.backtest.research --interval 1h --check-test ruime-stop  # eenmalig 2025
```
Een nieuwe variant voeg je toe aan `VARIANTS` in `worker/koersradar/backtest/research.py`. Doe dat vóórdat je naar de uitkomsten kijkt, en schrijf de reden erbij.
