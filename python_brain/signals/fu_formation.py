"""FU FORMATION Strategy (HYP-09 / ADR-0013).

Trader tomonidan belgilangan qat'iy deterministik qoidalar:
- Faqat yopilgan barlarda ishlaydi (Zero-Lookahead).
- Timeframe: FAQAT M1, M3, M5.
- Trend: FU shamdan oldin kamida 3 ta ketma-ket bir xil yo'nalishli sham.
- Engulfing yo'q: Trend shamlari bir-birini yutmagan bo'lishi kerak.
- FU sham (t):
    * SELL: Bearish, high_t > high_{t-1}, close_t < close_{t-1}.
    * BUY : Bullish, low_t < low_{t-1}, close_t > close_{t-1}.
- Entry: Keyingi sham ochilishida market order.
- SL: FU sham ekstremumidan hisoblanadi (high_t + 5 pip yoki low_t - 5 pip).
- 2 ta Leg (har biri 0.01 lot):
    * Leg A: TP = 20 pip.
    * Leg B: TP = 30 pip.
    * Leg A TP ga yetganda Leg B ning SL i Entry narxiga ko'chiriladi (Breakeven).
- Pip o'lchami: 1 pip = 0.10 USD (XAUUSDm da 100 punkt).
"""

from datetime import datetime
from typing import Optional, List
import pandas as pd

from python_brain.backtest.strategy_base import Strategy
from python_brain.backtest.models import Signal, SignalLeg


VALID_TIMEFRAMES = {"M1", "M3", "M5"}


