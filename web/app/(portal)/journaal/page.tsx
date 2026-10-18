import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { JournalForm, type InstrumentOption, type Prefill } from "@/components/JournalForm";
import { TradeActions } from "@/components/TradeActions";
import { fmtNum, fmtPrice, fmtTime } from "@/lib/format";
import { type JournalTrade, levelsOf, pnlPerUnit, rMultiple, stats } from "@/lib/journal";
import { createClient } from "@/lib/supabase/server";
import type { Instrument } from "@/lib/types";

const r = (v: number | null | undefined) => {
  if (v === null || v === undefined) return "–";
  if (Math.abs(v) < 0.005) return "0 R";
  return `${v > 0 ? "+" : ""}${fmtNum(v)} R`;
};
const tone = (v: number | null | undefined) =>
  v === null || v === undefined ? "text-muted" : v > 0 ? "text-up" : v < 0 ? "text-down" : "";
const pct = (v: number | null) =>
  v === null ? "–" : new Intl.NumberFormat("nl-NL", { style: "percent", maximumFractionDigits: 0 }).format(v);

/** Laatste slotkoers per instrument: 15m als die er is, anders 1h (AEX). */
async function latestPrices(supabase: Awaited<ReturnType<typeof createClient>>) {
  const now = Date.now();
  const [{ data: m15 }, { data: h1 }] = await Promise.all([
    supabase
      .from("candles")
      .select("instrument_id, open_time, close")
      .eq("interval", "15m")
      .gte("open_time", new Date(now - 3 * 3600_000).toISOString())
      .order("open_time", { ascending: false }),
    supabase
      .from("candles")
      .select("instrument_id, open_time, close")
      .eq("interval", "1h")
      .gte("open_time", new Date(now - 4 * 86400_000).toISOString())
      .order("open_time", { ascending: false }),
  ]);
  const out = new Map<number, number>();
  for (const c of [...(m15 ?? []), ...(h1 ?? [])]) if (!out.has(c.instrument_id)) out.set(c.instrument_id, c.close);
  return out;
}

function Summary({ title, trades }: { title: string; trades: JournalTrade[] }) {
  const s = stats(trades);
  return (
    <div className="rounded-2xl border border-line bg-panel p-4">
      <p className="truncate text-xs font-medium uppercase tracking-wide text-muted" title={title}>
        {title}
      </p>
      <p className={`num mt-1 text-2xl font-medium ${tone(s.avgR)}`}>{r(s.avgR)}</p>
      <p className="text-xs text-muted">gemiddeld per gesloten trade</p>
      <dl className="num mt-3 grid grid-cols-3 gap-2 text-sm">
        <div>
          <dt className="font-sans text-xs text-muted">Gesloten</dt>
          <dd>{s.trades}</dd>
        </div>
        <div>
          <dt className="font-sans text-xs text-muted">Winrate</dt>
          <dd>{pct(s.winrate)}</dd>
        </div>
        <div>
          <dt className="font-sans text-xs text-muted">Totaal</dt>
          <dd className={tone(s.totalR)}>{r(s.totalR)}</dd>
        </div>
      </dl>
    </div>
  );
}

