const nl = (opts: Intl.NumberFormatOptions) => new Intl.NumberFormat("nl-NL", opts);

/** Koers met zinvolle precisie: BTC 2 decimalen, DOGE meer. */
export function fmtPrice(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const abs = Math.abs(v);
  const digits = abs >= 1000 ? 2 : abs >= 1 ? 4 : 6;
  return nl({ minimumFractionDigits: Math.min(2, digits), maximumFractionDigits: digits }).format(v);
}

export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return nl({ maximumFractionDigits: digits }).format(v);
}

export function fmtPct(fraction: number): string {
  return nl({ style: "percent", maximumFractionDigits: 2, signDisplay: "always" }).format(fraction);
}

export function fmtCompact(v: number): string {
  return nl({ notation: "compact", maximumFractionDigits: 1 }).format(v);
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleString("nl-NL", {
    timeZone: "Europe/Amsterdam",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtAge(ms: number): string {
  const min = Math.max(0, Math.round(ms / 60_000));
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  return h < 48 ? `${h} u ${min % 60} m` : `${Math.floor(h / 24)} dagen`;
}
