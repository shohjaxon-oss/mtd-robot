"""HYP-04: Mean Reversion Range Strategy for XAUUSD.

Economic thesis:
In low-ADX range conditions, price excursions beyond extreme Bollinger Bands
represent temporary over-extensions that predictably mean-revert to the moving average.
"""

from typing import Optional
import numpy as np
import pandas as pd

from python_brain.backtest.models import Signal
from python_brain.backtest.strategy_base import Strategy


class MeanReversionStrategy(Strategy):
    """HYP-04: Low-ADX Bollinger Band Mean Reversion."""

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.2,
        adx_period: int = 14,
        adx_max: float = 22.0,  # Only active when market is non-trending
        atr_period: int = 14,
        atr_sl_mult: float = 1.2,
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.adx_period = adx_period
        self.adx_max = adx_max
        self.atr_period = atr_period
        self.atr_sl_mult = atr_sl_mult

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        if len(history) < max(self.bb_period, self.adx_period * 2) + 5:
            return None

        closes = history["close"].values
        highs = history["high"].values
        lows = history["low"].values
        current_time = history["time_utc"].iloc[-1]

        # 1. Bollinger Bands
        sma = float(np.mean(closes[-self.bb_period:]))
        std = float(np.std(closes[-self.bb_period:]))
        bb_upper = sma + (self.bb_std * std)
        bb_lower = sma - (self.bb_std * std)

        # 2. ADX calculation
        up_move = highs[1:] - highs[:-1]
        down_move = lows[:-1] - lows[1:]
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr = np.maximum(highs[1:] - lows[1:], np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])))
        if len(tr) < self.adx_period:
            return None

        tr_smooth = np.convolve(tr, np.ones(self.adx_period)/self.adx_period, mode="valid")
        p_dm_smooth = np.convolve(plus_dm, np.ones(self.adx_period)/self.adx_period, mode="valid")
        m_dm_smooth = np.convolve(minus_dm, np.ones(self.adx_period)/self.adx_period, mode="valid")

        if len(tr_smooth) == 0 or tr_smooth[-1] <= 0:
            return None

        p_di = 100.0 * (p_dm_smooth[-1] / tr_smooth[-1])
        m_di = 100.0 * (m_dm_smooth[-1] / tr_smooth[-1])
        di_sum = p_di + m_di
        dx = 100.0 * abs(p_di - m_di) / max(di_sum, 1e-6)
        adx = dx  # Proxy for instantaneous directional strength

        # Filter: Only trade in quiet ranging market
        if adx > self.adx_max:
            return None

        # 3. ATR(14)
        atr = float(np.mean(tr[-self.atr_period:])) if len(tr) >= self.atr_period else 2.0
        sl_dist = max(atr * self.atr_sl_mult, 1.2)

        curr_close = closes[-1]
        prev_close = closes[-2]

        # Oversold Mean Reversion (BUY): price dips below lower BB and closes back inside
        if prev_close <= bb_lower and curr_close > bb_lower:
            sl = curr_close - sl_dist
            tp = sma  # Target: Mean reversion back to central SMA
            if tp > curr_close + 0.5:
                return Signal(
                    time_utc=current_time,
                    action="BUY",
                    sl=round(sl, 3),
                    tp=round(tp, 3),
                    comment="HYP04_MeanRev_BUY",
                )

        # Overbought Mean Reversion (SELL): price spikes above upper BB and closes back inside
        elif prev_close >= bb_upper and curr_close < bb_upper:
            sl = curr_close + sl_dist
            tp = sma
            if tp < curr_close - 0.5:
                return Signal(
                    time_utc=current_time,
                    action="SELL",
                    sl=round(sl, 3),
                    tp=round(tp, 3),
                    comment="HYP04_MeanRev_SELL",
                )

        return None