class FUFormationStrategy(Strategy):
    """Trader tomonidan taqdim etilgan FU Formation strategiyasi."""

    def __init__(
        self,
        timeframe: str = "M5",
        min_trend_candles: int = 3,
        engulf_mode: str = "body",
        sl_buffer_pips: float = 5.0,
        tp1_pips: float = 20.0,
        tp2_pips: float = 30.0,
        lot_per_leg: float = 0.01,
        pip_size_price: float = 0.10,
        max_entry_delay_sec: int = 3,
    ):
        tf_clean = timeframe.upper().strip()
        if tf_clean not in VALID_TIMEFRAMES:
            raise ValueError(
                f"Noto'g'ri timeframe: '{timeframe}'. FU Formation strategiyasi "
                f"FAQAT {sorted(VALID_TIMEFRAMES)} timeframe'larida ishlashi mumkin!"
            )

        if engulf_mode not in {"body", "range"}:
            raise ValueError(f"Noto'g'ri engulf_mode: '{engulf_mode}'. Tanlov: 'body' yoki 'range'.")

        if min_trend_candles < 3:
            raise ValueError(f"min_trend_candles kamida 3 bo'lishi shart, berildi: {min_trend_candles}")

        self.timeframe = tf_clean
        self.min_trend_candles = min_trend_candles
        self.engulf_mode = engulf_mode
        self.sl_buffer_pips = sl_buffer_pips
        self.tp1_pips = tp1_pips
        self.tp2_pips = tp2_pips
        self.lot_per_leg = lot_per_leg
        self.pip_size_price = pip_size_price
        self.max_entry_delay_sec = max_entry_delay_sec

    def _is_engulfing(self, o_k: float, c_k: float, h_k: float, l_k: float,
                      o_prev: float, c_prev: float, h_prev: float, l_prev: float) -> bool:
        """k-sham k-1-shamni yutib yuborganini tekshiradi."""
        if self.engulf_mode == "body":
            min_k, max_k = min(o_k, c_k), max(o_k, c_k)
            min_prev, max_prev = min(o_prev, c_prev), max(o_prev, c_prev)
            return (min_k <= min_prev) and (max_k >= max_prev)
        else:  # range rejimi
            return (l_k <= l_prev) and (h_k >= h_prev)

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        """Yangi yopilgan barlarda FU formation signalini tekshiradi."""
        required_bars = self.min_trend_candles + 1  # Trend shamlari + FU sham
        if history is None or len(history) < required_bars:
            return None

        # Oxirgi kerakli shamlarni ajratib olish
        recent = history.iloc[-required_bars:]
        opens = recent["open"].values
        highs = recent["high"].values
        lows = recent["low"].values
        closes = recent["close"].values
        bar_time = recent["time_utc"].iloc[-1]

        # t = oxirgi sham (FU nomzod)
        fu_open = float(opens[-1])
        fu_high = float(highs[-1])
        fu_low = float(lows[-1])
        fu_close = float(closes[-1])

        # t-1 = FU dan oldingi oxirgi trend sham
        prev_open = float(opens[-2])
        prev_high = float(highs[-2])
        prev_low = float(lows[-2])
        prev_close = float(closes[-2])

        # -------------------------------------------------------------
        # 1. SELL SETUP TEKSHIRUVI
        # -------------------------------------------------------------
        # 1.1 FU sham bearish bo'lishi shart (close < open)
        is_fu_bearish = fu_close < fu_open

        if is_fu_bearish:
            # 1.2 Trend tekshiruvi: FU dan oldingi barcha trend shamlari BULLISH bo'lishi shart
            # Doji (close == open) yoki bearish (close < open) bo'lsa rad
            all_bullish = True
            for i in range(self.min_trend_candles):
                idx = -2 - i
                if closes[idx] <= opens[idx]:
                    all_bullish = False
                    break

            if all_bullish:
                # 1.3 Engulfing yo'q tekshiruvi: qo'shni trend shamlari bir-birini yutmasligi kerak
                has_engulfing = False
                for i in range(self.min_trend_candles - 1):
                    # k juftlik: k vs k-1
                    # misol: min=3 bo'lsa, idx_k=-2 (t-1) vs idx_prev=-3 (t-2), va idx_k=-3 (t-2) vs idx_prev=-4 (t-3)
                    idx_k = -2 - i
                    idx_prev = idx_k - 1
                    if self._is_engulfing(
                        opens[idx_k], closes[idx_k], highs[idx_k], lows[idx_k],
                        opens[idx_prev], closes[idx_prev], highs[idx_prev], lows[idx_prev]
                    ):
                        has_engulfing = True
                        break

                if not has_engulfing:
                    # 1.4 FU sham shartlari:
                    # - high_t > high_{t-1} (qat'iy)
                    # - close_t < close_{t-1}
                    if (fu_high > prev_high) and (fu_close < prev_close):
                        # SELL SETUP TASDIQLANDI
                        sl_price = round(fu_high + (self.sl_buffer_pips * self.pip_size_price), 3)

                        legs = [
                            SignalLeg(leg_id="A", volume=self.lot_per_leg, tp_pips=self.tp1_pips, comment="FU_LEG_A"),
                            SignalLeg(leg_id="B", volume=self.lot_per_leg, tp_pips=self.tp2_pips, comment="FU_LEG_B"),
                        ]

                        return Signal(
                            time_utc=bar_time,
                            action="SELL",
                            sl=sl_price,
                            legs=legs,
                            breakeven_on_first_tp=True,
                            pip_size_price=self.pip_size_price,
                            comment=f"FU_SELL_{self.timeframe}",
                        )

        # -------------------------------------------------------------
        # 2. BUY SETUP TEKSHIRUVI (Ko'zgudagi aksi)
        # -------------------------------------------------------------
        # 2.1 FU sham bullish bo'lishi shart (close > open)
        is_fu_bullish = fu_close > fu_open

        if is_fu_bullish:
            # 2.2 Trend tekshiruvi: FU dan oldingi barcha trend shamlari BEARISH bo'lishi shart
            all_bearish = True
            for i in range(self.min_trend_candles):
                idx = -2 - i
                if closes[idx] >= opens[idx]:
                    all_bearish = False
                    break

            if all_bearish:
                # 2.3 Engulfing yo'q tekshiruvi
                has_engulfing = False
                for i in range(self.min_trend_candles - 1):
                    idx_k = -2 - i
                    idx_prev = idx_k - 1
                    if self._is_engulfing(
                        opens[idx_k], closes[idx_k], highs[idx_k], lows[idx_k],
                        opens[idx_prev], closes[idx_prev], highs[idx_prev], lows[idx_prev]
                    ):
                        has_engulfing = True
                        break

                if not has_engulfing:
                    # 2.4 FU sham shartlari:
                    # - low_t < low_{t-1} (qat'iy)
                    # - close_t > close_{t-1}
                    if (fu_low < prev_low) and (fu_close > prev_close):
                        # BUY SETUP TASDIQLANDI
                        sl_price = round(fu_low - (self.sl_buffer_pips * self.pip_size_price), 3)

                        legs = [
                            SignalLeg(leg_id="A", volume=self.lot_per_leg, tp_pips=self.tp1_pips, comment="FU_LEG_A"),
                            SignalLeg(leg_id="B", volume=self.lot_per_leg, tp_pips=self.tp2_pips, comment="FU_LEG_B"),
                        ]

                        return Signal(
                            time_utc=bar_time,
                            action="BUY",
                            sl=sl_price,
                            legs=legs,
                            breakeven_on_first_tp=True,
                            pip_size_price=self.pip_size_price,
                            comment=f"FU_BUY_{self.timeframe}",
                        )

        return None
