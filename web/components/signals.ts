import type { SignalRow } from "@/lib/types";

export const STEPS = ["Data vers", "Liquide", "Trend omhoog", "Pullback", "Keerpunt", "R/R ≥ 1,5"] as const;

/** Hoeveel regels van de strategie haalt dit instrument nu (0..6)? */
export function stepsPassed(s: SignalRow): number {
  if (s.decision === "TRADE") return STEPS.length;
  const r = s.no_trade_reason ?? "";
  if (r.startsWith("geen analyse") || r.startsWith("te weinig historie")) return 0;
  if (r.includes("liquiditeit")) return 1;
  if (r.includes("opwaartse trend")) return 2;
  if (r.startsWith("geen pullback")) return 3;
  if (r.includes("niet gekeerd") || r.includes("te laat")) return 4;
  if (r.includes("risico/rendement")) return 5;
  return 0;
}

const INTERVAL_MS = { "15m": 15 * 60_000, "1h": 60 * 60_000 } as const;

/** Een kans is actueel zolang de volgende candle nog niet afgesloten is (+ marge). */
export function isCurrent(s: SignalRow, now: number): boolean {
  const ms = INTERVAL_MS[s.interval];
  return now - new Date(s.last_candle_at).getTime() < 2 * ms + 5 * 60_000;
}
