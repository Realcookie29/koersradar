import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Suspense } from "react";
import { Chart } from "@/components/Chart";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { SignalCard } from "@/components/SignalCard";
import { isCurrent } from "@/components/signals";
import { createClient } from "@/lib/supabase/server";
import { INTERVALS, type Candle, type DataStatus, type Interval, type SignalRow } from "@/lib/types";

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

  const [{ data: rows }, { data: status }, { data: sig }] = await Promise.all([
    supabase
      .from("candles")
      .select("open_time, open, high, low, close, volume")
      .eq("instrument_id", ins.id)
      .eq("interval", interval)
      .order("open_time", { ascending: false })
      .limit(MAX_CANDLES),
    supabase.from("data_status").select("*").eq("instrument_id", ins.id).eq("interval", interval).maybeSingle(),
    supabase.from("latest_signals").select("*").eq("instrument_id", ins.id).eq("interval", interval).maybeSingle(),
  ]);
  const candles = ((rows as Candle[] | null) ?? []).reverse();
  const now = new Date().getTime();
  const signal = sig as SignalRow | null;
  const activeTrade = signal?.decision === "TRADE" && isCurrent(signal, now) ? signal : null;

  return (
    <>
      <div className="mt-2 mb-3 flex flex-wrap items-center justify-between gap-3">
        <h1 className="animate-fade-slide-in-1 font-display text-4xl tracking-tight sm:text-5xl">{ins.symbol}</h1>
        <nav className="flex gap-1 rounded-full border border-line bg-panel p-1">
          {INTERVALS.map((iv) => (
            <Link
              key={iv}
              href={`/chart/${ins.id}?iv=${iv}`}
              className={`rounded-full px-3.5 py-1 text-sm font-medium ${iv === interval ? "bg-panel-2 text-text" : "text-muted hover:text-text"}`}
            >
              {iv}
            </Link>
          ))}
        </nav>
      </div>
      <FreshnessBadge status={status as DataStatus | undefined} now={now} />
      {ins.experimental && (
        <p className="mt-2 text-xs text-warn">
          Experimentele bron (onofficieel, mogelijk vertraagd of onvolledig). Signalen alleen ter informatie.
        </p>
      )}
      <div className="mt-4 rounded-2xl border border-line bg-panel p-2">
        {candles.length ? (
          <Chart
            candles={candles}
            levels={activeTrade ? { entry: activeTrade.entry!, stop: activeTrade.stop_loss!, target: activeTrade.target! } : null}
          />
        ) : (
          <p className="p-6 text-muted">Geen candles voor dit interval.</p>
        )}
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {activeTrade ? (
          <SignalCard s={activeTrade} />
        ) : (
          <div className="rounded-2xl border border-line bg-panel p-4 text-sm">
            <h2 className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">Laatste beoordeling</h2>
            <p>{signal ? (signal.no_trade_reason ?? "Kans verlopen") : "Nog niet gescand."}</p>
          </div>
        )}
      </div>
      <p className="mt-3 text-xs text-muted">
        EMA/RSI in de grafiek zijn alleen weergave; signalen komen uit de worker (gecontroleerde Python-code).
      </p>
    </>
  );
}

export default function ChartPage(props: PageProps<"/chart/[id]">) {
  return (
    <div className="mx-auto max-w-6xl">
      <Link href="/" className="text-sm text-muted hover:text-text">← scanner</Link>
      <Suspense fallback={<p className="mt-4 text-muted">Laden…</p>}>
        <ChartContent {...props} />
      </Suspense>
    </div>
  );
}
