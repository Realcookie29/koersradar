// Grotere candles (4 uur, dag) maken uit 1h-candles, in UTC: dag = 00:00 tot 00:00 UTC,
// 4 uur = 00–04, 04–08, … UTC. Zelfde indeling als de backtest (worker/koersradar/strategies/ideas.py).

export type OhlcvBar = { open_time: string; open: number; high: number; low: number; close: number; volume: number };

export const BUCKET_HOURS = { "4h": 4, "1d": 24 } as const;
export type BigInterval = keyof typeof BUCKET_HOURS;

const HOUR = 3600_000;

/**
 * Voeg 1h-candles (oud naar nieuw) samen. De laatste candle kan nog niet gesloten zijn;
 * `partial` geeft aan of die meetelt (voor de grafiek wel, voor berekeningen niet).
 */
export function resample(bars: OhlcvBar[], interval: BigInterval, partial = true): { bars: OhlcvBar[]; lastClosed: boolean } {
  const size = BUCKET_HOURS[interval] * HOUR;
  const out: OhlcvBar[] = [];
  let startMs = -1;
  for (const b of bars) {
    const t = Date.parse(b.open_time);
    const bucket = Math.floor(t / size) * size;
    const cur = out.at(-1);
    if (cur && bucket === startMs) {
      cur.high = Math.max(cur.high, b.high);
      cur.low = Math.min(cur.low, b.low);
      cur.close = b.close;
      cur.volume += b.volume;
    } else {
      startMs = bucket;
      out.push({ open_time: new Date(bucket).toISOString(), open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume });
    }
  }
  const last = bars.at(-1);
  // Gesloten als de laatste 1h-candle het laatste uur van de bucket is.
  const lastClosed = !last || Date.parse(last.open_time) + HOUR >= startMs + size;
  if (!partial && !lastClosed) out.pop();
  return { bars: out, lastClosed };
}
