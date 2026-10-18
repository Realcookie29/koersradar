"""Vergelijk de nieuwe instapideeën volgens de vooraf vastgelegde spelregel.

Zie docs/nieuwe-instap.md. Zonder --check-test wordt alleen de ontwikkelperiode bekeken.

Voorbeelden:
  python -m koersradar.backtest.ideas_research --interval 1h
  python -m koersradar.backtest.ideas_research --interval 1h --check-test breakout
"""

import argparse
import logging
from collections.abc import Callable
from datetime import UTC

import numpy as np
import pandas as pd

from koersradar.backtest.engine import random_signals, simulate
from koersradar.backtest.research import FREE, MIN_TRADES, table
from koersradar.backtest.run import make_periods
from koersradar.config import CostModel, load_costs, load_instruments
from koersradar.ingest.store import read_history
from koersradar.strategies import ideas

Builder = Callable[[pd.DataFrame, CostModel, pd.DataFrame], pd.DataFrame]
IDEAS: dict[str, Builder] = {
    "breakout": lambda df, c, _: ideas.breakout(df, c),
    "breakout-rust": lambda df, c, _: ideas.breakout_quiet(df, c),
    "momentum": ideas.momentum,
    "terugval": lambda df, c, _: ideas.pullback_rsi2(df, c),
}
RANDOM_RUNS = 100
RANDOM_SEED = 42


def _load(interval: str) -> list[tuple[str, CostModel, pd.DataFrame]]:
    costs_all = load_costs()
    return [
        (
            i.symbol,
            costs_all[i.source],
            read_history(i.source, i.symbol, interval).reset_index(drop=True),
        )
        for i in load_instruments()
        if i.market == "crypto" and interval in i.intervals
    ]


def _windows(df: pd.DataFrame, kind: str, split: str, holdout: str) -> list[tuple[str, int, int]]:
    times = pd.DatetimeIndex(df["open_time"])
    cut = pd.Timestamp(split, tz=UTC)
    out = []
    for p in make_periods(
        times[0], times[-1], cut, pd.Timestamp(holdout, tz=UTC), 3, include_holdout=False
    ):
        is_train_block = p.end <= cut
        if p.kind == kind or (p.kind == "walk_forward" and is_train_block == (kind == "train")):
            out.append((p.kind, int(times.searchsorted(p.start)), int(times.searchsorted(p.end))))
    return out


def run(
    interval: str, kind: str, names: list[str], split: str, holdout: str, random_runs: int = 0
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Trades per idee (netto en bruto) en, als gevraagd, de gem. R van willekeurige instap."""
    data = _load(interval)
    ranks = ideas.momentum_ranks({s: df for s, _, df in data})
    out = []
    rnd: dict[str, list[list[float]]] = {n: [[] for _ in range(random_runs)] for n in names}
    for symbol, costs, df in data:
        windows = _windows(df, kind, split, holdout)
        for name in names:
            sig = IDEAS[name](df, costs, ranks[symbol])
            rng = np.random.default_rng(RANDOM_SEED)
            for period, start, end in windows:
                for label, c in (("netto", costs), ("bruto", FREE)):
                    res = simulate(df, sig, c, start, end)
                    out += [
                        {
                            "variant": name,
                            "symbol": symbol,
                            "period": period,
                            "block": df["open_time"].iloc[start],
                            "kosten": label,
                            "r": t.r_multiple,
                        }
                        for t in res.trades
                    ]
                if period != kind or not random_runs:
                    continue
                # Willekeurige instap: zelfde stop en uitstap, ongeveer even veel trades.
                n = len(simulate(df, sig, costs, start, end).trades)
                idx = np.arange(len(df))
                eligible = (
                    (idx >= start)
                    & (idx < end)
                    & (idx >= ideas.MIN_HISTORY)
                    & np.isfinite(sig["stop"].to_numpy(dtype=float))
                )
                prob = min(1.0, n / max(1, int(eligible.sum())))
                for k in range(random_runs):
                    fake = random_signals(sig, prob, rng, eligible)
                    sim = simulate(df, fake, costs, start, end)
                    rnd[name][k] += [t.r_multiple for t in sim.trades]
    random_avg = {n: np.array([np.mean(r) for r in runs if r]) for n, runs in rnd.items()}
    return pd.DataFrame(out), random_avg


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--interval", default="1h", choices=["15m", "1h"])
    ap.add_argument("--split", default="2025-01-01")
    ap.add_argument("--holdout", default="2026-01-01")
    ap.add_argument("--check-test", metavar="IDEE", choices=list(IDEAS))
    args = ap.parse_args()
    logging.basicConfig(level="WARNING")
    pd.set_option("display.width", 140)
    fmt = {
        "winrate": "{:.1%}".format,
        "gem_R_netto": "{:+.2f}".format,
        "gem_R_bruto": "{:+.2f}".format,
        "PF": "{:.2f}".format,
    }

    kind = "test" if args.check_test else "train"
    names = [args.check_test] if args.check_test else list(IDEAS)
    trades, random_avg = run(
        args.interval, kind, names, args.split, args.holdout, random_runs=RANDOM_RUNS
    )
    res = table(trades, kind, names)
    res["willekeurig_R"] = [
        float(np.median(random_avg[n])) if len(random_avg[n]) else np.nan for n in names
    ]
    res["beter_dan_toeval"] = [
        float((random_avg[n] < res.loc[n, "gem_R_netto"]).mean()) if len(random_avg[n]) else np.nan
        for n in names
    ]
    fmt |= {"willekeurig_R": "{:+.2f}".format, "beter_dan_toeval": "{:.0%}".format}
    title = (
        f"Testperiode {args.split} t/m {args.holdout} ({args.interval}), eenmalige controle"
        if args.check_test
        else f"Ontwikkelperiode tot {args.split} ({args.interval}), alle crypto, na kosten"
    )
    print(f"\n{title}\n")
    print(res.to_string(formatters=fmt))
    if not args.check_test:
        eligible = res[res.trades >= MIN_TRADES]
        if not eligible.empty:
            best = str(eligible["gem_R_netto"].idxmax())
            print(f"\nGekozen volgens de spelregel: {best}")


if __name__ == "__main__":
    main()
