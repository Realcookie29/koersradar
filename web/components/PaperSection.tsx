import Link from "next/link";
import { fmtNum, fmtPrice, fmtTime } from "@/lib/format";
import { DEFAULT_COST_PCT, rMultiple } from "@/lib/journal";

/** Zelfde startvermogen als worker/koersradar/paper/ledger.py. */
export const PAPER_START = 10_000;

export type PaperTrade = {
  id: number;
  opened_at: string;
  entry_price: number;
  size: number;
  closed_at: string | null;
  exit_price: number | null;
  exit_reason: "stop" | "target" | "invalidated" | "manual" | "timeout" | null;
  pnl_after_costs: number | null;
  r_multiple: number | null;
  signals: { instrument_id: number; interval: string; stop_loss: number; target: number } | null;
};

const REASON = { stop: "stop", target: "doel", invalidated: "trend gebroken", manual: "handmatig", timeout: "tijd" } as const;

const r = (v: number | null | undefined) => {
  if (v === null || v === undefined) return "–";
  if (Math.abs(v) < 0.005) return "0 R";
  return `${v > 0 ? "+" : ""}${fmtNum(v)} R`;
};
const tone = (v: number | null | undefined) =>
  v === null || v === undefined ? "text-muted" : v > 0 ? "text-up" : v < 0 ? "text-down" : "";

export function PaperSection({
  trades,
  skipped,
  symbols,
  prices,
}: {
  trades: PaperTrade[];
  skipped: number;
  symbols: Map<number, string>;
  prices: Map<number, number>;
}) {
  const open = trades.filter((t) => t.closed_at === null);
  const closed = trades.filter((t) => t.closed_at !== null);
  const rs = closed.map((t) => t.r_multiple ?? 0);
  const pnl = closed.reduce((s, t) => s + (t.pnl_after_costs ?? 0), 0);
  const avgR = rs.length ? rs.reduce((s, x) => s + x, 0) / rs.length : null;
  const winrate = rs.length ? rs.filter((x) => x > 0).length / rs.length : null;
  const sym = (t: PaperTrade) => (t.signals ? symbols.get(t.signals.instrument_id) ?? "?" : "?");

  return (
    <section>
      <h2 className="mb-1 text-sm font-medium uppercase tracking-wide text-muted">Scanner, automatisch</h2>
      <p className="mb-3 text-sm text-muted">
        De worker voert elk koopsignaal van de scanner met nepgeld uit, met dezelfde regels als de backtest: 1% risico
        per trade, maximaal 5 posities, en geen nieuwe trades na 3% dagverlies. Zo testen we de regels vanaf nu vooruit.
      </p>
      <div className="grid grid-cols-2 gap-3 rounded-2xl border border-line bg-panel p-4 sm:grid-cols-5">
        {[
          { label: "Vermogen", value: `${fmtNum(PAPER_START + pnl, 0)}`, cls: tone(pnl) },
          { label: "Gem. per trade", value: r(avgR), cls: tone(avgR) },
          { label: "Gesloten", value: String(closed.length) },
          {
            label: "Winrate",
            value:
              winrate === null
                ? "–"
                : new Intl.NumberFormat("nl-NL", { style: "percent", maximumFractionDigits: 0 }).format(winrate),
          },
          { label: "Overgeslagen", value: String(skipped) },
        ].map((x) => (
          <div key={x.label}>
            <p className="text-xs text-muted">{x.label}</p>
            <p className={`num text-lg font-medium ${x.cls ?? ""}`}>{x.value}</p>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">
        Start met {fmtNum(PAPER_START, 0)} USDT nepgeld. Resultaten na kosten. Onder de 30 gesloten trades zegt dit nog
        weinig.
      </p>

      {open.length > 0 && (
        <ul className="mt-4 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-panel">
          {open.map((t) => {
            const s = t.signals;
            const price = s ? prices.get(s.instrument_id) ?? null : null;
            const now =
              s && price !== null
                ? rMultiple({ direction: "long", entry: t.entry_price, stop: s.stop_loss, costPct: DEFAULT_COST_PCT }, price)
                : null;
            return (
              <li key={t.id} className="num flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <span className="font-sans">
                  {s ? (
                    <Link href={`/chart/${s.instrument_id}?iv=${s.interval}`} className="font-medium hover:underline">
                      {sym(t)}
                    </Link>
                  ) : (
                    sym(t)
                  )}{" "}
                  <span className="text-xs text-muted">
                    {s?.interval} · open sinds {fmtTime(t.opened_at)}
                  </span>
                </span>
                <span className="text-xs text-muted">
                  instap {fmtPrice(t.entry_price)} · stop {fmtPrice(s?.stop_loss)} · doel {fmtPrice(s?.target)} · nu{" "}
                  {fmtPrice(price)} <span className={tone(now)}>({r(now)})</span>
                </span>
              </li>
            );
          })}
        </ul>
      )}

      {closed.length > 0 && (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-line bg-panel">
          <table className="w-full min-w-[680px] text-sm">
            <thead className="bg-panel-2 text-left text-xs text-muted">
              <tr>
                {["Instrument", "Open", "Dicht", "Instap", "Uit", "Reden", "R", "Resultaat"].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="num divide-y divide-line">
              {closed.slice(0, 30).map((t) => (
                <tr key={t.id} className="hover:bg-panel-2/50">
                  <td className="px-3 py-2 font-sans">
                    <span className="font-medium">{sym(t)}</span> <span className="text-xs text-muted">{t.signals?.interval}</span>
                  </td>
                  <td className="px-3 py-2 text-muted">{fmtTime(t.opened_at)}</td>
                  <td className="px-3 py-2 text-muted">{fmtTime(t.closed_at)}</td>
                  <td className="px-3 py-2">{fmtPrice(t.entry_price)}</td>
                  <td className="px-3 py-2">{fmtPrice(t.exit_price)}</td>
                  <td className="px-3 py-2 font-sans text-muted">{t.exit_reason ? REASON[t.exit_reason] : "–"}</td>
                  <td className={`px-3 py-2 ${tone(t.r_multiple)}`}>{r(t.r_multiple)}</td>
                  <td className={`px-3 py-2 ${tone(t.pnl_after_costs)}`}>
                    {t.pnl_after_costs === null ? "–" : `${t.pnl_after_costs > 0 ? "+" : ""}${fmtNum(t.pnl_after_costs)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!trades.length && <p className="mt-4 text-sm text-muted">Nog geen automatische paper trades. Die komen bij het eerstvolgende koopsignaal.</p>}
    </section>
  );
}
