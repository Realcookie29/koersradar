import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { fmtNum } from "@/lib/format";
import { createClient } from "@/lib/supabase/server";
import { INTERVALS, type Interval } from "@/lib/types";

type Metrics = {
  trades: number;
  winrate: number | null;
  avg_r: number | null;
  profit_factor: number | null;
  return_pct: number;
  max_drawdown_pct: number;
  exposure: number;
  beats_random_share?: number | null;
};

type Benchmarks = {
  buy_and_hold: { return_pct: number; max_drawdown_pct: number };
  random_entry?: { runs: number; avg_r_median: number; avg_r_p5: number; avg_r_p95: number } | null;
};

type Run = {
  id: number;
  strategy_version: string;
  interval: Interval;
  params: { risk_frac?: number; costs?: { taker_fee: number; spread: number; checked_on: string | null } };
  period_kind: "train" | "test" | "walk_forward" | "holdout";
  period_start: string;
  period_end: string;
  metrics: Metrics;
  benchmarks: Benchmarks;
  created_at: string;
  instruments: { symbol: string } | null;
};

const PERIOD_LABEL = { train: "2021 t/m 2024", test: "2025", holdout: "Hold-out" } as const;

const pct = (v: number | null | undefined, sign = false) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "–"
    : new Intl.NumberFormat("nl-NL", {
        style: "percent",
        maximumFractionDigits: 1,
        signDisplay: sign ? "exceptZero" : "auto",
      }).format(v);

const r = (v: number | null | undefined) => {
  if (v === null || v === undefined) return "–";
  if (Math.abs(v) < 0.005) return "0 R"; // anders "-0 R" door afronding
  return `${v > 0 ? "+" : ""}${fmtNum(v)} R`;
};

const tone = (v: number | null | undefined) =>
  v === null || v === undefined ? "text-muted" : v > 0 ? "text-up" : v < 0 ? "text-down" : "";

const date = (iso: string) =>
  new Date(iso).toLocaleDateString("nl-NL", { timeZone: "UTC", day: "numeric", month: "short", year: "numeric" });

/** Alle trades van alle instrumenten samen: gewogen naar het aantal trades. */
function pool(runs: Run[]) {
  const withTrades = runs.filter((x) => x.metrics.trades > 0);
  const trades = withTrades.reduce((s, x) => s + x.metrics.trades, 0);
  if (!trades) return { trades: 0, winrate: null, avgR: null, randomR: null };
  const w = (f: (x: Run) => number | null | undefined) =>
    withTrades.reduce((s, x) => s + (f(x) ?? 0) * x.metrics.trades, 0) / trades;
  const withRandom = withTrades.filter((x) => x.benchmarks.random_entry);
  return {
    trades,
    winrate: w((x) => x.metrics.winrate),
    avgR: w((x) => x.metrics.avg_r),
    randomR: withRandom.length ? w((x) => x.benchmarks.random_entry?.avg_r_median) : null,
  };
}

function Verdict({ kind, runs }: { kind: "train" | "test"; runs: Run[] }) {
  const p = pool(runs);
  return (
    <div className="rounded-2xl border border-line bg-panel p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">
        {kind === "train" ? "Ontwikkelperiode" : "Testperiode"} · {PERIOD_LABEL[kind]}
      </p>
      <p className={`num mt-2 text-3xl font-medium ${tone(p.avgR)}`}>{r(p.avgR)}</p>
      <p className="text-sm text-muted">gemiddeld per trade, na kosten</p>
      <dl className="num mt-4 grid grid-cols-3 gap-2 text-sm">
        <div>
          <dt className="font-sans text-xs text-muted">Trades</dt>
          <dd>{fmtNum(p.trades, 0)}</dd>
        </div>
        <div>
          <dt className="font-sans text-xs text-muted">Winrate</dt>
          <dd>{pct(p.winrate)}</dd>
        </div>
        <div>
          <dt className="font-sans text-xs text-muted">Willekeurig</dt>
          <dd className={tone(p.randomR)}>{r(p.randomR)}</dd>
        </div>
      </dl>
    </div>
  );
}

