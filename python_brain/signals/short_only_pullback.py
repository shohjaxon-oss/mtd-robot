"""Gipoteza 8: Short-Only Trend Pullback (HYP-08, POST-HOC).

Timeframe: H1 (yoki H4).
Iqtisodiy mantiq (POST-HOC, HYP03 natijalari asosida):
Exness MT5 da XAUUSD Short pozitsiyalari 100% SWAP-FREE ($0.00). Shu bilan birga,
oltin narxining keskin tushishlari (panika va likvidatsiya) yuqori tezlikda ro'y beradi.
Long swap (-$52.62/lot) tufayli barcha Long savdolar chetlatiladi va faqat
pasayuvchi trendda (D1/H4 da narx EMA 200 dan past bo'lganda) pullback'lar sotiladi.

Qoidalar:
- Trend filtri: Close < EMA200
- Pullback: Narx EMA 20 va EMA 50 oralig'iga ko'tariladi va RSI(14) >= 55 (overbought pullback)
- Kirish: FAQAT SELL (Short-only)
- SL: $1.5 * ATR(14)
- TP: $2.0 * SL masofasi
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from python_brain.backtest.models import Signal
from python_brain.backtest.strategy_base import Strategy


class ShortOnlyTrendPullbackStrategy(Strategy):
    def __init__(
        self,
        fast_ema: int = 20,
        slow_ema: int = 50,
        trend_ema: int = 200,
        rsi_overbought: float = 55.0,
        rr_ratio: float = 2.0,
        atr_sl_mult: float = 1.5,
    ) -> None:
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.trend_ema = trend_ema
        self.rsi_overbought = rsi_overbought
        self.rr_ratio = rr_ratio
        self.atr_sl_mult = atr_sl_mult

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        req_len = max(self.trend_ema, self.slow_ema, 15) + 5
        if len(history) < req_len:
            return None

        curr_bar = history.iloc[-1]
        time_utc = curr_bar["time_utc"] if "time_utc" in curr_bar else curr_bar.name

        closes = history["close"]
        ema_trend = closes.ewm(span=self.trend_ema, adjust=False).mean().iloc[-1]
        ema_slow = closes.ewm(span=self.slow_ema, adjust=False).mean().iloc[-1]
        ema_fast = closes.ewm(span=self.fast_ema, adjust=False).mean().iloc[-1]

        # Faqat AYIQ trendida (Short-Only)
        curr_close = float(curr_bar["close"])
        if curr_close >= ema_trend:
            return None

        # RSI(14)
        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        # Pullback: Narx sekin EMA va tez EMA oralig'ida bo'lib, RSI sovigan (pullback)
        pullback_in_sell_zone = curr_close >= min(ema_fast, ema_slow) and rsi >= self.rsi_overbought

        if pullback_in_sell_zone:
            highs = history["high"].values
            lows = history["low"].values
            c_vals = history["close"].values
            tr = np.maximum(
                highs[1:] - lows[1:],
                np.maximum(np.abs(highs[1:] - c_vals[:-1]), np.abs(lows[1:] - c_vals[:-1])),
            )
            atr_14 = float(np.mean(tr[-14:])) if len(tr) >= 14 else 5.0

            sl_dist = max(self.atr_sl_mult * atr_14, 2.0)
            sl_price = round(curr_close + sl_dist, 3)
            tp_price = round(curr_close - (sl_dist * self.rr_ratio), 3)

            return Signal(
                time_utc=time_utc,
                action="SELL",
                sl=sl_price,
                tp=tp_price,
                comment="ShortOnlyPullback_SELL",
            )

        return None
