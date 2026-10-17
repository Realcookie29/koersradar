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
