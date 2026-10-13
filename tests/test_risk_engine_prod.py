"""Production Risk Engine Testlari (1-Band).

Persistent SQLite holat, cooldown, kill-switch, kunlik limitlar va barcha himoyalarni tekshiradi.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from python_brain.backtest.models import AccountState, Signal
from python_brain.risk.gate import ProductionRiskGate
from python_brain.risk.live_guard import LiveGuard
from python_brain.risk.state_store import RiskStateStore


@pytest.fixture
def temp_db(tmp_path):
    return tmp_path / "test_risk_state.db"


def test_persistent_kill_switch_state(temp_db):
    """Kill-switch SQLite bazasida saqlanishi va keyingi chaqiruvda avtomatik rad etishi."""
    store = RiskStateStore(db_path=temp_db)
    gate = ProductionRiskGate(state_store=store, kill_switch_dd_pct=12.0)

    account = AccountState(
        initial_balance=10000.0,
        balance=8500.0,
        equity=8500.0,
        peak_equity=10000.0,
        max_equity_drawdown_pct=15.0,  # > 12.0%
    )
    sig = Signal(time_utc=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), action="BUY", sl=1980.0)

    # 1. Kill switch uriladi
    res = gate.check(sig, execution_price=2000.0, account=account)
    assert res.approved is False
    assert "MAX_EQUITY_DD_EXCEEDED" in res.rejection_reason

    # Bazada saqlanganini tekshirish
    state = store.load_state()
    assert state["kill_switch_active"] == 1

    # 2. Yangi gate instansi yaratilganda ham bazadan o'qib darhol rad etishi kerak
    gate_new = ProductionRiskGate(state_store=store, kill_switch_dd_pct=12.0)
    normal_account = AccountState(initial_balance=10000.0, balance=10000.0, equity=10000.0)
    res_persisted = gate_new.check(sig, execution_price=2000.0, account=normal_account)
    assert res_persisted.approved is False
    assert "KILL_SWITCH_ACTIVE_IN_DB" in res_persisted.rejection_reason

    # 3. Qo'lda tiklash
    reset_ok = store.reset_kill_switch(reset_reason="Audit tekshirildi va tasdiqlandi", force=True)
    assert reset_ok is True
    res_after_reset = gate_new.check(sig, execution_price=2000.0, account=normal_account)
    assert res_after_reset.approved is True


def test_consecutive_losses_cooldown(temp_db):
    """Ketma-ket 3 ta yo'qotishdan keyin cooldown faollashishi."""
    store = RiskStateStore(db_path=temp_db)
    gate = ProductionRiskGate(state_store=store, consecutive_losses_cooldown=3, cooldown_minutes=60)
    account = AccountState(initial_balance=10000.0, balance=9500.0, equity=9500.0)

    # 1 va 2 ta zarar
    gate.record_trade_closure(pnl=-50.0)
    gate.record_trade_closure(pnl=-50.0)
    sig = Signal(time_utc=datetime.now(timezone.utc), action="BUY", sl=1980.0)
    assert gate.check(sig, execution_price=2000.0, account=account).approved is True

    # 3-zarar -> Cooldown faollashadi!
    gate.record_trade_closure(pnl=-50.0)
    res_cooldown = gate.check(sig, execution_price=2000.0, account=account)
    assert res_cooldown.approved is False
    assert "IN_COOLDOWN_UNTIL" in res_cooldown.rejection_reason

    # G'alaba kelgach, cooldown nolga tushadi
    gate.record_trade_closure(pnl=100.0)
    assert gate.check(sig, execution_price=2000.0, account=account).approved is True


def test_friday_weekend_close_rule(temp_db):
    """Juma kuni 20:00 UTC dan keyin yangi savdo bloklanishi."""
    store = RiskStateStore(db_path=temp_db)
    gate = ProductionRiskGate(state_store=store, friday_close_hour_utc=20)
    account = AccountState(initial_balance=10000.0, balance=10000.0, equity=10000.0)

    # Juma soat 20:30 UTC (2026-03-13 is Friday)
    friday_night = datetime(2026, 3, 13, 20, 30, tzinfo=timezone.utc)
    sig = Signal(time_utc=friday_night, action="BUY", sl=1980.0)

    res = gate.check(sig, execution_price=2000.0, account=account)
    assert res.approved is False
    assert "FRIDAY_WEEKEND_CLOSE_RULE" in res.rejection_reason


def test_live_spread_filter(temp_db):
    """Jonli spread belgilangan limitdan (40 pts) katta bo'lsa rad etilishi."""
    store = RiskStateStore(db_path=temp_db)
    gate = ProductionRiskGate(state_store=store, max_spread_points=40.0)
    account = AccountState(initial_balance=10000.0, balance=10000.0, equity=10000.0)
    sig = Signal(time_utc=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), action="BUY", sl=1980.0)

    # 55.0 pts spread (> 40.0 pts)
    res = gate.check(sig, execution_price=2000.0, account=account, current_spread_pts=55.0)
    assert res.approved is False
    assert "SPREAD_TOO_HIGH" in res.rejection_reason

    # 25.0 pts spread (xavfsiz)
    res_ok = gate.check(sig, execution_price=2000.0, account=account, current_spread_pts=25.0)
    assert res_ok.approved is True
