import Link from "next/link";
import { fmtNum, fmtPct, fmtPrice, fmtTime } from "@/lib/format";
import type { SignalRow } from "@/lib/types";

const STRENGTH = {
  sterk: "bg-up/15 text-up",
  matig: "bg-warn/15 text-warn",
  zwak: "bg-muted/15 text-muted",
} as const;

function Level({ label, value, entry, tone }: { label: string; value: number; entry: number; tone?: string }) {
  const diff = (value - entry) / entry;
  return (
    <div className="rounded-lg bg-panel-2 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`num text-sm font-medium ${tone ?? ""}`}>{fmtPrice(value)}</div>
      {label !== "Instap" && <div className={`num text-[11px] ${tone ?? "text-muted"}`}>{fmtPct(diff)}</div>}
    </div>
  );
}

export function SignalCard({ s }: { s: SignalRow }) {
  if (s.entry === null || s.stop_loss === null || s.target === null) return null;
  return (
    <article className="flex flex-col gap-4 rounded-xl border border-line bg-panel p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Link href={`/chart/${s.instrument_id}?iv=${s.interval}`} className="text-lg font-semibold hover:underline">
            {s.symbol}
          </Link>
          <span className="rounded bg-panel-2 px-1.5 py-0.5 text-xs text-muted">{s.interval}</span>
          <span className="rounded bg-up/15 px-1.5 py-0.5 text-xs font-medium text-up">KOOP · long</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {s.strength && <span className={`rounded px-1.5 py-0.5 font-medium ${STRENGTH[s.strength]}`}>{s.strength}</span>}
          <span className="num rounded bg-panel-2 px-1.5 py-0.5">R/R {fmtNum(s.rr_ratio)}</span>
        </div>
      </header>

      <div className="grid grid-cols-3 gap-2">
        <Level label="Stop" value={s.stop_loss} entry={s.entry} tone="text-down" />
        <Level label="Instap" value={s.entry} entry={s.entry} />
        <Level label="Doel" value={s.target} entry={s.entry} tone="text-up" />
      </div>

      <section className="text-sm">
        <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">AI-uitleg</h3>
        {s.explanation_status === "ok" && s.explanation ? (
          <p className="whitespace-pre-line leading-relaxed">{s.explanation}</p>
        ) : (
          <p className="text-muted">
            {s.explanation_status === "rejected"
              ? "Uitleg afgewezen door de getallencontrole; zie de feiten hieronder."
              : "Nog geen AI-uitleg (API-key niet ingesteld of tijdelijk niet bereikbaar)."}
          </p>
        )}
      </section>

      <details className="text-sm">
        <summary className="cursor-pointer text-xs font-medium uppercase tracking-wide text-muted">
          Feiten, aannames en ongeldigverklaring
        </summary>
        <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
          {s.facts.map((f) => (
            <div key={f.name} className="contents">
              <dt className="text-muted">{f.name}</dt>
              <dd className="num text-right">{fmtNum(f.value, Math.abs(f.value) >= 1000 ? 0 : 2)}</dd>
            </div>
          ))}
        </dl>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-muted">
          {s.assumptions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
        <p className="mt-3">
          <span className="text-muted">Ongeldig als: </span>
          {s.invalidation}
        </p>
      </details>

      <footer className="flex flex-wrap justify-between gap-2 border-t border-line pt-3 text-[11px] text-muted">
        <span>
          Candle {fmtTime(s.last_candle_at)} · bron {s.data_source} · {s.strategy_version}
        </span>
        <span className="text-warn">Ongetest: nog geen backtest</span>
      </footer>
    </article>
  );
}
