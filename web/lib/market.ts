// Marktoverzicht: kerncijfers per instrument uit gesloten 1h-candles (oud naar nieuw).
// Alleen informatie, geen koopadvies: de backtests laten zien dat geen van deze kenmerken
// op zichzelf na kosten winst oplevert (zie docs/nieuwe-instap.md en docs/swing-breakout.md).

import { ema } from "./indicators.ts"; // met extensie, zodat npm test (Node) het bestand ook vindt

export type Bar = { open_time: string; high: number; low: number; close: number };

export type Overview = {
  close: number;
  change24h: number | null;
  change7d: number | null;
  /** Slot boven de hoogste high van de 24 uur daarvoor (op de laatste candle). */
  breakout24h: boolean;
  /** Slot boven de hoogste high van de 20 dagen daarvoor (Turtle-regel op dagbasis). */
  breakout20d: boolean;
  /** Waar de slotkoers staat in de band van de laatste 20 dagen: 0 = laagste, 1 = hoogste. */
  rangePos20d: number | null;
  trendUp: boolean | null;
};

// In uren kalendertijd, niet in aantal candles: aandelen hebben alleen candles tijdens beursuren.
const HOUR = 3600_000;
const H24 = 24;
const D7 = 7 * 24;
const D20 = 20 * 24;

const maxOf = (xs: number[]) => xs.reduce((m, x) => Math.max(m, x), -Infinity);
const minOf = (xs: number[]) => xs.reduce((m, x) => Math.min(m, x), Infinity);

export function overview(bars: Bar[]): Overview | null {
  const n = bars.length;
  if (!n) return null;
  const close = bars[n - 1].close;
  const last = Date.parse(bars[n - 1].open_time);
  /** Laatste candle die minstens `hours` uur voor de laatste ligt; null als de historie te kort is. */
  const at = (hours: number) => {
    const cutoff = last - hours * HOUR;
    for (let i = n - 2; i >= 0; i--) if (Date.parse(bars[i].open_time) <= cutoff) return i;
    return null;
  };
  const i24 = at(H24);
  const i20 = at(D20);
  const back = (i: number | null) => (i === null ? null : close / bars[i].close - 1);
  const highsBefore = (i: number | null) => (i === null ? null : maxOf(bars.slice(i, n - 1).map((b) => b.high)));
  const prev24 = highsBefore(i24);
  const prev20d = highsBefore(i20);
  const window = bars.slice(i20 === null ? 0 : i20 + 1);
  const hi = maxOf(window.map((b) => b.high));
  const lo = minOf(window.map((b) => b.low));
  const closes = bars.map((b) => b.close);
  const e50 = ema(closes, 50).at(-1) ?? null;
  const e200 = ema(closes, 200).at(-1) ?? null;
  return {
    close,
    change24h: back(i24),
    change7d: back(at(D7)),
    breakout24h: prev24 !== null && close > prev24,
    breakout20d: prev20d !== null && close > prev20d,
    rangePos20d: i20 !== null && hi > lo ? (close - lo) / (hi - lo) : null,
    trendUp: e50 !== null && e200 !== null ? e50 > e200 : null,
  };
}

/** Rang op 7-daags rendement (1 = sterkste); instrumenten zonder 7 dagen data krijgen geen rang. */
export function rankBy7d<T extends { change7d: number | null }>(rows: T[]): (T & { rank: number | null })[] {
  const sorted = rows.filter((r) => r.change7d !== null).sort((a, b) => b.change7d! - a.change7d!);
  return rows.map((r) => ({ ...r, rank: r.change7d === null ? null : sorted.indexOf(r) + 1 }));
}

export const BARS_NEEDED = D20 + 1;