function InstrumentTable({ runs }: { runs: Run[] }) {
  const rows = runs
    .filter((x) => x.period_kind === "train" || x.period_kind === "test" || x.period_kind === "holdout")
    .sort(
      (a, b) =>
        (a.instruments?.symbol ?? "").localeCompare(b.instruments?.symbol ?? "") ||
        a.period_start.localeCompare(b.period_start),
    );
  const heads = ["Instrument", "Periode", "Trades", "Winrate", "Gem. R", "PF", "Rendement", "Max. daling", "Vasthouden", "Willekeurig", "Beter dan toeval"];
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
      <table className="w-full min-w-[920px] text-sm">
        <thead className="bg-panel-2 text-left text-xs text-muted">
          <tr>
            {heads.map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="num divide-y divide-line">
          {rows.map((x) => {
            const m = x.metrics;
            const rnd = x.benchmarks.random_entry;
            return (
              <tr key={x.id} className="hover:bg-panel-2/50">
                <td className="px-3 py-2 font-sans font-medium">{x.instruments?.symbol}</td>
                <td className="px-3 py-2 font-sans text-muted">
                  {PERIOD_LABEL[x.period_kind as keyof typeof PERIOD_LABEL] ?? x.period_kind}
                </td>
                <td className="px-3 py-2">{m.trades}</td>
                <td className="px-3 py-2">{pct(m.winrate)}</td>
                <td className={`px-3 py-2 ${tone(m.avg_r)}`}>{r(m.avg_r)}</td>
                <td className="px-3 py-2">{fmtNum(m.profit_factor)}</td>
                <td className={`px-3 py-2 ${tone(m.return_pct)}`}>{pct(m.return_pct, true)}</td>
                <td className="px-3 py-2 text-muted">{pct(m.max_drawdown_pct, true)}</td>
                <td className={`px-3 py-2 ${tone(x.benchmarks.buy_and_hold.return_pct)}`}>
                  {pct(x.benchmarks.buy_and_hold.return_pct, true)}
                </td>
                <td className="px-3 py-2 text-muted">{r(rnd?.avg_r_median)}</td>
                <td className="px-3 py-2">{pct(m.beats_random_share)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WalkForward({ runs }: { runs: Run[] }) {
  const byStart = new Map<string, Run[]>();
  for (const x of runs.filter((x) => x.period_kind === "walk_forward")) {
    byStart.set(x.period_start, [...(byStart.get(x.period_start) ?? []), x]);
  }
  const blocks = [...byStart.entries()].sort(([a], [b]) => a.localeCompare(b));
  if (!blocks.length) return null;
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
      <table className="w-full text-sm">
        <thead className="bg-panel-2 text-left text-xs text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Blok</th>
            <th className="px-3 py-2 font-medium">Trades</th>
            <th className="px-3 py-2 font-medium">Winrate</th>
            <th className="px-3 py-2 font-medium">Gem. R</th>
          </tr>
        </thead>
        <tbody className="num divide-y divide-line">
          {blocks.map(([start, rs]) => {
            const p = pool(rs);
            return (
              <tr key={start}>
                <td className="px-3 py-2 font-sans text-muted">
                  {date(start)} t/m {date(rs[0].period_end)}
                </td>
                <td className="px-3 py-2">{p.trades}</td>
                <td className="px-3 py-2">{pct(p.winrate)}</td>
                <td className={`px-3 py-2 ${tone(p.avgR)}`}>{r(p.avgR)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

async function Report({ interval }: { interval: Interval }) {
  await connection();
  const supabase = await createClient();
  const { data } = await supabase
    .from("backtest_runs")
    .select(
      "id, strategy_version, interval, params, period_kind, period_start, period_end, metrics, benchmarks, created_at, instruments(symbol)",
    )
    .eq("interval", interval)
    .order("created_at", { ascending: false })
    .limit(500);
  const all = (data as unknown as Run[] | null) ?? [];
  // Eén backtest wordt in één keer opgeslagen: alle regels van de laatste run delen created_at.
  const runs = all.filter((x) => x.created_at === all[0]?.created_at);

  if (!runs.length) {
    return (
      <div className="rounded-2xl border border-dashed border-line bg-panel px-5 py-8 text-center text-sm text-muted">
        Nog geen backtest opgeslagen voor {interval}. Draai in de worker{" "}
        <code className="num">python -m koersradar.backtest.run --interval {interval} --save-db</code>.
      </div>
    );
  }

  const first = runs[0];
  const costs = first.params.costs;
  const train = runs.filter((x) => x.period_kind === "train");
  const test = runs.filter((x) => x.period_kind === "test");
  const testR = pool(test).avgR;

  return (
    <>
      <section className="mb-8 grid gap-4 md:grid-cols-2">
        <Verdict kind="train" runs={train} />
        <Verdict kind="test" runs={test} />
      </section>

      <p className="mb-10 max-w-3xl text-sm leading-relaxed">
        {testR === null
          ? "In de testperiode gaf de strategie geen trades."
          : testR > 0
            ? "In de testperiode verdiende de strategie gemiddeld iets na kosten. Kijk of dat over alle blokken hieronder standhoudt voordat je er waarde aan hecht."
            : "Na kosten verliest deze strategie gemiddeld geld per trade, ook in de testperiode. Volg de signalen nog niet met echt geld."}
      </p>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted">Per instrument</h2>
        <InstrumentTable runs={runs} />
      </section>

      <section className="mb-10">
        <h2 className="mb-1 text-sm font-medium uppercase tracking-wide text-muted">Per blok van 3 maanden</h2>
        <p className="mb-3 text-sm text-muted">
          Alle instrumenten samen. Een strategie die werkt, is in de meeste blokken positief en niet alleen in één goede
          periode.
        </p>
        <WalkForward runs={runs} />
      </section>

      <details className="rounded-2xl border border-line bg-panel p-5 text-sm leading-relaxed">
        <summary className="cursor-pointer font-medium">Hoe lees je dit?</summary>
        <dl className="mt-3 grid gap-3 sm:grid-cols-[10rem_1fr]">
          <dt className="text-muted">Gem. R</dt>
          <dd>
            Winst of verlies per trade in &quot;keer het risico&quot;. +1 R: je won wat je riskeerde. −1 R: de stop werd
            geraakt. Boven nul is goed.
          </dd>
          <dt className="text-muted">Rendement</dt>
          <dd>Resultaat van de hele periode als elke trade {pct(first.params.risk_frac ?? 0.01)} van het kapitaal riskeert.</dd>
          <dt className="text-muted">Max. daling</dt>
          <dd>De grootste daling vanaf een hoogste stand. Zo pijnlijk werd het onderweg.</dd>
          <dt className="text-muted">PF</dt>
          <dd>Profit factor: totale winst gedeeld door totaal verlies. Boven 1 is winstgevend.</dd>
          <dt className="text-muted">Vasthouden</dt>
          <dd>Wat kopen aan het begin en verkopen aan het eind van de periode had opgeleverd.</dd>
          <dt className="text-muted">Willekeurig</dt>
          <dd>
            Gem. R bij instappen op willekeurige momenten, met dezelfde stop, hetzelfde doel en dezelfde kosten (mediaan
            van {first.benchmarks.random_entry?.runs ?? 100} keer proberen).
          </dd>
          <dt className="text-muted">Beter dan toeval</dt>
          <dd>Welk deel van die willekeurige pogingen het slechter deed dan de strategie.</dd>
          <dt className="text-muted">Perioden</dt>
          <dd>
            2021 t/m 2024 is de ontwikkelperiode, 2025 de testperiode. 2026 blijft bewust buiten beeld als laatste
            controle, zodat we de regels er niet op kunnen afstemmen.
          </dd>
        </dl>
      </details>

      <p className="mt-6 text-xs leading-relaxed text-muted">
        Strategie {first.strategy_version} · berekend op {date(first.created_at)} · instap op de open na het signaal,
        stop gaat voor doel binnen één candle
        {costs && (
          <>
            {" "}
            · kosten: fee {pct(costs.taker_fee)}, spread {pct(costs.spread)} plus slippage
            {!costs.checked_on && <span className="text-warn"> (tarieven nog niet gecontroleerd)</span>}
          </>
        )}
        . Een backtest laat zien hoe de regels het in het verleden deden. Het is geen voorspelling en geen advies.
      </p>
    </>
  );
}

async function BacktestContent(props: PageProps<"/backtest">) {
  const sp = await props.searchParams;
  const interval: Interval = INTERVALS.includes(sp.iv as Interval) ? (sp.iv as Interval) : "1h";
  return (
    <>
      <nav className="mb-6 flex w-fit gap-1 rounded-full border border-line bg-panel p-1">
        {INTERVALS.map((iv) => (
          <Link
            key={iv}
            href={`/backtest?iv=${iv}`}
            className={`rounded-full px-3.5 py-1 text-sm font-medium ${iv === interval ? "bg-panel-2 text-text" : "text-muted hover:text-text"}`}
          >
            {iv}
          </Link>
        ))}
      </nav>
      <Report interval={interval} />
    </>
  );
}

export default function BacktestPage(props: PageProps<"/backtest">) {
  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-4">
        <h1 className="animate-fade-slide-in-1 font-display text-4xl tracking-tight sm:text-5xl">Backtest</h1>
        <p className="mt-1 text-sm text-muted">Hoe de scanner het sinds 2021 had gedaan, na kosten.</p>
      </header>
      <Suspense fallback={<p className="text-muted">Laden…</p>}>
        <BacktestContent {...props} />
      </Suspense>
    </div>
  );
}
