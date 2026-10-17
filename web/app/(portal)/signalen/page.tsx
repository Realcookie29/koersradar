import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { fmtNum, fmtPrice, fmtTime } from "@/lib/format";
import { createClient } from "@/lib/supabase/server";

type Row = {
  id: number;
  instrument_id: number;
  interval: string;
  strength: string | null;
  entry: number;
  stop_loss: number;
  target: number;
  rr_ratio: number;
  last_candle_at: string;
  strategy_version: string;
  explanation_status: string | null;
  instruments: { symbol: string } | null;
};

async function Log() {
  await connection();
  const supabase = await createClient();
  const { data } = await supabase
    .from("signals")
    .select("id, instrument_id, interval, strength, entry, stop_loss, target, rr_ratio, last_candle_at, strategy_version, explanation_status, instruments(symbol)")
    .eq("decision", "TRADE")
    .order("last_candle_at", { ascending: false })
    .limit(200);
  const rows = (data as unknown as Row[] | null) ?? [];

  if (!rows.length) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-panel px-5 py-8 text-center text-sm text-muted">
        Nog geen koopsignalen gelogd. Elke kans die de scanner vindt komt hier, zodat we achteraf kunnen beoordelen
        wat werkte.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-panel">
      <table className="w-full min-w-[720px] text-sm">
        <thead className="bg-panel-2 text-left text-xs text-muted">
          <tr>
            {["Candle", "Instrument", "Int.", "Sterkte", "Instap", "Stop", "Doel", "R/R", "Uitleg"].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="num divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.id} className="hover:bg-panel-2/50">
              <td className="px-3 py-2 text-muted">{fmtTime(r.last_candle_at)}</td>
              <td className="px-3 py-2 font-sans font-medium">
                <Link href={`/chart/${r.instrument_id}?iv=${r.interval}`} className="hover:underline">{r.instruments?.symbol}</Link>
              </td>
              <td className="px-3 py-2 text-muted">{r.interval}</td>
              <td className="px-3 py-2 font-sans">{r.strength}</td>
              <td className="px-3 py-2">{fmtPrice(r.entry)}</td>
              <td className="px-3 py-2 text-down">{fmtPrice(r.stop_loss)}</td>
              <td className="px-3 py-2 text-up">{fmtPrice(r.target)}</td>
              <td className="px-3 py-2">{fmtNum(r.rr_ratio)}</td>
              <td className="px-3 py-2 font-sans text-muted">{r.explanation_status ?? "–"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SignalenPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Signalenlog</h1>
        <p className="mt-1 text-sm text-muted">
          Alle koopsignalen met hun niveaus. Uitkomsten (geraakt doel of stop) volgen met paper trading in fase 4.
        </p>
      </header>
      <Suspense fallback={<p className="text-muted">Laden…</p>}>
        <Log />
      </Suspense>
    </div>
  );
}
