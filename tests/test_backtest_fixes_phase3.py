"""Engine integratsiya testlari (3/10 tuzatishlari: A1 - A9).

A1: Swap va komissiya bir marta hisoblanishi (balans o'zgarishi = gross P&L + (-2.62)).
A2: Rollover blackout ijro barining ochilish vaqtida (21:00-22:00 UTC).
A3: Gap bilan SL to'ldirish (min(SL, bar_open) - slippage).
A4: halt_on_kill_switch bayrog'i va kill-switch audit timestamp.
A8: Min lot majburlanganda 1.5x risk tolerance oshsa rad etish.
A9: News blackout paytida kirishni bloklash va spread kengayishi.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import pandas as pd
import pytest

from python_brain.backtest.costs import CostModel
from python_brain.backtest.engine import BacktestEngine
from python_brain.backtest.models import (
    AccountState,
    ExitReason,
    Order,
    OrderSide,
    Signal,
)
from python_brain.backtest.risk_gate import DefaultRiskGate, RiskGate
from python_brain.backtest.strategy_base import Strategy
from python_brain.news.calendar_loader import NewsCalendar


class ZeroCostModel(CostModel):
    """Faqat motor logikasini sof tekshirish uchun xarajatsiz model."""
    def __init__(self):
        super().__init__(base_spread_points=0.0, commission_per_lot=0.0, swap_long_usd_per_lot=0.0, swap_short_usd_per_lot=0.0)

    def get_effective_spread(self, time_utc, bar_spread=None, is_news_blackout=False):
        return 0.0, 0.0

    def get_slippage_penalty(self, order_side, is_stop_order, spread_price, local_atr=1.0):
        return 0.0

    def calculate_swap(self, side, volume, rollover_time):
        return 0.0


class SingleSignalStrategy(Strategy):
    """Bitta aniq qadamda signal beruvchi test strategiyasi."""
    def __init__(self, step_to_fire: int, signal: Signal) -> None:
        self.step_to_fire = step_to_fire
        self.signal = signal
        self.current_step = 0

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        step = self.current_step
        self.current_step += 1
        if step == self.step_to_fire:
            return self.signal
        return None


def _make_df(records: List[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df["time_utc"] = pd.to_datetime(df["time_utc"])
    return df


def test_a1_swap_single_accounting():
    """A1 Testi: 0.01 lot long, spread/slippage=0, 3 kecha (1+1+3 swap) ushlanib SL ga uriladi.

    Gross P&L = -$50.00.
    1 kecha (Mon): -$52.33 * 0.01 = -$0.5233
    2 kecha (Tue): -$52.33 * 0.01 = -$0.5233
    3 kecha (Thu triple): -$52.33 * 0.01 * 3 = -$1.5699
    Jami swap = -$2.6165 ≈ -$2.62 USD.
    To'g'ri hisob: Balans o'zgarishi = Gross P&L + Swap = -$50.00 + (-$2.62) = -$52.62 (±0.01).
    (Eski xato kodda: -$55.24 bo'lardi, chunki swap ikki marta ayrilgan).
    """
    # 2026-03-09 Dushanba (Monday) 10:00 da signal
    # Bar 0: Mon 10:00 -> Signal BUY
    # Bar 1: Mon 11:00 -> Entry at 2000.0, SL=1950.0
    # Bar 2: Tue 00:00 -> Swap 1 (-0.5233)
    # Bar 3: Wed 00:00 -> Swap 2 (-0.5233)
    # Bar 4: Thu 00:00 -> Swap 3 (Triple! -1.5699)
    # Bar 5: Thu 10:00 -> Low=1940.0 (SL ga uriladi at 1950.0, Gross PnL = -$50.00)
    records = [
        {"time_utc": datetime(2026, 3, 9, 10, 0, tzinfo=timezone.utc), "open": 2000.0, "high": 2002.0, "low": 1998.0, "close": 2000.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 9, 11, 0, tzinfo=timezone.utc), "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2001.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc), "open": 2001.0, "high": 2004.0, "low": 1999.0, "close": 2002.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 11, 0, 0, tzinfo=timezone.utc), "open": 2002.0, "high": 2003.0, "low": 1998.0, "close": 2000.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 12, 0, 0, tzinfo=timezone.utc), "open": 2000.0, "high": 2002.0, "low": 1995.0, "close": 1998.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc), "open": 1998.0, "high": 1999.0, "low": 1940.0, "close": 1945.0, "spread": 0.0},
    ]
    df = _make_df(records)

    sig = Signal(
        time_utc=df["time_utc"].iloc[0],
        action="BUY",
        sl=1950.0,
    )
    strat = SingleSignalStrategy(step_to_fire=0, signal=sig)

    class SwapOnlyCostModel(CostModel):
        def get_effective_spread(self, time_utc, bar_spread=None, is_news_blackout=False):
            return 0.0, 0.0
        def get_slippage_penalty(self, order_side, is_stop_order, spread_price, local_atr=1.0):
            return 0.0

    cost_model = SwapOnlyCostModel(
        base_spread_points=0.0,
        commission_per_lot=0.0,
        swap_long_usd_per_lot=-52.33,
        swap_short_usd_per_lot=0.0,
        triple_swap_weekday=3,  # Thursday
    )

    class FixedLotGate(RiskGate):
        def approve(self, signal: Signal, execution_price: float, account: AccountState, point: float = 0.001, contract_size: float = 100.0) -> Optional[Order]:
            return Order(order_id=1, symbol="XAUUSDm", side=OrderSide.BUY, volume=0.01, requested_price=execution_price, sl=signal.sl, tp=signal.tp, time_utc=signal.time_utc)

    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strat, risk_gate=FixedLotGate(), cost_model=cost_model)

    assert len(account.closed_positions) == 1
    pos = account.closed_positions[0]
    assert pos.exit_reason == ExitReason.STOP_LOSS
    assert pos.close_price == 1950.0

    # Gross P&L: (1950 - 2000) * 100 * 0.01 = -$50.00
    # Swap: -0.5233 - 0.5233 - 1.5699 = -2.6165
    balance_delta = round(account.balance - account.initial_balance, 2)
    expected_delta = round(-50.00 + pos.accumulated_swap, 2)

    # Qat'iy tekshiruv: Balans o'zgarishi = Gross PnL + Swap (-52.62)
    assert pytest.approx(balance_delta, abs=0.02) == expected_delta
    assert pytest.approx(balance_delta, abs=0.02) == -52.62


def test_a2_rollover_blackout_on_execution_bar():
    """A2 Testi: 20:00 da berilgan signal 21:00 barida ochilmasligi shart (Rollover blackout)."""
    records = [
        {"time_utc": datetime(2026, 3, 10, 20, 0, tzinfo=timezone.utc), "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2001.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 10, 21, 0, tzinfo=timezone.utc), "open": 2001.0, "high": 2006.0, "low": 1996.0, "close": 2002.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 10, 22, 0, tzinfo=timezone.utc), "open": 2002.0, "high": 2008.0, "low": 1998.0, "close": 2004.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 10, 23, 0, tzinfo=timezone.utc), "open": 2004.0, "high": 2010.0, "low": 2000.0, "close": 2005.0, "spread": 0.0},
    ]
    df = _make_df(records)

    # Signal 20:00 bari yopilishida berildi -> ijro vaqti 21:00 bo'lishi kerak edi
    sig = Signal(time_utc=df["time_utc"].iloc[0], action="BUY", sl=1980.0)
    strat = SingleSignalStrategy(step_to_fire=0, signal=sig)

    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strat, cost_model=ZeroCostModel())

    # 21:00 da blackout tufayli buyruq ochilmasligi kerak!
    assert len(account.open_positions) == 0
    assert len(account.closed_positions) == 0


def test_a3_gap_down_stop_loss_fill():
    """A3 Testi: Gap-down holatida Buy SL bar_open bo'yicha to'ldirilishi (min(SL, bar_open) - slip)."""
    records = [
        {"time_utc": datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), "open": 4000.0, "high": 4005.0, "low": 3998.0, "close": 4002.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc), "open": 4002.0, "high": 4010.0, "low": 3998.0, "close": 4005.0, "spread": 0.0},
        # Gap-down: bar 3950 da ochildi, vaholanki SL = 3995 edi!
        {"time_utc": datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc), "open": 3950.0, "high": 3955.0, "low": 3940.0, "close": 3945.0, "spread": 0.0},
    ]
    df = _make_df(records)

    sig = Signal(time_utc=df["time_utc"].iloc[0], action="BUY", sl=3995.0)
    strat = SingleSignalStrategy(step_to_fire=0, signal=sig)

    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strat, cost_model=ZeroCostModel())

    assert len(account.closed_positions) == 1
    pos = account.closed_positions[0]
    assert pos.exit_reason == ExitReason.STOP_LOSS
    # Gap-down tufayli fill 3995 emas, 3950 bo'lishi shart!
    assert pos.close_price <= 3950.0


def test_a4_kill_switch_flag_and_audit():
    """A4 Testi: halt_on_kill_switch=False bo'lganda savdo davom etadi, lekin timestamp qayd etiladi."""
    account = AccountState(
        initial_balance=10000.0,
        balance=8500.0,
        equity=8500.0,
        peak_equity=10000.0,
        max_equity_drawdown_pct=15.0,  # > 12.0%
    )
    sig = Signal(time_utc=datetime.now(timezone.utc), action="BUY", sl=1980.0)

    # 1. halt_on_kill_switch = False (Discovery rejimida buyruq o'tadi)
    gate_discovery = DefaultRiskGate(kill_switch_dd_pct=12.0, halt_on_kill_switch=False)
    order_ok = gate_discovery.approve(sig, execution_price=2000.0, account=account)
    assert order_ok is not None

    # 2. halt_on_kill_switch = True (Live/Risk rejimida bloklanadi)
    gate_live = DefaultRiskGate(kill_switch_dd_pct=12.0, halt_on_kill_switch=True)
    order_blocked = gate_live.approve(sig, execution_price=2000.0, account=account)
    assert order_blocked is None


def test_a8_min_lot_risk_tolerance_guard():
    """A8 Testi: Kichik balansda ($500) keng SL bilan majburiy min lot riski 1.5x dan oshsa rad etish."""
    gate = DefaultRiskGate(
        risk_per_trade_pct=0.5,             # 0.5% risk = $500 da $2.50
        max_risk_tolerance_multiplier=1.5,  # Max ruxsat etilgan risk = $2.50 * 1.5 = $3.75
        min_lot=0.01,
    )
    account = AccountState(initial_balance=500.0, balance=500.0, equity=500.0)

    # Kirish: 2000.0, SL: 1990.0 (Farq: $10.00).
    # 0.01 lotda zarar: 10 * 100 * 0.01 = $10.00 USD!
    # $10.00 > $3.75 (4x oshib ketdi!) -> Buyruq RAD ETILISHI SHART!
    sig = Signal(time_utc=datetime.now(timezone.utc), action="BUY", sl=1990.0)
    order = gate.approve(sig, execution_price=2000.0, account=account)
    assert order is None  # Rad etildi!


def test_a9_news_blackout_spread_and_entry_guard():
    """A9 Testi: Yangilik paytida yangi kirish bloklanishi va spread kengayishi."""
    event_time = datetime(2026, 3, 10, 12, 30, tzinfo=timezone.utc)
    calendar = NewsCalendar(high_impact_times=[event_time])

    records = [
        {"time_utc": datetime(2026, 3, 10, 12, 20, tzinfo=timezone.utc), "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2001.0, "spread": 200.0},
        # 12:30 da news blackout (±15 daqiqa ichida)
        {"time_utc": datetime(2026, 3, 10, 12, 30, tzinfo=timezone.utc), "open": 2001.0, "high": 2015.0, "low": 1990.0, "close": 2005.0, "spread": 200.0},
        {"time_utc": datetime(2026, 3, 10, 13, 0, tzinfo=timezone.utc), "open": 2005.0, "high": 2008.0, "low": 2002.0, "close": 2004.0, "spread": 200.0},
    ]
    df = _make_df(records)

    # 12:20 barida berilgan signal 12:30 da ijro bo'lmoqchi edi
    sig = Signal(time_utc=df["time_utc"].iloc[0], action="BUY", sl=1980.0)
    strat = SingleSignalStrategy(step_to_fire=0, signal=sig)

    engine = BacktestEngine(calendar=calendar, news_before_minutes=15, news_after_minutes=15)
    account = engine.run(df, strat)

    # 12:30 da News blackout tufayli buyruq bloklandi!
    assert len(account.open_positions) == 0
    assert len(account.closed_positions) == 0


def test_r2_1_stress_multiplier_passed_correctly():
    """R2-1 Testi: CostModel(stress_multiplier=1.5) berilsa, engine uni 1.0 ga qaytarib tashlamasligi."""
    records = [
        {"time_utc": datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2001.0, "spread": 200.0},
        {"time_utc": datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc), "open": 2001.0, "high": 2010.0, "low": 1998.0, "close": 2005.0, "spread": 200.0},
    ]
    df = _make_df(records)
    sig = Signal(time_utc=df["time_utc"].iloc[0], action="BUY", sl=1980.0)
    strat = SingleSignalStrategy(step_to_fire=0, signal=sig)

    cost_model = CostModel(stress_multiplier=1.5)
    engine = BacktestEngine(initial_balance=10000.0)
    # stress_multiplier uzatilmagan taqdirda ham cost_model ichidagi 1.5 saqlanadi
    account = engine.run(df, strat, cost_model=cost_model)

    assert cost_model.stress_multiplier == 1.5
    assert len(account.open_positions) == 1
    pos = account.open_positions[0]
    # 200.0 pts * 1.5 stress = 300.0 pts ($0.30)
    # Buy open_price = bar_open (2001.0) + spread_price (0.30) = 2001.30
    assert round(pos.open_price, 2) == 2001.30


def test_r2_3_ambiguous_exit_flag_detection():
    """R2-3 Testi: Bir barda ham SL, ham TP tekkanda is_ambiguous_exit bayrog'i rost bo'lishi."""
    records = [
        {"time_utc": datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), "open": 2000.0, "high": 2005.0, "low": 1995.0, "close": 2001.0, "spread": 0.0},
        {"time_utc": datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc), "open": 2001.0, "high": 2002.0, "low": 2000.0, "close": 2001.0, "spread": 0.0},
        # Katta volatillik: Low 1980 ga tushdi (SL=1990 ga tegdi), High 2030 ga chiqdi (TP=2020 ga tegdi)
        {"time_utc": datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc), "open": 2001.0, "high": 2030.0, "low": 1980.0, "close": 2010.0, "spread": 0.0},
    ]
    df = _make_df(records)
    sig = Signal(time_utc=df["time_utc"].iloc[0], action="BUY", sl=1990.0, tp=2020.0)
    strat = SingleSignalStrategy(step_to_fire=0, signal=sig)

    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strat, cost_model=ZeroCostModel())

    assert len(account.closed_positions) == 1
    pos = account.closed_positions[0]
    assert pos.exit_reason == ExitReason.STOP_LOSS  # SL-first qoidasi
    assert pos.is_ambiguous_exit is True            # Ikkilamchi bar deb belgilandi!

