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

  return (
    <>
      {!instruments?.length && (
        <p className="text-neutral-500">Nog geen instrumenten. Start de worker (zie README) om data op te halen.</p>
      )}

      <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
        {(instruments as Instrument[] | null)?.map((ins) => (
          <li key={ins.id} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
            <Link href={`/chart/${ins.id}`} className="font-medium hover:underline">
              {ins.symbol}
              {ins.experimental && (
                <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900 dark:bg-amber-900/40 dark:text-amber-200">
                  experimenteel
                </span>
              )}
            </Link>
            <div className="flex flex-col gap-1 sm:items-end">
              {(ins.market === "aex" ? ["1h"] : ["15m", "1h"]).map((iv) => (
                <div key={iv} className="flex items-center gap-2">
                  <span className="w-8 text-xs text-neutral-500">{iv}</span>
                  <FreshnessBadge status={byKey.get(`${ins.id}:${iv}`)} now={now} />
                </div>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 p-4 sm:p-6">
      <header className="mb-6 flex items-baseline justify-between gap-4">
        <h1 className="text-2xl font-semibold">Koersradar</h1>
        <p className="text-xs text-neutral-500">Beslisondersteuning, geen advies. Geen trade is ook een uitkomst.</p>
      </header>
      <Suspense fallback={<p className="text-neutral-500">Laden…</p>}>
        <InstrumentList />
      </Suspense>
    </main>
  );
}
