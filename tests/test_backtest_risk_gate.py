"""RiskGate va xavfsizlik filtrlari testlari."""

from datetime import datetime, timezone
import pytest

from python_brain.backtest.models import AccountState, OrderSide, Signal
from python_brain.backtest.risk_gate import DefaultRiskGate


def test_mandatory_stop_loss_enforcement():
    gate = DefaultRiskGate(risk_per_trade_pct=0.5, require_stop_loss=True)
    account = AccountState(initial_balance=10000.0, balance=10000.0, equity=10000.0)

    # 1. SL yo'q signal (Taqiqlangan!)
    sig_no_sl = Signal(
        time_utc=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        action="BUY",
        sl=None,
        tp=2010.0,
    )
    approved = gate.approve(sig_no_sl, execution_price=2000.0, account=account)
    assert approved is None

    # 2. SL = 0 bo'lgan signal (Taqiqlangan!)
    sig_zero_sl = Signal(
        time_utc=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        action="BUY",
        sl=0.0,
    )
    approved = gate.approve(sig_zero_sl, execution_price=2000.0, account=account)
    assert approved is None


def test_position_sizing_calculation():
    gate = DefaultRiskGate(risk_per_trade_pct=0.5)  # 0.5% risk
    account = AccountState(initial_balance=10000.0, balance=10000.0, equity=10000.0, free_margin=10000.0)

    # Balans: $10,000. 0.5% risk = $50.00.
    # Kirish narxi: 2000.0, SL: 1990.0 (Farq: 10.0 USD).
    # 1 lotda zarar: 10.0 * 100 oz = $1,000.
    # Lot: 50.0 / 1000 = 0.05 lot bo'lishi shart.
    sig = Signal(
        time_utc=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        action="BUY",
        sl=1990.0,
        tp=2020.0,
    )
    order = gate.approve(sig, execution_price=2000.0, account=account, contract_size=100.0)
    assert order is not None
    assert order.side == OrderSide.BUY
    assert pytest.approx(order.volume, rel=1e-2) == 0.05


def test_daily_loss_limit_block():
    gate = DefaultRiskGate(max_daily_loss_pct=2.0)
    # Boshlang'ich balans $10,000. Bugungi realized zarar -$250 (2.5% > 2.0%)
    account = AccountState(
        initial_balance=10000.0,
        balance=9750.0,
        equity=9750.0,
        daily_realized_pnl=-250.0,
    )
    sig = Signal(
        time_utc=datetime(2026, 3, 10, 14, 0, tzinfo=timezone.utc),
        action="BUY",
        sl=1990.0,
    )
    order = gate.approve(sig, execution_price=2000.0, account=account)
    assert order is None  # Bloklandi!


def test_kill_switch_max_drawdown():
    gate = DefaultRiskGate(kill_switch_dd_pct=12.0)
    # Max DD = 13.0% (> 12.0%)
    account = AccountState(
        initial_balance=10000.0,
        balance=8700.0,
        equity=8700.0,
        max_equity_drawdown_pct=13.0,
    )
    sig = Signal(
        time_utc=datetime(2026, 3, 10, 14, 0, tzinfo=timezone.utc),
        action="BUY",
        sl=1990.0,
    )
    order = gate.approve(sig, execution_price=2000.0, account=account)
    assert order is None  # Kill-switch ishladi!
