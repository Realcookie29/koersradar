import Link from "next/link";
import { connection } from "next/server";
import { fmtPct, fmtPrice } from "@/lib/format";
import { BARS_NEEDED, type Bar, overview, rankBy7d } from "@/lib/market";
import { createClient } from "@/lib/supabase/server";
import type { Instrument } from "@/lib/types";

const tone = (v: number | null) => (v === null ? "text-muted" : v > 0 ? "text-up" : v < 0 ? "text-down" : "");
const change = (v: number | null) => (v === null ? "–" : fmtPct(v));

function Band({ pos }: { pos: number | null }) {
  if (pos === null) return <span className="text-muted">–</span>;
  return (
    <span className="flex items-center gap-2" title={`${Math.round(pos * 100)}% van laag naar hoog`}>
      <span className="relative h-1.5 w-20 rounded-full bg-panel-2">
        <span className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-text" style={{ left: `${pos * 100}%` }} />
      </span>
    </span>
  );
}

function Tag({ children, tone }: { children: React.ReactNode; tone: "up" | "warn" | "muted" }) {
  const cls = { up: "bg-up/15 text-up", warn: "bg-warn/15 text-warn", muted: "bg-panel-2 text-muted" }[tone];
  return <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${cls}`}>{children}</span>;
}

export async function MarketOverview() {
  // Request-time rendering: Supabase-auth en de koersen veranderen per kwartier.
  await connection();
  const supabase = await createClient();
  const { data: instruments } = await supabase
    .from("instruments")
    .select("id, symbol, market, source, experimental")
    .eq("active", true)
    .order("symbol");
  const list = (instruments as Instrument[] | null) ?? [];
  const rows = await Promise.all(
    list.map(async (ins) => {
      const { data } = await supabase
        .from("candles")
        .select("open_time, high, low, close")
        .eq("instrument_id", ins.id)
        .eq("interval", "1h")
        .order("open_time", { ascending: false })
        .limit(BARS_NEEDED + 20);
      const bars = ((data as Bar[] | null) ?? []).reverse();
      return { ins, o: overview(bars), last: bars.at(-1)?.open_time ?? null };
    }),
  );
  const ranked = rankBy7d(
    rows.filter((r) => r.o).map((r) => ({ ...r, change7d: r.o!.change7d })),
  ).sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));

  if (!ranked.length) {
    return <p className="text-sm text-muted">Nog geen koersdata. Die verschijnt zodra de worker draait.</p>;
  }

  const crypto = ranked.filter((r) => r.ins.market === "crypto" && r.rank !== null);
  const strongest = crypto.slice(0, 3);
  const breaking = ranked.filter((r) => r.o!.breakout20d || r.o!.breakout24h);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-line bg-panel p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Sterkst deze week</p>
          <ul className="mt-2 flex flex-col gap-1 text-sm">
            {strongest.map((r) => (
              <li key={r.ins.id} className="flex justify-between">
                <Link href={`/chart/${r.ins.id}?iv=1h`} className="font-medium hover:underline">
                  {r.ins.symbol}
                </Link>
                <span className={`num ${tone(r.change7d)}`}>{change(r.change7d)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-line bg-panel p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">Breekt nu uit</p>
          {breaking.length ? (
            <ul className="mt-2 flex flex-col gap-1 text-sm">
              {breaking.map((r) => (
                <li key={r.ins.id} className="flex items-center justify-between gap-2">
                  <Link href={`/chart/${r.ins.id}?iv=1h`} className="font-medium hover:underline">
                    {r.ins.symbol}
                  </Link>
                  {r.o!.breakout20d ? <Tag tone="up">boven 20-daagse high</Tag> : <Tag tone="warn">boven high van 24 uur</Tag>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted">Op dit moment breekt niets uit.</p>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-panel-2 text-left text-xs text-muted">
            <tr>
              {["#", "Instrument", "Koers", "24 uur", "7 dagen", "20 dagen: laag → hoog", "Trend (1h)", ""].map((h) => (
                <th key={h} className="px-3 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="num divide-y divide-line">
            {ranked.map(({ ins, o, rank }) => (
              <tr key={ins.id} className="hover:bg-panel-2/50">
                <td className="px-3 py-2 text-muted">{rank ?? "–"}</td>
                <td className="px-3 py-2 font-sans">
                  <Link href={`/chart/${ins.id}?iv=1h`} className="font-medium hover:underline">
                    {ins.symbol}
                  </Link>
                  {ins.experimental && <span className="ml-1 text-[11px] text-muted">experimenteel</span>}
                </td>
                <td className="px-3 py-2">{fmtPrice(o!.close)}</td>
                <td className={`px-3 py-2 ${tone(o!.change24h)}`}>{change(o!.change24h)}</td>
                <td className={`px-3 py-2 ${tone(o!.change7d)}`}>{change(o!.change7d)}</td>
                <td className="px-3 py-2">
                  <Band pos={o!.rangePos20d} />
                </td>
                <td className="px-3 py-2 font-sans">
                  {o!.trendUp === null ? (
                    <span className="text-muted">–</span>
                  ) : o!.trendUp ? (
                    <Tag tone="up">stijgend</Tag>
                  ) : (
                    <Tag tone="muted">dalend</Tag>
                  )}
                </td>
                <td className="px-3 py-2 font-sans">
                  {o!.breakout20d ? <Tag tone="up">20-daagse high</Tag> : o!.breakout24h ? <Tag tone="warn">24-uurs high</Tag> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted">
        Op basis van gesloten 1h-candles. Dit is informatie, geen koopadvies: in onze backtests leverde geen van deze
        kenmerken op zichzelf winst op na kosten, ook breakouts niet. Rang = sterkste over 7 dagen.
      </p>
    </div>
  );
}
