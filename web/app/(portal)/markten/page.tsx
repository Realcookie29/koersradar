import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { createClient } from "@/lib/supabase/server";
import type { DataStatus, Instrument } from "@/lib/types";

async function InstrumentList() {
  // Request-time rendering: Supabase-auth en de data-leeftijd gebruiken de klok.
  await connection();
  const supabase = await createClient();
  const [{ data: instruments }, { data: statuses }] = await Promise.all([
    supabase.from("instruments").select("id, symbol, market, source, experimental").eq("active", true).order("market").order("symbol"),
    supabase.from("data_status").select("*"),
  ]);
  const byKey = new Map((statuses as DataStatus[] | null)?.map((s) => [`${s.instrument_id}:${s.interval}`, s]));
  const now = new Date().getTime();
  const groups = [
    { key: "crypto", title: "Crypto" },
    { key: "aex", title: "AEX (experimenteel)" },
  ] as const;

  return (
    <div className="flex flex-col gap-8">
      {groups.map((g) => {
        const list = (instruments as Instrument[] | null)?.filter((i) => i.market === g.key) ?? [];
        if (!list.length) return null;
        return (
          <section key={g.key}>
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">{g.title}</h2>
            <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-panel">
              {list.map((ins) => (
                <li key={ins.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <Link href={`/chart/${ins.id}`} className="font-medium hover:underline">
                    {ins.symbol}
                  </Link>
                  <div className="flex flex-col gap-1 sm:items-end">
                    {(ins.market === "aex" ? ["1h"] : ["15m", "1h"]).map((iv) => (
                      <div key={iv} className="flex items-center gap-2">
                        <Link href={`/chart/${ins.id}?iv=${iv}`} className="w-8 text-xs text-muted hover:text-text">
                          {iv}
                        </Link>
                        <FreshnessBadge status={byKey.get(`${ins.id}:${iv}`)} now={now} />
                      </div>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {!instruments?.length && <p className="text-muted">Nog geen instrumenten. Start de worker (zie README).</p>}
    </div>
  );
}

export default function MarktenPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6">
        <h1 className="animate-fade-slide-in-1 font-display text-4xl tracking-tight sm:text-5xl">Markten</h1>
        <p className="mt-1 text-sm text-muted">Databron, laatste candle en versheid per instrument.</p>
      </header>
      <Suspense fallback={<p className="text-muted">Laden…</p>}>
        <InstrumentList />
      </Suspense>
    </div>
  );
}
