"""HYP-03: Multi-Timeframe Trend Pullback Strategy for XAUUSD.

Economic thesis:
Gold exhibits strong macro regimes driven by interest rates & inflation.
Trading in the dominant trend direction after a temporary mean-reversion
pullback provides high risk-reward entries with strong institutional support.
"""

from typing import Optional
import numpy as np
import pandas as pd

from python_brain.backtest.models import Signal
from python_brain.backtest.strategy_base import Strategy


class TrendPullbackStrategy(Strategy):
    """HYP-03: EMA Trend Filter + RSI Pullback Entry."""

    def __init__(
        self,
        fast_ema: int = 20,
        slow_ema: int = 50,
        trend_ema: int = 200,
        rsi_period: int = 14,
        rsi_oversold: float = 45.0,
        rsi_overbought: float = 55.0,
        atr_period: int = 14,
        atr_sl_mult: float = 1.5,
        rr_ratio: float = 2.0,
    ):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.trend_ema = trend_ema
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.atr_period = atr_period
        self.atr_sl_mult = atr_sl_mult
        self.rr_ratio = rr_ratio

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        if len(history) < self.trend_ema + 5:
            return None

        closes = history["close"].values
        highs = history["high"].values
        lows = history["low"].values
        current_time = history["time_utc"].iloc[-1]

        # EMA calculations (Vectorized ewm)
        s_closes = pd.Series(closes)
        ema_fast = s_closes.ewm(span=self.fast_ema, adjust=False).mean().values
        ema_slow = s_closes.ewm(span=self.slow_ema, adjust=False).mean().values
        ema_trend = s_closes.ewm(span=self.trend_ema, adjust=False).mean().values

        # RSI(14)
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.mean(gains[-self.rsi_period:]) if len(gains) >= self.rsi_period else 0.001
        avg_loss = np.mean(losses[-self.rsi_period:]) if len(losses) >= self.rsi_period else 0.001
        rs = avg_gain / max(avg_loss, 1e-6)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # ATR(14)
        tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))[1:]
        atr = float(np.mean(tr[-self.atr_period:])) if len(tr) >= self.atr_period else 2.0
        sl_dist = max(atr * self.atr_sl_mult, 1.5)

        curr_close = closes[-1]
        prev_close = closes[-2]

        is_bull_trend = ema_slow[-1] > ema_trend[-1] and curr_close > ema_trend[-1]
        is_bear_trend = ema_slow[-1] < ema_trend[-1] and curr_close < ema_trend[-1]

        # Bullish Pullback: In bull trend, price pulls back to between fast and slow EMA, RSI cools down
        # Trigger: current bar turns back up above previous high
        if is_bull_trend:
            in_pullback = curr_close <= ema_fast[-1] and curr_close >= (ema_slow[-1] - 0.5 * atr)
            rsi_ready = rsi <= self.rsi_oversold
            trigger = curr_close > highs[-2]

            if in_pullback and rsi_ready and trigger:
                sl = curr_close - sl_dist
                tp = curr_close + (sl_dist * self.rr_ratio)
                return Signal(
                    time_utc=current_time,
                    action="BUY",
                    sl=round(sl, 3),
                    tp=round(tp, 3),
                    comment="HYP03_Pullback_BUY",
                )

        # Bearish Pullback
        elif is_bear_trend:
            in_pullback = curr_close >= ema_fast[-1] and curr_close <= (ema_slow[-1] + 0.5 * atr)
            rsi_ready = rsi >= self.rsi_overbought
            trigger = curr_close < lows[-2]

            if in_pullback and rsi_ready and trigger:
                sl = curr_close + sl_dist
                tp = curr_close - (sl_dist * self.rr_ratio)
                return Signal(
                    time_utc=current_time,
                    action="SELL",
                    sl=round(sl, 3),
                    tp=round(tp, 3),
                    comment="HYP03_Pullback_SELL",
                )

        return None
