import sys

import numpy as np
import pandas as pd

from core.strategy import StrategyEngine


def make_df(trend: str) -> pd.DataFrame:
    n = 120
    ts = pd.date_range("2026-01-01", periods=n, freq="min", tz="UTC")
    if trend == "buy":
        base = np.linspace(100, 120, n) + np.sin(np.arange(n) / 3)
        base[-15:] -= np.linspace(2.0, 8.0, 15)  # lower RSI while trend still strong
        volume = np.ones(n) * 100
        volume[-1] = 130
    else:
        base = np.linspace(120, 100, n) - np.sin(np.arange(n) / 3)
        base[-15:] += np.linspace(2.0, 8.0, 15)
        volume = np.ones(n) * 100
        volume[-1] = 130
    return pd.DataFrame({"timestamp": ts, "open": base, "high": base + 1, "low": base - 1, "close": base, "volume": volume})


def run_test() -> int:
    s = StrategyEngine()
    buy_signal = s.generate_signal(make_df("buy"), "BTC/USDT")
    sell_signal = s.generate_signal(make_df("sell"), "ETH/USDT")

    ok = True
    if not (buy_signal.action == "BUY" and buy_signal.score >= 2):
        print(f"FAIL: BUY test -> action={buy_signal.action}, score={buy_signal.score}")
        ok = False
    if not (sell_signal.action == "SELL" and sell_signal.score >= 2):
        print(f"FAIL: SELL test -> action={sell_signal.action}, score={sell_signal.score}")
        ok = False

    if ok:
        print(f"PASS: BUY={buy_signal.action}/{buy_signal.score}, SELL={sell_signal.action}/{sell_signal.score}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(run_test())
