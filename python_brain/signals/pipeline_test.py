"""FOYDA UCHUN EMAS, FAQAT QUVUR SINOVI (PIPELINE TEST ONLY)!

DIQQAT:
Ushbu strategiya HISOBLARDA FOYDA OLISH UCHUN EMAS.
Yagona vazifasi: Python Brain -> Risk Gate -> Broker Execution -> MT5
infratuzilmasi zanjirining texnik to'g'ri ishlashini (quvur o'tkazuvchanligini) tekshirish.

Bu strategiya hech qachon REAL hisobda ishlamasligi uchun Live Guard va
allow_live=False qat'iy nazoratida turadi.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from python_brain.backtest.strategy_base import Strategy
from python_brain.backtest.models import Signal
from python_brain.risk.live_guard import LiveTradingBlockedError


class PipelineTestStrategy(Strategy):
    """Faqat infratuzilma va quvur sinovi uchun mo'ljallangan test strategiyasi."""

    def __init__(
        self,
        target_hour_utc: int = 10,
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
        tp_atr_mult: float = 2.0,
        config: Optional[Dict[str, Any]] = None,
    ):
        # 1. LIVE GUARD XAVFSIZLIK NAZORATI:
        # Hech qanday holatda real hisobda ruxsat berilmasin
        if config:
            allow_live = config.get("safety", {}).get("allow_live", False)
            if allow_live:
                raise LiveTradingBlockedError(
                    "PipelineTestStrategy HECH QACHON real hisobda (allow_live=True) ishlay olmaydi!"
                )

        self.target_hour_utc = target_hour_utc
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.last_traded_date: Optional[str] = None

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        """Yangi bar yopilganda quvur sinovi uchun signal qaytaradi."""
        if history is None or len(history) < self.atr_period + 2:
            return None

        last_row = history.iloc[-1]
        time_utc = last_row["time_utc"]
        if isinstance(time_utc, str):
            time_utc = pd.to_datetime(time_utc)

        current_date_str = time_utc.strftime("%Y-%m-%d")

        # Kuniga faqat bir marta, belgilangan soatda (target_hour_utc) sinov savdosi
        if time_utc.hour == self.target_hour_utc and self.last_traded_date != current_date_str:
            # ATR hisoblash
            high = history["high"].values
            low = history["low"].values
            close = history["close"].values

            tr1 = high[-self.atr_period:] - low[-self.atr_period:]
            tr2 = np.abs(high[-self.atr_period:] - close[-self.atr_period - 1:-1])
            tr3 = np.abs(low[-self.atr_period:] - close[-self.atr_period - 1:-1])
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr = float(np.mean(tr))
            if atr <= 0:
                atr = 1.0  # Fallback for gold

            current_close = float(close[-1])
            sl = round(current_close - (self.sl_atr_mult * atr), 2)
            tp = round(current_close + (self.tp_atr_mult * atr), 2)

            self.last_traded_date = current_date_str

            return Signal(
                time_utc=time_utc,
                action="BUY",
                sl=sl,
                tp=tp,
                comment="PIPE_TEST_01",
            )

        return None
