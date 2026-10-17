import type { DataStatus } from "@/lib/types";

const LABEL: Record<DataStatus["status"], string> = {
  ok: "actueel",
  delayed: "vertraagd",
  stale: "verouderd",
  gap: "gaten in data",
  error: "fout",
};

const COLOR: Record<DataStatus["status"], string> = {
  ok: "bg-up/15 text-up",
  delayed: "bg-warn/15 text-warn",
  stale: "bg-down/15 text-down",
  gap: "bg-down/15 text-down",
  error: "bg-down/15 text-down",
};

function fmtAge(ms: number): string {
  const min = Math.round(ms / 60_000);
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  return h < 48 ? `${h} u ${min % 60} min` : `${Math.floor(h / 24)} dagen`;
}

// Altijd zichtbaar naast koersdata: bron, laatste candle en vertraging.
export function FreshnessBadge({ status, now }: { status?: DataStatus; now: number }) {
  if (!status) {
    return <span className={`rounded px-2 py-0.5 text-xs ${COLOR.error}`}>nog geen data</span>;
  }
  const last = status.last_candle_at ? new Date(status.last_candle_at) : null;
  return (
    <span className="inline-flex flex-wrap items-center gap-2 text-xs">
      <span className={`rounded px-2 py-0.5 font-medium ${COLOR[status.status]}`}>
        {LABEL[status.status]}
      </span>
      <span className="text-muted">
        bron {status.source}
        {last && (
          <>
            {" · "}laatste candle {last.toLocaleString("nl-NL", { timeZone: "Europe/Amsterdam" })}
            {" · "}leeftijd {fmtAge(now - last.getTime())}
          </>
        )}
        {status.detail && <> · {status.detail}</>}
      </span>
    </span>
  );
}
