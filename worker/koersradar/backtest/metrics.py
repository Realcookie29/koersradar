"""Metrieken en benchmarks voor een backtest-periode.

Rendement wordt berekend met vaste risico-sizing: elke trade riskeert `risk_frac` van het
kapitaal (plan: max 1%). Een trade van +2R levert dan +2% op, een stop -1%.
"""

import math

import numpy as np
import pandas as pd

from koersradar.backtest.engine import SimResult, buy_cost, random_signals, sell_proceeds, simulate
from koersradar.config import CostModel

RISK_FRAC = 0.01
RANDOM_RUNS = 200
RANDOM_SEED = 42


def _max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    return float((equity / peak - 1).min())


def summarize(res: SimResult, risk_frac: float = RISK_FRAC) -> dict[str, float | int | None]:
    r = np.array([t.r_multiple for t in res.trades], dtype=float)
    n = len(r)
    equity = np.cumprod(np.r_[1.0, 1 + risk_frac * r])
    gains, losses = r[r > 0].sum(), -r[r < 0].sum()
    reasons = pd.Series([t.exit_reason for t in res.trades], dtype="object").value_counts()
    return {
        "trades": n,
        "winrate": float((r > 0).mean()) if n else None,
        "avg_r": float(r.mean()) if n else None,
        "median_r": float(np.median(r)) if n else None,
        "profit_factor": float(gains / losses) if losses > 0 else (math.inf if gains > 0 else None),
        "return_pct": float(equity[-1] - 1),
        "max_drawdown_pct": _max_drawdown(equity),
        "exposure": res.bars_in_trade / res.bars if res.bars else 0.0,
        "avg_bars_held": float(np.mean([t.bars_held for t in res.trades])) if n else None,
        "skipped_gaps": res.skipped_gaps,
        **{f"exit_{k}": int(v) for k, v in reasons.items()},
    }


def buy_and_hold(df: pd.DataFrame, costs: CostModel, start: int, end: int, atr: float) -> dict:
    """Kopen op de eerste open, houden tot de laatste slot (met kosten aan beide kanten)."""
    cost = buy_cost(float(df["open"].iloc[start]), atr, costs)
    closes = df["close"].iloc[start:end].to_numpy(dtype=float)
    path = np.r_[cost, closes]
    proceeds = sell_proceeds(float(closes[-1]), atr, costs)
    return {"return_pct": proceeds / cost - 1, "max_drawdown_pct": _max_drawdown(path)}


def random_entry(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    costs: CostModel,
    start: int,
    end: int,
    n_trades: int,
    min_history: int,
    runs: int = RANDOM_RUNS,
    seed: int = RANDOM_SEED,
) -> dict | None:
    """Instappen op willekeurige candles met dezelfde stop- en doelregels en kosten.
    Ongeveer even veel kansen als de strategie; laat zien wat toeval oplevert."""
    idx = np.arange(len(df))
    eligible = (
        (idx >= max(start, min_history - 1)) & (idx < end) & signals["atr"].notna().to_numpy()
    )
    n_eligible = int(eligible.sum())
    if n_trades == 0 or n_eligible == 0:
        return None
    prob = min(1.0, n_trades / n_eligible)
    rng = np.random.default_rng(seed)
    avg_r, ret = [], []
    for _ in range(runs):
        res = simulate(df, random_signals(signals, prob, rng, eligible), costs, start, end)
        s = summarize(res)
        if s["trades"]:
            avg_r.append(s["avg_r"])
            ret.append(s["return_pct"])
    if not avg_r:
        return None
    a, r = np.array(avg_r), np.array(ret)
    return {
        "runs": len(a),
        "avg_r_median": float(np.median(a)),
        "avg_r_p5": float(np.percentile(a, 5)),
        "avg_r_p95": float(np.percentile(a, 95)),
        "return_pct_median": float(np.median(r)),
        "return_pct_p5": float(np.percentile(r, 5)),
        "return_pct_p95": float(np.percentile(r, 95)),
        "_avg_r_runs": a,  # voor percentielrang; niet opslaan
    }


def percentile_rank(value: float | None, sample: np.ndarray) -> float | None:
    """Welk deel van de willekeurige runs deed het slechter dan de strategie."""
    if value is None or len(sample) == 0:
        return None
    return float((sample < value).mean())
