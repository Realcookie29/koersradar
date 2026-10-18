"""Vergelijk een vaste lijst strategievarianten, eerst alleen op de ontwikkelperiode.

Spelregel (vooraf vastgelegd, zie docs/backtest-varianten.md):
  1. Alle varianten draaien op train (tot --split). De test- en hold-outdata worden niet bekeken.
  2. Gekozen wordt de variant met de hoogste gem. R na kosten op train, met >= MIN_TRADES trades.
  3. Alleen die variant (plus de basis ter vergelijking) gaat met --check-test één keer over 2025.

Voorbeelden:
  python -m koersradar.backtest.research --interval 1h
  python -m koersradar.backtest.research --interval 1h --check-test dagtrend
"""

import argparse
import logging
from datetime import UTC

import numpy as np
import pandas as pd

from koersradar.backtest.engine import simulate
from koersradar.backtest.run import make_periods
from koersradar.config import CostModel, load_costs, load_instruments
from koersradar.ingest.store import read_history
from koersradar.strategies import trend_pullback as tp

MIN_TRADES = 100
FREE = CostModel(0.0, 0.0, 0.0, 0.0, 0.0, None)
REGIME_SYMBOL = "BTC/USDT"

# name -> (variant, BTC-dagtrend als marktfilter)
VARIANTS: dict[str, tuple[tp.Variant, bool]] = {
    "basis": (tp.BASE, False),
    "ruime-stop": (tp.Variant(stop_atr=2.5), False),
    "kostenfilter": (tp.Variant(max_cost_share=0.10), False),
    "dagtrend": (tp.Variant(htf="1D"), False),
    "btc-trend": (tp.BASE, True),
    "combinatie": (tp.Variant(max_cost_share=0.10, htf="1D"), True),
}


def _regime(btc: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
    """BTC-dagtrend per candle van df (zelfde tijdstippen, anders de laatst bekende waarde)."""
    up = pd.DataFrame({"open_time": btc["open_time"], "up": tp.htf_trend(btc, "1D").to_numpy()})
    merged = pd.merge_asof(df[["open_time"]], up, on="open_time", direction="backward")
    return pd.Series(merged["up"].eq(True).to_numpy(), index=df.index)


def run(interval: str, kind: str, names: list[str], split: str, holdout: str) -> pd.DataFrame:
    costs_all = load_costs()
    instruments = [
        i for i in load_instruments() if i.market == "crypto" and interval in i.intervals
    ]
    btc = read_history("binance", REGIME_SYMBOL, interval).reset_index(drop=True)
    out = []
    for ins in instruments:
        costs = costs_all[ins.source]
        df = read_history(ins.source, ins.symbol, interval).reset_index(drop=True)
        times = pd.DatetimeIndex(df["open_time"])
        periods = make_periods(
            times[0],
            times[-1],
            split=pd.Timestamp(split, tz=UTC),
            holdout=pd.Timestamp(holdout, tz=UTC),
            wf_months=3,
            include_holdout=False,
        )
        regime = _regime(btc, df)
        for name in names:
            variant, use_regime = VARIANTS[name]
            sig = tp.evaluate_all(df, costs, variant, regime if use_regime else None)
            for p in periods:
                if p.kind not in (kind, "walk_forward"):
                    continue
                if p.kind == "walk_forward" and (kind == "train") != (
                    p.end <= pd.Timestamp(split, tz=UTC)
                ):
                    continue
                start, end = int(times.searchsorted(p.start)), int(times.searchsorted(p.end))
                for label, c in (("netto", costs), ("bruto", FREE)):
                    for t in simulate(df, sig, c, start, end).trades:
                        out.append(
                            {
                                "variant": name,
                                "symbol": ins.symbol,
                                "period": p.kind,
                                "block": p.start,
                                "kosten": label,
                                "r": t.r_multiple,
                            }
                        )
    return pd.DataFrame(out)


def table(trades: pd.DataFrame, kind: str, names: list[str]) -> pd.DataFrame:
    rows = []
    for name in names:
        t = trades[(trades.variant == name) & (trades.period == kind)]
        net, gross = t[t.kosten == "netto"]["r"], t[t.kosten == "bruto"]["r"]
        blocks = (
            trades[
                (trades.variant == name)
                & (trades.period == "walk_forward")
                & (trades.kosten == "netto")
            ]
            .groupby("block")["r"]
            .mean()
        )
        gains, losses = net[net > 0].sum(), -net[net < 0].sum()
        rows.append(
            {
                "variant": name,
                "trades": len(net),
                "winrate": float((net > 0).mean()) if len(net) else np.nan,
                "gem_R_netto": float(net.mean()) if len(net) else np.nan,
                "gem_R_bruto": float(gross.mean()) if len(gross) else np.nan,
                "PF": float(gains / losses) if losses > 0 else np.nan,
                "kwartalen_positief": f"{int((blocks > 0).sum())}/{len(blocks)}",
            }
        )
    return pd.DataFrame(rows).set_index("variant")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--interval", default="1h", choices=["15m", "1h"])
    ap.add_argument("--split", default="2025-01-01")
    ap.add_argument("--holdout", default="2026-01-01")
    ap.add_argument(
        "--check-test", metavar="VARIANT", help="controleer deze variant één keer op 2025"
    )
    args = ap.parse_args()
    logging.basicConfig(level="WARNING")
    pd.set_option("display.width", 140)
    fmt = {
        "winrate": "{:.1%}".format,
        "gem_R_netto": "{:+.2f}".format,
        "gem_R_bruto": "{:+.2f}".format,
        "PF": "{:.2f}".format,
    }

    if args.check_test:
        names = ["basis", args.check_test]
        trades = run(args.interval, "test", names, args.split, args.holdout)
        print(
            f"\nTestperiode {args.split} t/m {args.holdout} ({args.interval}), eenmalige controle\n"
        )
        print(table(trades, "test", names).to_string(formatters=fmt))
        return

    names = list(VARIANTS)
    trades = run(args.interval, "train", names, args.split, args.holdout)
    res = table(trades, "train", names)
    print(f"\nOntwikkelperiode tot {args.split} ({args.interval}), alle crypto, na kosten\n")
    print(res.to_string(formatters=fmt))
    eligible = res[res.trades >= MIN_TRADES]
    if not eligible.empty:
        scores = eligible["gem_R_netto"]
        best = str(scores.idxmax())
        print(f"\nGekozen volgens de spelregel: {best} (gem. R netto {scores.max():+.2f})")


if __name__ == "__main__":
    main()
