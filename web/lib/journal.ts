// Rekenregels voor het handelsjournaal (paper trading). Dezelfde opzet als de backtest:
// kosten per kant (fee + halve spread + slippage), R = resultaat na kosten / gepland verlies na kosten.

export type Direction = "long" | "short";

/** Kosten per kant voor Binance volgens config/costs.yaml: fee 0,1% + halve spread 0,01% + slippage 0,05%. */
export const DEFAULT_COST_PCT = 0.0016;

export type JournalTrade = {
  id: number;
  user_id: string;
  instrument_id: number;
  signal_id: number | null;
  direction: Direction;
  opened_at: string;
  entry_price: number;
  stop_loss: number;
  target: number | null;
  quantity: number;
  cost_pct: number;
  reason: string | null;
  closed_at: string | null;
  exit_price: number | null;
  exit_note: string | null;
};

type Levels = { direction: Direction; entry: number; stop: number; costPct: number };

/** Verlies per eenheid als de stop wordt geraakt, inclusief kosten aan beide kanten. */
export function riskPerUnit({ direction, entry, stop, costPct }: Levels): number {
  return direction === "long"
    ? entry * (1 + costPct) - stop * (1 - costPct)
    : stop * (1 + costPct) - entry * (1 - costPct);
}

/** Resultaat per eenheid bij verkoop (long) of terugkoop (short) op `exit`, na kosten. */
export function pnlPerUnit({ direction, entry, costPct }: Omit<Levels, "stop">, exit: number): number {
  return direction === "long"
    ? exit * (1 - costPct) - entry * (1 + costPct)
    : entry * (1 - costPct) - exit * (1 + costPct);
}

export function rMultiple(levels: Levels, exit: number): number | null {
  const risk = riskPerUnit(levels);
  return risk > 0 ? pnlPerUnit(levels, exit) / risk : null;
}

/** Positiegrootte zodat een geraakte stop (na kosten) precies `riskAmount` kost. */
export function sizeForRisk(levels: Levels, riskAmount: number): number | null {
  const risk = riskPerUnit(levels);
  return risk > 0 && riskAmount > 0 ? riskAmount / risk : null;
}

export function levelsOf(t: JournalTrade): Levels {
  return { direction: t.direction, entry: t.entry_price, stop: t.stop_loss, costPct: t.cost_pct };
}

/** Controle vóór opslaan; dezelfde regels als de checks in de database. */
export function validate(direction: Direction, entry: number, stop: number, target: number | null): string | null {
  if (!(entry > 0) || !(stop > 0)) return "Vul een geldige instap en stop in.";
  if (direction === "long" && stop >= entry) return "Bij long ligt de stop onder de instap.";
  if (direction === "short" && stop <= entry) return "Bij short ligt de stop boven de instap.";
  if (target !== null) {
    if (!(target > 0)) return "Vul een geldig doel in of laat het leeg.";
    if (direction === "long" && target <= entry) return "Bij long ligt het doel boven de instap.";
    if (direction === "short" && target >= entry) return "Bij short ligt het doel onder de instap.";
  }
  return null;
}

export type Stats = { trades: number; winrate: number | null; avgR: number | null; totalR: number; pnl: number };

/** Samenvatting van gesloten trades. */
export function stats(trades: JournalTrade[]): Stats {
  const closed = trades.filter((t) => t.exit_price !== null);
  const rs = closed.map((t) => rMultiple(levelsOf(t), t.exit_price!)).filter((x): x is number => x !== null);
  const pnl = closed.reduce((s, t) => s + pnlPerUnit(levelsOf(t), t.exit_price!) * t.quantity, 0);
  const totalR = rs.reduce((s, x) => s + x, 0);
  return {
    trades: closed.length,
    winrate: rs.length ? rs.filter((x) => x > 0).length / rs.length : null,
    avgR: rs.length ? totalR / rs.length : null,
    totalR,
    pnl,
  };
}
