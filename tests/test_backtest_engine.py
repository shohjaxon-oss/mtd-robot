"""Backtest Engine ishonchlilik testlari.

- Zero lookahead (Signal bar t close -> Execution bar t+1 open)
- Intrabar SL vs TP konservativ qoida (SL birinchi)
- Determinizm (Aynan bir xil natija)
- Xarajatlar va aniq narx ijrosi
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import numpy as np
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


class ZeroCostModel(CostModel):
    """Nol xarajatli test modeli."""
    def __init__(self):
        super().__init__(base_spread_points=0.0, commission_per_lot=0.0, swap_long_usd_per_lot=0.0, swap_short_usd_per_lot=0.0)

    def get_effective_spread(self, time_utc, bar_spread=None, is_news_blackout=False):
        return 0.0, 0.0

    def get_slippage_penalty(self, order_side, is_stop_order, spread_price, local_atr=1.0):
        return 0.0

    def calculate_swap(self, side, volume, rollover_time):
        return 0.0


class PermissiveRiskGate(RiskGate):
    """Fixed volume (0.1 lot) tasdiqlovchi oddiy gate."""
    def approve(self, signal: Signal, execution_price: float, account: AccountState, point: float = 0.001, contract_size: float = 100.0) -> Optional[Order]:
        side = OrderSide.BUY if signal.action == "BUY" else OrderSide.SELL
        return Order(
            order_id=1,
            symbol="XAUUSDm",
            side=side,
            volume=0.1,
            requested_price=execution_price,
            sl=signal.sl or 0.0,
            tp=signal.tp,
            time_utc=signal.time_utc,
            comment=signal.comment,
        )


class FixedStepSignalStrategy(Strategy):
    """Oldindan belgilangan qadamda bitta signal beruvchi test strategiyasi."""
    def __init__(self, target_step: int, signal: Signal) -> None:
        self.target_step = target_step
        self.signal = signal
        self.current_step = 0

    def on_bar(self, history: pd.DataFrame) -> Optional[Signal]:
        step = self.current_step
        self.current_step += 1
        if step == self.target_step:
            return self.signal
        return None


def _make_bars_df(bars_tuples) -> pd.DataFrame:
    base_t = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    records = []
    for i, (o, h, l, c) in enumerate(bars_tuples):
        t = base_t + timedelta(hours=i)
        records.append({
            "time_utc": t,
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "spread": 0.0,
        })
    return pd.DataFrame(records)


def test_zero_lookahead_execution():
    """Bar 0 yopilishida berilgan signal Bar 1 OPEN narxida ochilishi shart."""
    bars = [
        (2000.0, 2005.0, 1995.0, 2002.0),  # Bar 0 -> Signal BUY
        (2006.0, 2015.0, 2004.0, 2012.0),  # Bar 1 -> OPEN 2006.0 da ochiladi
        (2012.0, 2025.0, 2010.0, 2022.0),  # Bar 2 -> TP (2020.0) ga yetib yopiladi
    ]
    df = _make_bars_df(bars)

    sig = Signal(
        time_utc=df["time_utc"].iloc[0],
        action="BUY",
        sl=1990.0,
        tp=2020.0,
    )
    strat = FixedStepSignalStrategy(target_step=0, signal=sig)
    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strat, risk_gate=PermissiveRiskGate(), cost_model=ZeroCostModel())

    assert len(account.closed_positions) == 1
    pos = account.closed_positions[0]

    # Bar 0 Close (2002.0) da EMAS, Bar 1 Open (2006.0) da ochilishi shart!
    assert pos.open_price == 2006.0
    assert pos.open_time_utc == df["time_utc"].iloc[1]
    assert pos.close_price == 2020.0
    assert pos.exit_reason == ExitReason.TAKE_PROFIT


def test_intrabar_conservative_sl_tp():
    """Bitta bar ichida ham High >= TP, ham Low <= SL bo'lsa, konservativ qoida bo'yicha SL birinchi ishlashi shart."""
    bars = [
        (2000.0, 2002.0, 1998.0, 2000.0),  # Bar 0 -> Signal BUY
        (2000.0, 2030.0, 1970.0, 2010.0),  # Bar 1 -> High 2030 >= TP(2020), Low 1970 <= SL(1980) !
    ]
    df = _make_bars_df(bars)

    sig = Signal(
        time_utc=df["time_utc"].iloc[0],
        action="BUY",
        sl=1980.0,
        tp=2020.0,
    )
    strat = FixedStepSignalStrategy(target_step=0, signal=sig)
    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strat, risk_gate=PermissiveRiskGate(), cost_model=ZeroCostModel())

    assert len(account.closed_positions) == 1
    pos = account.closed_positions[0]

    # Konservativ printsip: SL birinchi!
    assert pos.exit_reason == ExitReason.STOP_LOSS
    assert pos.close_price <= 1980.0
    assert pos.realized_pnl < 0.0


def test_backtest_determinism():
    """Aynan bir xil ma'lumot va strategiya bilan ikki marta yurgizilganda 100% bir xil natija chiqishi shart."""
    np.random.seed(42)
    p = 2000.0
    bars = []
    for _ in range(50):
        o = p
        h = o + 2.0
        l = o - 2.0
        c = o + 0.5
        bars.append((o, h, l, c))
        p = c
    df = _make_bars_df(bars)

    sig = Signal(
        time_utc=df["time_utc"].iloc[0],
        action="BUY",
        sl=1990.0,
        tp=2020.0,
    )

    strat1 = FixedStepSignalStrategy(target_step=2, signal=sig)
    engine1 = BacktestEngine()
    acc1 = engine1.run(df, strat1, risk_gate=PermissiveRiskGate(), cost_model=ZeroCostModel())

    strat2 = FixedStepSignalStrategy(target_step=2, signal=sig)
    engine2 = BacktestEngine()
    acc2 = engine2.run(df, strat2, risk_gate=PermissiveRiskGate(), cost_model=ZeroCostModel())

    assert len(acc1.closed_positions) == len(acc2.closed_positions)
    assert acc1.balance == acc2.balance
    assert acc1.equity == acc2.equity
