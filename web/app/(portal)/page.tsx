import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { ScanButton } from "@/components/ScanButton";
import { SignalCard } from "@/components/SignalCard";
import { STEPS, isCurrent, stepsPassed } from "@/components/signals";
import { fmtAge, fmtTime } from "@/lib/format";
import { createClient } from "@/lib/supabase/server";
import type { ScanRun, SignalRow } from "@/lib/types";

function Progress({ s }: { s: SignalRow }) {
  const passed = stepsPassed(s);
  return (
    <div className="flex items-center gap-1" title={STEPS.map((st, i) => `${i < passed ? "✓" : "✗"} ${st}`).join("\n")}>
      {STEPS.map((st, i) => (
        <span
          key={st}
          className={`h-1.5 w-4 rounded-full ${i < passed ? (passed === STEPS.length ? "bg-up" : "bg-accent") : "bg-line"}`}
        />
      ))}
    </div>
  );
}

async function Scanner() {
  await connection();
  const supabase = await createClient();
  const [{ data: latest }, { data: runs }] = await Promise.all([
    supabase.from("latest_signals").select("*").order("symbol"),
    supabase.from("scan_runs").select("*").order("requested_at", { ascending: false }).limit(1),
  ]);
  const signals = (latest as SignalRow[] | null) ?? [];
  const run = (runs as ScanRun[] | null)?.[0];
  const now = new Date().getTime();
  const busy = run?.status === "pending" || run?.status === "running";

  const opportunities = signals.filter((s) => s.decision === "TRADE" && isCurrent(s, now));
  const strengthRank = { sterk: 0, matig: 1, zwak: 2 };
  opportunities.sort((a, b) => strengthRank[a.strength ?? "zwak"] - strengthRank[b.strength ?? "zwak"] || (b.rr_ratio ?? 0) - (a.rr_ratio ?? 0));

  const radar = [...signals].sort((a, b) => stepsPassed(b) - stepsPassed(a) || a.symbol.localeCompare(b.symbol));
  const lastDone = run?.finished_at ?? run?.requested_at;

  return (
    <>
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Daytrade-scanner</h1>
          <p className="mt-1 text-sm text-muted">
            Zoekt elke 15 minuten naar pullbacks in een opwaartse trend (alleen kopen).{" "}
            {lastDone && (
              <>
                Laatste scan {fmtTime(lastDone)} ({fmtAge(now - new Date(lastDone).getTime())} geleden)
                {run?.status === "error" && <span className="text-down"> · mislukt</span>}.
              </>
            )}
          </p>
        </div>
        <ScanButton busy={busy} />
      </header>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">
          Koopkansen nu <span className="num">({opportunities.length})</span>
        </h2>
        {opportunities.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {opportunities.map((s) => (
              <SignalCard key={s.id} s={s} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-line bg-panel px-5 py-8 text-center">
            <p className="font-medium">Op dit moment geen koopkansen</p>
            <p className="mx-auto mt-1 max-w-xl text-sm text-muted">
              Geen enkel instrument voldoet aan alle regels. Dat is een geldige uitkomst: niet traden is beter dan
              een zwak signaal volgen. Hieronder zie je per instrument hoe dicht het erbij zit.
            </p>
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <h2 className="text-sm font-medium uppercase tracking-wide text-muted">Radar</h2>
          <p className="text-xs text-muted">{STEPS.join(" → ")}</p>
        </div>
        <div className="overflow-hidden rounded-xl border border-line bg-panel">
          <table className="w-full text-sm">
            <thead className="bg-panel-2 text-left text-xs text-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Instrument</th>
                <th className="px-2 py-2 font-medium">Interval</th>
                <th className="px-2 py-2 font-medium">Regels gehaald</th>
                <th className="hidden px-4 py-2 font-medium sm:table-cell">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {radar.map((s) => (
                <tr key={`${s.instrument_id}-${s.interval}`} className="hover:bg-panel-2/50">
                  <td className="px-4 py-2.5">
                    <Link href={`/chart/${s.instrument_id}?iv=${s.interval}`} className="font-medium hover:underline">
                      {s.symbol}
                    </Link>
                    {s.experimental && <span className="ml-2 text-[11px] text-warn">experimenteel</span>}
                  </td>
                  <td className="px-2 py-2.5 text-muted">{s.interval}</td>
                  <td className="px-2 py-2.5">
                    <Progress s={s} />
                  </td>
                  <td className="hidden px-4 py-2.5 text-muted sm:table-cell">
                    {s.decision === "TRADE" ? <span className="text-up">koopkans</span> : s.no_trade_reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!radar.length && <p className="px-4 py-6 text-sm text-muted">Nog geen scan gedraaid. Klik op ‘Scan nu’.</p>}
        </div>
      </section>
    </>
  );
}

export default function ScannerPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <Suspense fallback={<p className="text-muted">Laden…</p>}>
        <Scanner />
      </Suspense>
      <p className="mt-10 text-xs leading-relaxed text-muted">
        Koersradar is beslisondersteuning voor eigen gebruik, geen beleggingsadvies. Signalen zijn berekend door
        regels die nog niet gebacktest zijn; de AI vat alleen samen. Er worden geen orders geplaatst.
      </p>
    </div>
  );
}
