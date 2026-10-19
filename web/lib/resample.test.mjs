// Tests voor 4h- en dagcandles uit 1h-candles. Draaien: npm test.
import assert from "node:assert/strict";
import { test } from "node:test";
import { resample } from "./resample.ts";

const T0 = Date.UTC(2026, 9, 1); // 1 okt 2026 00:00 UTC
const hours = (n, start = 0) =>
  Array.from({ length: n }, (_, i) => {
    const c = 100 + start + i;
    return { open_time: new Date(T0 + (start + i) * 3600_000).toISOString(), open: c - 0.5, high: c + 1, low: c - 1, close: c, volume: 1 };
  });

test("dagcandle: open van het eerste uur, slot van het laatste, uiterste high/low, opgeteld volume", () => {
  const { bars, lastClosed } = resample(hours(48), "1d");
  assert.equal(bars.length, 2);
  assert.equal(lastClosed, true);
  const d = bars[0];
  assert.equal(d.open_time, new Date(T0).toISOString());
  assert.equal(d.open, 99.5);
  assert.equal(d.close, 123);
  assert.equal(d.high, 124);
  assert.equal(d.low, 99);
  assert.equal(d.volume, 24);
});

test("4 uur: grenzen op 00, 04, 08 … UTC", () => {
  const { bars } = resample(hours(12), "4h");
  assert.deepEqual(
    bars.map((b) => new Date(b.open_time).getUTCHours()),
    [0, 4, 8],
  );
});

test("lopende candle: zichtbaar in de grafiek, weg bij partial=false", () => {
  const h = hours(30); // dag 2 heeft pas 6 uur
  const shown = resample(h, "1d");
  assert.equal(shown.bars.length, 2);
  assert.equal(shown.lastClosed, false);
  assert.equal(resample(h, "1d", false).bars.length, 1);
});

test("ontbrekende uren (onderhoud) breken de indeling niet", () => {
  const h = [...hours(10), ...hours(10, 14)]; // uur 10-13 ontbreekt
  const { bars } = resample(h, "1d");
  assert.equal(bars.length, 1);
  assert.equal(bars[0].volume, 20);
});
