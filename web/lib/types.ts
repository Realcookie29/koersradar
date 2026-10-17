export type Interval = "15m" | "1h";
export const INTERVALS: Interval[] = ["15m", "1h"];

export type DataStatus = {
  instrument_id: number;
  interval: Interval;
  source: string;
  last_candle_at: string | null;
  last_checked_at: string;
  status: "ok" | "delayed" | "stale" | "gap" | "error";
  detail: string | null;
};

export type Instrument = {
  id: number;
  symbol: string;
  market: "crypto" | "aex";
  source: string;
  experimental: boolean;
};

export type Candle = {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type Fact = { name: string; value: number; note?: string | null };

export type SignalRow = {
  id: number;
  instrument_id: number;
  symbol: string;
  market: "crypto" | "aex";
  experimental: boolean;
  interval: Interval;
  decision: "TRADE" | "NO_TRADE";
  direction: "long" | "short" | null;
  entry: number | null;
  invalidation: string | null;
  stop_loss: number | null;
  target: number | null;
  rr_ratio: number | null;
  strength: "zwak" | "matig" | "sterk" | null;
  facts: Fact[];
  assumptions: string[];
  no_trade_reason: string | null;
  data_source: string;
  last_candle_at: string;
  data_delay_s: number;
  strategy_version: string;
  created_at: string;
  explanation: string | null;
  explanation_status: "ok" | "rejected" | "skipped" | "error" | null;
};

export type ScanRun = {
  id: number;
  trigger: "schedule" | "manual";
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  status: "pending" | "running" | "done" | "error";
  instruments_scanned: number | null;
  trade_count: number | null;
  error: string | null;
};
