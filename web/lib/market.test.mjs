// Tests voor het marktoverzicht. Draaien: npm test.
import assert from "node:assert/strict";
import { test } from "node:test";
import { BARS_NEEDED, overview, rankBy7d } from "./market.ts";

const bars = (closes) =>
  closes.map((c, i) => ({ open_time: new Date(i * 3600_000).toISOString(), high: c * 1.001, low: c * 0.999, close: c }));
const flat = (n, v = 100) => Array(n).fill(v);

test("rendement over 24 uur en 7 dagen", () => {
  const o = overview(bars([...flat(200), ...flat(167, 110), 121]));
  assert.ok(Math.abs(o.change24h - 0.1) < 1e-9);
  assert.ok(Math.abs(o.change7d - 0.21) < 1e-9);
});

test("te weinig historie geeft geen cijfer in plaats van een verkeerd cijfer", () => {
  const o = overview(bars(flat(10)));
  assert.equal(o.change24h, null);
  assert.equal(o.change7d, null);
  assert.equal(o.rangePos20d, null);
  assert.equal(o.trendUp, null);
  assert.equal(o.breakout24h, false);
  assert.equal(overview([]), null);
});

test("breakout alleen als de slot boven de eerdere highs uitkomt", () => {
  assert.equal(overview(bars([...flat(BARS_NEEDED), 105])).breakout20d, true);
  assert.equal(overview(bars([...flat(BARS_NEEDED), 100])).breakout20d, false);
  assert.equal(overview(bars([...flat(30), 100.05])).breakout24h, false); // binnen de oude high
  assert.equal(overview(bars([...flat(30), 101])).breakout24h, true);
});

test("positie in de 20-daagse band", () => {
  const up = Array.from({ length: BARS_NEEDED }, (_, i) => 100 + i);
  assert.ok(overview(bars(up)).rangePos20d > 0.99);
  assert.ok(overview(bars([...up].reverse())).rangePos20d < 0.01);
});

test("trend: EMA 50 boven EMA 200 bij een stijgende reeks", () => {
  const up = Array.from({ length: 300 }, (_, i) => 100 + i);
  assert.equal(overview(bars(up)).trendUp, true);
  assert.equal(overview(bars([...up].reverse())).trendUp, false);
});

test("rang op 7 dagen, zonder data geen rang", () => {
  const rows = rankBy7d([{ change7d: 0.05 }, { change7d: null }, { change7d: 0.2 }, { change7d: -0.1 }]);
  assert.deepEqual(
    rows.map((r) => r.rank),
    [2, null, 1, 3],
  );
});

test("aandelen: 24 uur en 7 dagen in kalendertijd, ook met gaten buiten beursuren", () => {
  // 9 candles per werkdag (09:00 t/m 17:00 UTC), 20 werkdagen vanaf maandag 7 sep 2026.
  const out = [];
  for (let d = 0; out.length < 20 * 9; d++) {
    const day = new Date(Date.UTC(2026, 8, 7 + d));
    if (day.getUTCDay() === 0 || day.getUTCDay() === 6) continue;
    for (let h = 9; h <= 17; h++) out.push({ t: Date.UTC(2026, 8, 7 + d, h), c: 100 + out.length });
  }
  const b = out.map(({ t, c }) => ({ open_time: new Date(t).toISOString(), high: c, low: c, close: c }));
  const o = overview(b);
  const close = b.at(-1).close;
  // 24 uur terug = hetzelfde klokuur op de vorige handelsdag: 9 candles terug.
  assert.ok(Math.abs(o.change24h - (close / b.at(-10).close - 1)) < 1e-9);
  // 7 dagen terug = 5 handelsdagen: 45 candles terug.
  assert.ok(Math.abs(o.change7d - (close / b.at(-46).close - 1)) < 1e-9);
});
