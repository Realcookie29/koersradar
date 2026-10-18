# Nieuwe instapideeën: opzet

Vastgelegd op 18 oktober 2026, **voordat** er uitkomsten zijn bekeken (commit 751da11). De uitkomsten staan onderaan.

## Waarom
De varianten van `trend-pullback` (zie [backtest-varianten.md](backtest-varianten.md)) komen zonder kosten allemaal rond 0R uit. Het instapsignaal voorspelt de richting niet. Extra filters lossen dat niet op, dus we testen een paar wezenlijk andere ideeën.

Er kwam nog iets uit naar voren: de kosten wegen zwaar bij een krappe stop. De ideeën hieronder hebben daarom een ruimere stop en geen vast doel. Ze stappen uit op een eigen uitstapregel, zodat een winnaar kan doorlopen.

## De ideeën
Vaste instellingen, gekozen op basis van gangbare regels uit de literatuur en niet afgestemd op onze data. Tijden in uren gelden voor zowel 15m als 1h.

| Idee | Instap (op de slotkoers) | Stop | Uitstap |
|---|---|---|---|
| breakout | slot boven de hoogste high van de vorige 24 uur, en slot boven EMA 200 | 2× ATR | slot onder de laagste low van de vorige 12 uur |
| breakout-rust | als breakout, maar alleen als de koersband van de vorige 24 uur smaller was dan normaal (onder de mediaan van de 30 dagen ervoor) | 2× ATR | als breakout |
| momentum | munt hoort bij de 3 sterkste van de 10 over de laatste 7 dagen, en stijgt over die 7 dagen | 2× dag-ATR | munt zakt uit de top 5 of daalt over 7 dagen |
| terugval | slot boven EMA 200 en RSI(2) onder 10 (kortdurende dip in een stijgende markt) | 3× ATR | slot boven het gemiddelde van de laatste 5 candles |

Waarom deze vier:
- **breakout**: trends beginnen vaak met een uitbraak. Dat is het tegenovergestelde van kopen in een dip.
- **breakout-rust**: een uitbraak na een rustige periode is vaker het begin van een echte beweging.
- **momentum**: in crypto blijven de sterkste munten vaak een tijdje de sterkste. De stop gebruikt de dag-ATR, omdat zo'n positie dagen loopt.
- **terugval**: de klassieke Connors-regel, korte dips in een stijgende markt herstellen vaak snel. Dat is een ander gedrag dan de andere drie.

Voor alle ideeën gelden dezelfde regels als in de backtest: dezelfde kosten, hetzelfde liquiditeitsfilter, instap op de open van de volgende candle, en één positie tegelijk per munt. Een trade is ongeveer even groot als bij `trend-pullback` (1% risico per trade).

## Spelregel
1. Alle ideeën draaien alleen op de **ontwikkelperiode 2021 t/m 2024**, voor 1h en 15m.
2. Gekozen wordt per tijdschaal het idee met de hoogste gemiddelde R na kosten, met minstens 100 trades.
3. Alleen dat idee gaat **één keer** door 2025. 2026 blijft onaangeroerd.
4. We noemen een idee pas veelbelovend als **alle drie** gelden:
   - gemiddelde R na kosten boven 0 in de ontwikkelperiode én in 2025
   - in 2025 minstens 2 van de 4 kwartalen positief
   - beter dan willekeurige instap met dezelfde stop en uitstap
5. Ook een veelbelovend idee gaat niet meteen live. De volgende stap is dan paper trading: signalen tonen en bijhouden, zonder echt geld.

## Uitkomsten
10 crypto-paren van Binance. Gemiddelde R per trade na kosten, met tussen haakjes zonder kosten. "Beter dan toeval" is het deel van 100 rondes willekeurige instap (zelfde stop en uitstap, ongeveer even veel trades) dat slechter uitkwam.

**1h, 2021 t/m 2024**

| Idee | Trades | Winrate | Gem. R | Kwartalen positief | Willekeurig | Beter dan toeval |
|---|---|---|---|---|---|---|
| breakout | 3.654 | 28,8% | −0,03 (+0,16) | 5 van 16 | −0,14 | 98% |
| breakout-rust | 2.947 | 28,7% | −0,04 (+0,17) | 5 van 16 | −0,14 | 100% |
| **momentum** | 2.642 | 25,7% | **+0,05** (+0,09) | 7 van 16 | +0,00 | 100% |
| terugval | 7.017 | 49,0% | −0,09 (+0,02) | 0 van 16 | −0,12 | 100% |

Controle op 2025: momentum **−0,03R** (777 trades, 1 van 4 kwartalen positief, willekeurig −0,04R, beter dan toeval 69%).

**15m, 2021 t/m 2024**

| Idee | Trades | Winrate | Gem. R | Kwartalen positief | Willekeurig | Beter dan toeval |
|---|---|---|---|---|---|---|
| breakout | 6.850 | 20,6% | −0,14 (+0,16) | 3 van 16 | −0,24 | 95% |
| breakout-rust | 5.341 | 20,3% | −0,13 (+0,19) | 3 van 16 | −0,24 | 96% |
| **momentum** | 4.604 | 19,5% | **+0,02** (+0,05) | 7 van 16 | −0,00 | 100% |
| terugval | 29.398 | 31,7% | −0,17 (+0,03) | 0 van 16 | −0,19 | 100% |

Controle op 2025: momentum **−0,03R** (1.335 trades, 1 van 4 kwartalen positief, willekeurig −0,03R, beter dan toeval 80%).

## Conclusie
- **Geen enkel idee is veelbelovend volgens de spelregel.** Momentum was het enige idee dat na kosten positief uitkwam in 2021 t/m 2024, maar in 2025 is het op beide tijdschalen negatief en niet duidelijk beter dan toeval.
- Er is wel vooruitgang ten opzichte van `trend-pullback`: **breakout heeft zonder kosten een echte voorsprong** (+0,16R tot +0,19R, en duidelijk beter dan willekeurige instap). Die voorsprong is alleen kleiner dan de kosten. Op 1h blijft er −0,03R over, op 15m −0,14R.
- Hoe korter de tijdschaal, hoe zwaarder de kosten wegen. Dat wijst richting een langere tijdschaal (4 uur of dag) of lagere kosten (maker-orders in plaats van taker).
- Terugval (Connors) wint vaak, maar met kleine winsten. De kosten maken dat ruim negatief.
- Een vervolgonderzoek moet opnieuw vooraf worden vastgelegd. De cijfers van 2025 zijn nu bekeken, dus die tellen bij een vervolg niet meer als schone controle. Daarvoor blijft 2026 over als hold-out.

## Zelf herhalen
```bash
python -m koersradar.backtest.ideas_research --interval 1h                        # alleen 2021 t/m 2024
python -m koersradar.backtest.ideas_research --interval 1h --check-test momentum  # eenmalig 2025
```
Draai dit vanuit de hoofdmap van de repo, zodat `DATA_DIR` uit `.env` klopt.
