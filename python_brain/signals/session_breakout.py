"""HYP-01: Session Breakout Strategy for XAUUSD.

Economic thesis:
Asian session (00:00 - 07:00 UTC) consolidates liquidity.
London institutional open (07:00 - 10:00 UTC) injects massive volume,
driving strong directional breakout from the Asian range.
"""

from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd

from python_brain.backtest.models import Signal
from python_brain.backtest.strategy_base import Strategy


class SessionBreakoutStrategy(Strategy):
    """HYP-01: Asian Range Breakout at London Open."""

    def __init__(
        self,
        asian_start_hour: int = 0,
        asian_end_hour: int = 7,
        entry_window_hours: int = 3,  # 07:00 - 10:00 UTC
        atr_period: int = 14,
        atr_sl_mult: float = 1.5,
        rr_ratio: float = 2.0,
        point: float = 0.001,
    ):
        self.asian_start_hour = asian_start_hour
        self.asian_end_hour = asian_end_hour
        self.entry_window_hours = entry_window_hours
        self.atr_period = atr_period
        self.atr_sl_mult = atr_sl_mult
        self.rr_ratio = rr_ratio
        self.point = point

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        if len(history) < self.atr_period + 10:
            return None

        current_time = pd.to_datetime(history["time_utc"].iloc[-1])
        curr_hour = current_time.hour
        entry_end_hour = self.asian_end_hour + self.entry_window_hours

        # Only evaluate during London opening entry window
        if not (self.asian_end_hour <= curr_hour < entry_end_hour):
            return None

        # Extract current day's Asian session candles (00:00 - 07:00 UTC)
        times = pd.to_datetime(history["time_utc"])
        same_day_mask = (times.dt.date == current_time.date()) & (times.dt.hour >= self.asian_start_hour) & (times.dt.hour < self.asian_end_hour)
        asian_slice = history[same_day_mask]

        if len(asian_slice) < 3:
            return None

        asian_high = float(asian_slice["high"].max())
        asian_low = float(asian_slice["low"].min())

        current_close = float(history["close"].iloc[-1])
        prev_close = float(history["close"].iloc[-2])

        # Compute ATR(14)
        highs = history["high"].values
        lows = history["low"].values
        closes = history["close"].values
        tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))[1:]
        atr = float(np.mean(tr[-self.atr_period:])) if len(tr) >= self.atr_period else 2.0
        sl_dist = max(atr * self.atr_sl_mult, 1.5)

        # Bullish Breakout above Asian High
        if prev_close <= asian_high and current_close > asian_high:
            sl = current_close - sl_dist
            tp = current_close + (sl_dist * self.rr_ratio)
            return Signal(
                time_utc=current_time,
                action="BUY",
                sl=round(sl, 3),
                tp=round(tp, 3),
                comment="HYP01_Asian_Breakout_BUY",
            )

        # Bearish Breakout below Asian Low
        elif prev_close >= asian_low and current_close < asian_low:
            sl = current_close + sl_dist
            tp = current_close - (sl_dist * self.rr_ratio)
            return Signal(
                time_utc=current_time,
                action="SELL",
                sl=round(sl, 3),
                tp=round(tp, 3),
                comment="HYP01_Asian_Breakout_SELL",
            )

        return None
