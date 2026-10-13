"""Gipoteza 6: Intraday Session Breakout No-Overnight (HYP-06).

Timeframe: H1.
Iqtisodiy mantiq:
Long swap (-$52.62/lot/kecha) xarajatidan to'liq qochish uchun barcha pozitsiyalar
20:00 UTC da (rollover 21:00 UTC oldidan) majburiy yopiladi. Hech qachon tungi
swap to'lanmaydi.

Qoidalar:
- Osiyo sessiyasi (00:00 - 07:00 UTC) High/Low aniqlanadi.
- 07:00 - 10:00 UTC oralig'ida yorilish bo'lsa kirish.
- SL: $1.5 * ATR(14), TP: $2.0 * SL masofasi.
- Chiqish: Agar bar soati >= 20 bo'lsa, pozitsiyani ushlab turish to'xtatiladi (time-exit).
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from python_brain.backtest.models import Signal
from python_brain.backtest.strategy_base import Strategy


class IntradayNoOvernightStrategy(Strategy):
    def __init__(
        self,
        asian_start_hour: int = 0,
        asian_end_hour: int = 7,
        entry_window_hours: int = 3,
        rr_ratio: float = 2.0,
        atr_sl_mult: float = 1.5,
    ) -> None:
        self.asian_start_hour = asian_start_hour
        self.asian_end_hour = asian_end_hour
        self.entry_window_hours = entry_window_hours
        self.rr_ratio = rr_ratio
        self.atr_sl_mult = atr_sl_mult

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        if len(history) < 25:
            return None

        curr_bar = history.iloc[-1]
        time_utc = curr_bar["time_utc"] if "time_utc" in curr_bar else curr_bar.name
        bar_dt = pd.to_datetime(time_utc)
        hour = bar_dt.hour

        # 20:00 UTC dan keyin yangi savdo umuman OCHILMAYDI (no-overnight)
        if hour >= 20:
            return None

        # Kirish faqat 07:00 dan 07:00 + entry_window_hours oralig'ida
        valid_entry_hours = list(range(self.asian_end_hour, self.asian_end_hour + self.entry_window_hours))
        if hour not in valid_entry_hours:
            return None

        # Bugungi Osiyo barlari (00:00 dan 07:00 gacha)
        hist = history.copy()
        if "time_utc" in hist.columns:
            hist["dt"] = pd.to_datetime(hist["time_utc"])
        else:
            hist["dt"] = pd.to_datetime(hist.index)

        today_date = bar_dt.date()
        asian_mask = (hist["dt"].dt.date == today_date) & (hist["dt"].dt.hour >= self.asian_start_hour) & (hist["dt"].dt.hour < self.asian_end_hour)
        asian_bars = hist[asian_mask]

        if len(asian_bars) < 3:
            return None

        asian_high = asian_bars["high"].max()
        asian_low = asian_bars["low"].min()

        # ATR(14)
        highs = history["high"].values
        lows = history["low"].values
        closes = history["close"].values
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])),
        )
        atr_14 = float(np.mean(tr[-14:])) if len(tr) >= 14 else 5.0

        close_price = float(curr_bar["close"])
        sl_dist = max(self.atr_sl_mult * atr_14, 2.0)

        if close_price > asian_high:
            sl_price = round(close_price - sl_dist, 3)
            tp_price = round(close_price + (sl_dist * self.rr_ratio), 3)
            return Signal(time_utc=time_utc, action="BUY", sl=sl_price, tp=tp_price, comment="IntradayBreakout_BUY")

        elif close_price < asian_low:
            sl_price = round(close_price + sl_dist, 3)
            tp_price = round(close_price - (sl_dist * self.rr_ratio), 3)
            return Signal(time_utc=time_utc, action="SELL", sl=sl_price, tp=tp_price, comment="IntradayBreakout_SELL")

        return None
