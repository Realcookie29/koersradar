// Tests voor de rekenregels van het journaal. Draaien: npm test (Node 22.18+ leest TypeScript zelf).
import assert from "node:assert/strict";
import { test } from "node:test";
import { pnlPerUnit, riskPerUnit, rMultiple, sizeForRisk, stats, validate } from "./journal.ts";

const long = { direction: "long", entry: 100, stop: 95, costPct: 0.001 };
const short = { direction: "short", entry: 100, stop: 105, costPct: 0.001 };
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test("zonder kosten is R gewoon winst gedeeld door stopafstand", () => {
  const free = { ...long, costPct: 0 };
  close(riskPerUnit(free), 5);
  close(rMultiple(free, 110), 2);
  close(rMultiple(free, 95), -1);
});

test("kosten maken het risico groter en de winst kleiner", () => {
  close(riskPerUnit(long), 100 * 1.001 - 95 * 0.999); // 5,195
  close(pnlPerUnit(long, 110), 110 * 0.999 - 100 * 1.001); // 9,789
  close(rMultiple(long, 95), -1); // stop geraakt = precies -1 R, ook na kosten
  assert.ok(rMultiple(long, 110) < 2);
});

test("short rekent andersom", () => {
  close(riskPerUnit(short), 105 * 1.001 - 100 * 0.999);
  close(rMultiple(short, 105), -1);
  assert.ok(rMultiple(short, 90) > 1.8);
});

test("positiegrootte: een geraakte stop kost precies het gekozen risico", () => {
  const qty = sizeForRisk(long, 10);
  close(qty * riskPerUnit(long), 10);
  assert.equal(sizeForRisk(long, 0), null);
});

test("ongeldige niveaus worden geweigerd", () => {
  assert.ok(validate("long", 100, 105, null));
  assert.ok(validate("short", 100, 95, null));
  assert.ok(validate("long", 100, 95, 90));
  assert.equal(validate("long", 100, 95, 110), null);
  assert.equal(validate("short", 100, 105, null), null);
});

test("samenvatting telt alleen gesloten trades", () => {
  const base = { direction: "long", entry_price: 100, stop_loss: 95, cost_pct: 0, quantity: 2 };
  const s = stats([
    { ...base, exit_price: 110 },
    { ...base, exit_price: 95 },
    { ...base, exit_price: null },
  ]);
  assert.equal(s.trades, 2);
  close(s.avgR, 0.5);
  close(s.totalR, 1);
  close(s.pnl, 2 * 10 - 2 * 5);
  assert.equal(s.winrate, 0.5);
});
