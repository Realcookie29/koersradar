# Meedoen aan Koersradar

## Werkwijze
1. Pak een issue op (of maak er een met het template *Taak*) en wijs het aan jezelf toe.
2. Maak een branch: `feat/<korte-naam>` of `fix/<korte-naam>`.
3. Kleine commits en een PR naar `main` met het PR-template ingevuld.
4. **Minstens 1 review** van een ander groepslid en **groene CI** voordat je merget.
5. Squash-merge, daarna de branch verwijderen.

Labels per rol: `data-backend`, `quant`, `frontend`, `devops-qa`. Nieuw in programmeren?
Kijk bij `good first issue`.

## Lokaal checken voor je pusht
```bash
cd worker && ruff format . && ruff check . && mypy koersradar && pytest -q
cd web && npm run lint && npm run typecheck
```

## Regels die niet onderhandelbaar zijn
- **Geen secrets in git.** Gebruik `.env` (staat in `.gitignore`). CI draait gitleaks.
  Toch per ongeluk een key gecommit? Trek de key direct in en maak een nieuwe aan;
  hem uit de geschiedenis verwijderen is niet genoeg.
- **Geen look-ahead.** Signalen en backtests gebruiken alleen *gesloten* candles, en een signaal
  op candle *t* wordt uitgevoerd op de open van *t+1*.
- **Tijd is UTC** en altijd timezone-aware in Python (ruff-regel DTZ).
- **Een nieuwe analysemethode** komt er alleen bij met een out-of-sample backtest na kosten,
  vergeleken met de baseline en buy-and-hold.
- **Geen echte orders.** Er komen geen exchange-keys met handelsrechten in dit project.
- **Kanspercentages** tonen we pas als ze aantoonbaar gekalibreerd zijn op testdata.

## Code-stijl
- Python: ruff (format + lint), type hints, kleine pure functies die je kunt testen.
- TypeScript: eslint (Next.js-config), strict mode.
- Commentaar en UI-teksten in het Nederlands, code-identifiers in het Engels.
