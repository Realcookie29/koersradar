## Wat verandert er?
<!-- Kort: wat en waarom. Link het issue: Closes #.. -->

## Hoe getest?
- [ ] `pytest` / `npm run lint && npm run typecheck` lokaal groen
- [ ] Nieuwe logica heeft een test (zeker bij signalen, kosten, risico, data)

## Checklist
- [ ] Geen secrets, API-keys of `.env` in deze PR
- [ ] Raakt dit signalen of backtests? Dan: geen look-ahead (alleen gesloten candles, uitvoering op t+1)
- [ ] Nieuwe analysemethode? Dan: out-of-sample resultaat na kosten bijgevoegd
