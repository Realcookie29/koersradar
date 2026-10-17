import Link from "next/link";
import { connection } from "next/server";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Chart } from "@/components/Chart";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { createClient } from "@/lib/supabase/server";
import { INTERVALS, type Candle, type DataStatus, type Interval } from "@/lib/types";

const MAX_CANDLES = 1000;

async function ChartContent(props: PageProps<"/chart/[id]">) {
  // Request-time rendering: Supabase-auth en de data-leeftijd gebruiken de klok.
  await connection();
  const { id } = await props.params;
  const sp = await props.searchParams;
  const interval: Interval = INTERVALS.includes(sp.iv as Interval) ? (sp.iv as Interval) : "1h";

  const supabase = await createClient();
  const { data: ins } = await supabase.from("instruments").select("id, symbol, experimental").eq("id", id).maybeSingle();
  if (!ins) notFound();

  const [{ data: rows }, { data: status }] = await Promise.all([
    supabase
      .from("candles")
      .select("open_time, open, high, low, close, volume")
      .eq("instrument_id", ins.id)
      .eq("interval", interval)
      .order("open_time", { ascending: false })
      .limit(MAX_CANDLES),
    supabase.from("data_status").select("*").eq("instrument_id", ins.id).eq("interval", interval).maybeSingle(),
  ]);
  const candles = ((rows as Candle[] | null) ?? []).reverse();
  const now = new Date().getTime();

  return (
    <>
      <div className="mt-2 mb-3 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{ins.symbol}</h1>
        <nav className="flex gap-1">
          {INTERVALS.map((iv) => (
            <Link
              key={iv}
              href={`/chart/${ins.id}?iv=${iv}`}
              className={`rounded px-3 py-1 text-sm ${iv === interval ? "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900" : "border border-neutral-300 dark:border-neutral-700"}`}
            >
              {iv}
            </Link>
          ))}
        </nav>
      </div>
      <FreshnessBadge status={status as DataStatus | undefined} now={now} />
      {ins.experimental && (
        <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
          Experimentele bron (onofficieel, mogelijk vertraagd of onvolledig). Signalen alleen ter informatie.
        </p>
      )}
      <div className="mt-4">
        {candles.length ? <Chart candles={candles} /> : <p className="text-neutral-500">Geen candles voor dit interval.</p>}
      </div>
      <p className="mt-2 text-xs text-neutral-500">
        EMA/RSI hier zijn alleen weergave. Signalen komen uit de worker en staan los van deze grafiek.
      </p>
    </>
  );
}

export default function ChartPage(props: PageProps<"/chart/[id]">) {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6">
      <Link href="/" className="text-sm text-neutral-500 hover:underline">← overzicht</Link>
      <Suspense fallback={<p className="mt-4 text-neutral-500">Laden…</p>}>
        <ChartContent {...props} />
      </Suspense>
    </main>
  );
}
