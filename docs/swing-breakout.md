# Swing-breakout: opzet

Vastgelegd op 18 oktober 2026, **voordat** er uitkomsten zijn bekeken (commit 713351c). De uitkomsten staan onderaan.

## Waarom
In [nieuwe-instap.md](nieuwe-instap.md) had breakout als enige idee zonder kosten een duidelijke voorsprong (+0,16R tot +0,19R, beter dan willekeurige instap). Op 15m en 1h waren de kosten groter dan die voorsprong. Op een langere tijdschaal zijn de bewegingen groter en wegen dezelfde kosten minder zwaar. Dit test of breakout als **swingtrade** (dagen tot weken) wel overeind blijft.

## De regels
De klassieke Turtle-regels (Richard Dennis, jaren 80), alleen long. De instellingen zijn overgenomen zoals ze bekendstaan. Er is niet gezocht naar betere waarden.

| Idee | Instap (op de slotkoers) | Stop | Uitstap |
|---|---|---|---|
| turtle-20 | slot boven de hoogste high van de vorige 20 candles | 2× ATR(20) | slot onder de laagste low van de vorige 10 candles |
| turtle-55 | slot boven de hoogste high van de vorige 55 candles | 2× ATR(20) | slot onder de laagste low van de vorige 20 candles |

Beide ideeën testen we op twee tijdschalen:
- **4 uur**
- **dag**: dit zijn precies de oorspronkelijke Turtle-regels

De candles worden gemaakt uit de 1h-historie (UTC, dag van 00:00 tot 00:00). Een candle telt pas mee als hij helemaal gesloten is. De rest is gelijk aan de eerdere tests:
- kosten
- liquiditeitsfilter
- instap op de open van de volgende candle
- één positie tegelijk per munt
- 1% risico per trade

Er is geen vast doel: een trade loopt door tot de stop of de uitstapregel.

## Periodes
De ontwikkelperiode is **2021 t/m 2025**. Bij de vorige tests was 2025 de controleperiode, maar breakout op 4 uur en dag is daar nooit op bekeken.

De controleperiode is **2026 (januari tot 18 oktober)**. Niemand heeft die data bekeken, en we gebruiken haar één keer.

## Spelregel
1. Alle vier de combinaties (2 ideeën × 2 tijdschalen) draaien alleen op de ontwikkelperiode.
2. Per tijdschaal kiezen we het idee met de hoogste gemiddelde R na kosten. Op de daggrafiek moet het idee minstens 50 trades hebben, op 4 uur minstens 100.
3. Alleen die twee keuzes gaan **één keer** door 2026.
4. We noemen een keuze pas veelbelovend als **alle drie** de volgende punten kloppen:
   - De gemiddelde R na kosten is positief, zowel in de ontwikkelperiode als in 2026.
   - De ontwikkelperiode is beter dan minstens 90% van 100 rondes willekeurige instap, met dezelfde stop en uitstap.
   - In 2026 zijn minstens 2 van de kwartalen positief. Het laatste, onvolledige kwartaal telt mee.
5. Op de daggrafiek levert 2026 waarschijnlijk weinig trades op. Bij minder dan 30 trades in 2026 spreken we hooguit van een "voorlopig" resultaat.
6. Ook een veelbelovend resultaat gaat niet meteen live. De volgende stap is dan paper trading.

## Uitkomsten
10 crypto-paren van Binance. Gemiddelde R per trade na kosten, met tussen haakjes zonder kosten. "Beter dan toeval" is het deel van 100 rondes willekeurige instap (zelfde stop en uitstap) dat slechter uitkwam.

**Dag, 2021 t/m 2025**

| Idee | Trades | Winrate | Gem. R | Kwartalen positief | Willekeurig | Beter dan toeval |
|---|---|---|---|---|---|---|
| turtle-20 | 252 | 35,3% | +0,82 (+0,97) | 7 van 20 | +0,20 | 92% |
| **turtle-55** | 134 | 31,3% | **+1,13** (+1,31) | 7 van 20 | +0,27 | 89% |

Controle op 2026: turtle-55 **+0,05R** (23 trades, 1 van 4 kwartalen positief, willekeurig −0,16R, beter dan toeval 59%).

**4 uur, 2021 t/m 2025**

| Idee | Trades | Winrate | Gem. R | Kwartalen positief | Willekeurig | Beter dan toeval |
|---|---|---|---|---|---|---|
| turtle-20 | 1.649 | 28,6% | +0,23 (+0,39) | 12 van 20 | +0,07 | 93% |
| **turtle-55** | 857 | 26,1% | **+0,61** (+0,83) | 10 van 20 | +0,30 | 95% |

Controle op 2026: turtle-55 **−0,14R** (150 trades, 1 van 4 kwartalen positief, willekeurig −0,20R, beter dan toeval 53%).

## Conclusie
- **Geen van beide keuzes is veelbelovend volgens de spelregel.**
  - Dag: al in de ontwikkelperiode net niet beter dan 90% van toeval (89%). In 2026 maar 1 van 4 kwartalen positief, op te weinig trades (23) om iets te zeggen.
  - 4 uur: haalde in de ontwikkelperiode alle eisen, maar verloor in 2026 na kosten (−0,14R). Het verschil met toeval was in 2026 weg (53%).
- Op een langere tijdschaal wegen de kosten wel veel minder: ongeveer 0,15R tot 0,2R tegen een beweging van soms meerdere R. Op dat punt klopte de verwachting.
- De winst in 2021 t/m 2025 komt vooral uit een paar sterke stijgingen. Ook willekeurige instap met dezelfde uitstapregel verdiende toen geld (+0,20R tot +0,30R). In 2026 verloor willekeurige instap (−0,16R tot −0,20R), dus was 2026 voor kopers een moeilijk jaar. Een strategie die alleen long gaat, verdient dan weinig.
- **2026 is nu bekeken.** Er is geen schone historische controleperiode meer over. Elk volgend idee kan alleen eerlijk worden getoetst door het vanaf nu vooruit te volgen (paper trading).

## Zelf herhalen
```bash
python -m koersradar.backtest.ideas_research --interval 1d                         # alleen 2021 t/m 2025
python -m koersradar.backtest.ideas_research --interval 4h --check-test turtle-55  # eenmalig 2026
```
Draai dit vanuit de hoofdmap van de repo.
