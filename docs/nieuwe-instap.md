# Nieuwe instapideeën: opzet

Vastgelegd op 18 oktober 2026, **voordat** er uitkomsten zijn bekeken. De uitkomsten komen onderaan zodra ze er zijn.

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
