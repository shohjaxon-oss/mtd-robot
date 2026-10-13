"""HYP-02: Volatility Squeeze Strategy for XAUUSD.

Economic thesis:
Low volatility compression (Bollinger Bands inside Keltner Channel)
inevitably resolves into high volatility directional momentum expansion.
"""

from typing import Optional
import numpy as np
import pandas as pd

from python_brain.backtest.models import Signal
from python_brain.backtest.strategy_base import Strategy


class VolatilitySqueezeStrategy(Strategy):
    """HYP-02: Bollinger Bands & Keltner Channel Squeeze Breakout."""

    def __init__(
        self,
        period: int = 20,
        bb_mult: float = 2.0,
        kc_mult: float = 1.5,
        atr_period: int = 14,
        atr_sl_mult: float = 1.5,
        rr_ratio: float = 2.0,
    ):
        self.period = period
        self.bb_mult = bb_mult
        self.kc_mult = kc_mult
        self.atr_period = atr_period
        self.atr_sl_mult = atr_sl_mult
        self.rr_ratio = rr_ratio

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        if len(history) < max(self.period, self.atr_period) + 5:
            return None

        closes = history["close"].values
        highs = history["high"].values
        lows = history["low"].values
        current_time = history["time_utc"].iloc[-1]

        # 1. Bollinger Bands
        sma = float(np.mean(closes[-self.period:]))
        std = float(np.std(closes[-self.period:]))
        bb_upper = sma + (self.bb_mult * std)
        bb_lower = sma - (self.bb_mult * std)

        # 2. Keltner Channel
        tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))[1:]
        atr = float(np.mean(tr[-self.atr_period:])) if len(tr) >= self.atr_period else 2.0
        kc_upper = sma + (self.kc_mult * atr)
        kc_lower = sma - (self.kc_mult * atr)

        # Squeeze condition on previous candle: BB inside KC
        # (bb_upper < kc_upper) and (bb_lower > kc_lower)
        prev_closes = closes[:-1]
        prev_sma = float(np.mean(prev_closes[-self.period:]))
        prev_std = float(np.std(prev_closes[-self.period:]))
        prev_bb_upper = prev_sma + (self.bb_mult * prev_std)
        prev_bb_lower = prev_sma - (self.bb_mult * prev_std)

        prev_tr = tr[:-1] if len(tr) > 1 else tr
        prev_atr = float(np.mean(prev_tr[-self.atr_period:])) if len(prev_tr) >= self.atr_period else 2.0
        prev_kc_upper = prev_sma + (self.kc_mult * prev_atr)
        prev_kc_lower = prev_sma - (self.kc_mult * prev_atr)

        was_in_squeeze = (prev_bb_upper < prev_kc_upper) and (prev_bb_lower > prev_kc_lower)

        current_close = float(closes[-1])
        sl_dist = max(atr * self.atr_sl_mult, 1.5)

        # Bullish Squeeze Fired
        if was_in_squeeze and current_close > kc_upper:
            sl = current_close - sl_dist
            tp = current_close + (sl_dist * self.rr_ratio)
            return Signal(
                time_utc=current_time,
                action="BUY",
                sl=round(sl, 3),
                tp=round(tp, 3),
                comment="HYP02_Squeeze_BUY",
            )

        # Bearish Squeeze Fired
        elif was_in_squeeze and current_close < kc_lower:
            sl = current_close + sl_dist
            tp = current_close - (sl_dist * self.rr_ratio)
            return Signal(
                time_utc=current_time,
                action="SELL",
                sl=round(sl, 3),
                tp=round(tp, 3),
                comment="HYP02_Squeeze_SELL",
            )

        return None