async function JournalContent(props: PageProps<"/journaal">) {
  await connection();
  const sp = await props.searchParams;
  const signalParam = typeof sp.signal === "string" ? Number(sp.signal) : null;
  const supabase = await createClient();
  const { data: claims } = await supabase.auth.getClaims();
  const me = (claims?.claims?.sub as string | undefined) ?? null;

  const [{ data: instruments }, { data: trades }, { data: profiles }, prices, { data: signal }] = await Promise.all([
    supabase.from("instruments").select("id, symbol, market, source, experimental").eq("active", true).order("market").order("symbol"),
    supabase.from("journal_trades").select("*").order("opened_at", { ascending: false }).limit(500),
    supabase.from("profiles").select("id, display_name"),
    latestPrices(supabase),
    signalParam
      ? supabase
          .from("signals")
          .select("id, instrument_id, direction, entry, stop_loss, target, decision")
          .eq("id", signalParam)
          .maybeSingle()
      : Promise.resolve({ data: null }),
  ]);

  const list = (instruments as Instrument[] | null) ?? [];
  const bySymbol = new Map(list.map((i) => [i.id, i]));
  const names = new Map((profiles ?? []).map((p) => [p.id as string, (p.display_name as string | null) ?? "lid"]));
  const all = (trades as JournalTrade[] | null) ?? [];
  const options: InstrumentOption[] = list.map((i) => ({
    id: i.id,
    symbol: i.symbol,
    currency: i.market === "aex" ? "EUR" : (i.symbol.split("/")[1] ?? ""),
    price: prices.get(i.id) ?? null,
  }));
  const prefill: Prefill | null =
    signal && signal.decision === "TRADE" && signal.entry && signal.stop_loss
      ? {
          instrumentId: signal.instrument_id,
          direction: signal.direction === "short" ? "short" : "long",
          entry: signal.entry,
          stop: signal.stop_loss,
          target: signal.target,
          signalId: signal.id,
        }
      : null;

  const open = all.filter((t) => t.closed_at === null);
  const closed = all.filter((t) => t.closed_at !== null);
  const people = [...new Set(all.map((t) => t.user_id))];

  const symbol = (t: JournalTrade) => bySymbol.get(t.instrument_id)?.symbol ?? "?";
  const who = (t: JournalTrade) => (t.user_id === me ? "jij" : names.get(t.user_id) ?? "lid");

  return (
    <div className="flex flex-col gap-10">
      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Nieuwe paper trade</h2>
        {prefill && <p className="mb-3 text-sm text-muted">Ingevuld vanuit signaal #{prefill.signalId}. Pas gerust aan.</p>}
        {options.length ? (
          <JournalForm key={prefill?.signalId ?? "leeg"} instruments={options} prefill={prefill} />
        ) : (
          <p className="text-muted">Nog geen instrumenten. Start de worker (zie README).</p>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Resultaat na kosten</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Summary title="Hele groep" trades={all} />
          {me && <Summary title="Jij" trades={all.filter((t) => t.user_id === me)} />}
          {people
            .filter((p) => p !== me)
            .map((p) => (
              <Summary key={p} title={names.get(p) ?? "lid"} trades={all.filter((t) => t.user_id === p)} />
            ))}
        </div>
        <p className="mt-2 text-xs text-muted">
          R = resultaat gedeeld door het geplande verlies bij de stop, allebei na kosten. Onder de 30 gesloten trades zegt
          een gemiddelde nog weinig.
        </p>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Open ({open.length})</h2>
        {open.length ? (
          <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-panel">
            {open.map((t) => {
              const price = prices.get(t.instrument_id) ?? null;
              const now = price !== null ? rMultiple(levelsOf(t), price) : null;
              return (
                <li key={t.id} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-center gap-2">
                      <Link href={`/chart/${t.instrument_id}`} className="font-medium hover:underline">
                        {symbol(t)}
                      </Link>
                      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${t.direction === "long" ? "bg-up/15 text-up" : "bg-down/15 text-down"}`}>
                        {t.direction}
                      </span>
                      <span className="text-xs text-muted">
                        {who(t)} · {fmtTime(t.opened_at)}
                      </span>
                    </p>
                    <p className="num mt-1 text-xs text-muted">
                      instap {fmtPrice(t.entry_price)} · stop {fmtPrice(t.stop_loss)}
                      {t.target !== null && <> · doel {fmtPrice(t.target)}</>} · nu {fmtPrice(price)}{" "}
                      <span className={tone(now)}>({r(now)})</span>
                    </p>
                    {t.reason && <p className="mt-1 text-sm">{t.reason}</p>}
                  </div>
                  {t.user_id === me && <TradeActions id={t.id} price={price} open />}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-sm text-muted">Geen open paper trades.</p>
        )}
        <p className="mt-2 text-xs text-muted">
          Je sluit een trade zelf, ook als de stop of het doel is geraakt. Vul dan die koers in.
        </p>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Gesloten ({closed.length})</h2>
        {closed.length ? (
          <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-panel-2 text-left text-xs text-muted">
                <tr>
                  {["Instrument", "Wie", "Open", "Dicht", "Instap", "Uit", "Resultaat", "R", ""].map((h) => (
                    <th key={h} className="px-3 py-2 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="num divide-y divide-line">
                {closed.map((t) => {
                  const rm = rMultiple(levelsOf(t), t.exit_price!);
                  const pnl = pnlPerUnit(levelsOf(t), t.exit_price!) * t.quantity;
                  return (
                    <tr key={t.id} className="align-top hover:bg-panel-2/50">
                      <td className="px-3 py-2 font-sans">
                        <span className="font-medium">{symbol(t)}</span> <span className="text-xs text-muted">{t.direction}</span>
                        {(t.reason || t.exit_note) && (
                          <p className="max-w-64 text-xs text-muted">{[t.reason, t.exit_note].filter(Boolean).join(" · ")}</p>
                        )}
                      </td>
                      <td className="px-3 py-2 font-sans text-muted">{who(t)}</td>
                      <td className="px-3 py-2 text-muted">{fmtTime(t.opened_at)}</td>
                      <td className="px-3 py-2 text-muted">{fmtTime(t.closed_at)}</td>
                      <td className="px-3 py-2">{fmtPrice(t.entry_price)}</td>
                      <td className="px-3 py-2">{fmtPrice(t.exit_price)}</td>
                      <td className={`px-3 py-2 ${tone(pnl)}`}>{`${pnl > 0 ? "+" : ""}${fmtNum(pnl)}`}</td>
                      <td className={`px-3 py-2 ${tone(rm)}`}>{r(rm)}</td>
                      <td className="px-3 py-2">{t.user_id === me && <TradeActions id={t.id} price={null} open={false} />}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted">Nog geen gesloten paper trades.</p>
        )}
      </section>
    </div>
  );
}

export default function JournaalPage(props: PageProps<"/journaal">) {
  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6">
        <h1 className="animate-fade-slide-in-1 font-display text-4xl tracking-tight sm:text-5xl">Journaal</h1>
        <p className="mt-1 text-sm text-muted">
          Paper trading zonder echt geld. Leg je trades vast en zie na kosten of je het beter doet dan toeval.
        </p>
      </header>
      <Suspense fallback={<p className="text-muted">Laden…</p>}>
        <JournalContent {...props} />
      </Suspense>
    </div>
  );
}
