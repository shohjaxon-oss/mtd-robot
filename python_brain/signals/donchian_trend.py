"""Gipoteza 5: Donchian Kanal Breakout Trend-Following (HYP-05).

Timeframe: H4 (yoki D1).
Iqtisodiy mantiq:
Oltin bozorida uzoq muddatli makro trendlar mavjud. Donchian kanali (20 va 55 bar)
orqali yangi N-bar ekstremumlariga (High/Low) kirish klassik "Turtle Trading" qoidasi.
Katta timeframe'da (H4) spread xarajati ($0.24) harakatning kichik foizini tashkil qiladi.

Qoidalar:
- BUY: Close > Donchian_High(lookback_entry)
- SELL: Close < Donchian_Low(lookback_entry)
- Chiqish: Donchian_Low(lookback_exit) ga tekkanda yoki ATR asosli Trailing Stop.
- Majburiy Stop Loss: entry_price - (atr_sl_mult * ATR(14)).
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from python_brain.backtest.models import Signal
from python_brain.backtest.strategy_base import Strategy


class DonchianTrendStrategy(Strategy):
    def __init__(
        self,
        entry_period: int = 20,
        exit_period: int = 10,
        atr_sl_mult: float = 2.0,
        rr_ratio: float = 3.0,
    ) -> None:
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.atr_sl_mult = atr_sl_mult
        self.rr_ratio = rr_ratio

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        req_bars = max(self.entry_period, self.exit_period, 15) + 2
        if len(history) < req_bars:
            return None

        # Faqat yopilgan barlar (oxirgi bar history.iloc[-1])
        curr_bar = history.iloc[-1]
        time_utc = curr_bar["time_utc"] if "time_utc" in curr_bar else curr_bar.name

        # Oldingi barlardan Donchian kanallari (Zero-lookahead: joriy bardan oldingi barlar!)
        past_bars = history.iloc[:-1]
        entry_window = past_bars.iloc[-self.entry_period:]
        highest_high = entry_window["high"].max()
        lowest_low = entry_window["low"].min()

        # ATR(14)
        highs = history["high"].values
        lows = history["low"].values
        closes = history["close"].values
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])),
        )
        atr_14 = float(np.mean(tr[-14:])) if len(tr) >= 14 else 10.0

        close_price = float(curr_bar["close"])

        # Signal shakllantirish
        if close_price > highest_high:
            sl_dist = max(self.atr_sl_mult * atr_14, 3.0)
            sl_price = round(close_price - sl_dist, 3)
            tp_price = round(close_price + (sl_dist * self.rr_ratio), 3)
            return Signal(
                time_utc=time_utc,
                action="BUY",
                sl=sl_price,
                tp=tp_price,
                comment=f"DonchianBreakout_BUY_{self.entry_period}",
            )

        elif close_price < lowest_low:
            sl_dist = max(self.atr_sl_mult * atr_14, 3.0)
            sl_price = round(close_price + sl_dist, 3)
            tp_price = round(close_price - (sl_dist * self.rr_ratio), 3)
            return Signal(
                time_utc=time_utc,
                action="SELL",
                sl=sl_price,
                tp=tp_price,
                comment=f"DonchianBreakout_SELL_{self.entry_period}",
            )

        return None
