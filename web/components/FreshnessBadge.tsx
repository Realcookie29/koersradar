import type { DataStatus } from "@/lib/types";

const LABEL: Record<DataStatus["status"], string> = {
  ok: "actueel",
  delayed: "vertraagd",
  stale: "verouderd",
  gap: "gaten in data",
  error: "fout",
};

const COLOR: Record<DataStatus["status"], string> = {
  ok: "bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-200",
  delayed: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200",
  stale: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200",
  gap: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200",
  error: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200",
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
      <span className="text-neutral-500">
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
