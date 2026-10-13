"""Base strategy class and initial diagnostic baseline strategies.

Core architectural principle:
The EXACT same strategy signal code is utilized both in offline backtesting and in live forward execution.
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
import pandas as pd
from python_brain.backtest.models import Signal


class Strategy(ABC):
    """Abstract Strategy interface. Guaranteed zero-lookahead on_bar signature."""

    @abstractmethod
    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        """Receives historical closed candles up to bar t. Returns trade Signal or None."""
        pass


class MovingAverageCrossStrategy(Strategy):
    """Deterministic MA Crossover baseline for engine verification and sanity checks."""

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        sl_points: float = 300.0,   # 30 cents on gold ($0.30)
        tp_points: float = 600.0,   # 60 cents on gold ($0.60, R:R = 2.0)
        point: float = 0.001,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.sl_points = sl_points
        self.tp_points = tp_points
        self.point = point

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        if len(history) < self.slow_period + 2:
            return None

        closes_arr = history["close"].values
        current_time = history["time_utc"].iloc[-1]
        current_close = float(closes_arr[-1])

        # High-performance O(1) sliding window calculation
        fast_prev = float(np.mean(closes_arr[-self.fast_period - 1 : -1]))
        fast_curr = float(np.mean(closes_arr[-self.fast_period :]))
        slow_prev = float(np.mean(closes_arr[-self.slow_period - 1 : -1]))
        slow_curr = float(np.mean(closes_arr[-self.slow_period :]))

        # Bullish crossover on bar close
        if fast_prev <= slow_prev and fast_curr > slow_curr:
            sl = current_close - (self.sl_points * self.point)
            tp = current_close + (self.tp_points * self.point)
            return Signal(
                time_utc=current_time,
                action="BUY",
                sl=round(sl, 3),
                tp=round(tp, 3),
                comment="MA_Cross_Bullish",
            )

        # Bearish crossover on bar close
        elif fast_prev >= slow_prev and fast_curr < slow_curr:
            sl = current_close + (self.sl_points * self.point)
            tp = current_close - (self.tp_points * self.point)
            return Signal(
                time_utc=current_time,
                action="SELL",
                sl=round(sl, 3),
                tp=round(tp, 3),
                comment="MA_Cross_Bearish",
            )

        return None


class RandomEntryStrategy(Strategy):
    """Randomized entry baseline used to empirically measure cost drag against theoretical expectancy."""

    def __init__(
        self,
        entry_probability: float = 0.05,
        sl_points: float = 300.0,
        tp_points: float = 300.0,  # 1:1 R:R
        seed: int = 42,
        point: float = 0.001,
    ):
        self.entry_probability = entry_probability
        self.sl_points = sl_points
        self.tp_points = tp_points
        self.point = point
        self.rng = np.random.RandomState(seed)

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        if len(history) < 5:
            return None

        current_time = history["time_utc"].iloc[-1]
        current_close = history["close"].iloc[-1]

        dice = self.rng.rand()
        if dice < self.entry_probability:
            # 50% Buy, 50% Sell
            is_buy = self.rng.rand() > 0.5
            action = "BUY" if is_buy else "SELL"
            sl_dir = -1.0 if is_buy else 1.0
            tp_dir = 1.0 if is_buy else -1.0

            sl = current_close + (sl_dir * self.sl_points * self.point)
            tp = current_close + (tp_dir * self.tp_points * self.point)

            return Signal(
                time_utc=current_time,
                action=action,
                sl=round(sl, 3),
                tp=round(tp, 3),
                comment="Random_Benchmark",
            )

        return None
