"""Test strict configuration wiring to ProductionRiskGate and Settings."""

import pytest
from pydantic import ValidationError

from python_brain.config_loader import load_all_configs, StrategySettingsConfig
from python_brain.risk.gate import ProductionRiskGate
from python_brain.risk.live_guard import LiveTradingBlockedError
from python_brain.backtest.models import AccountState, Signal, SignalLeg
from datetime import datetime, timezone


class MockAccountInfo:
    def __init__(self, login=123456, trade_mode=0, server="MetaQuotes-Demo"):
        self.login = login
        self.trade_mode = trade_mode  # 0 = DEMO, 2 = REAL
        self.server = server
        self.balance = 10000.0


def test_config_wiring_exact_values():
    """Verify all values in config/risk.yaml are wired 1-to-1 without silent fallbacks."""
    configs = load_all_configs()

    # Settings verification
    assert configs.settings.strategy.timeframe == "M3"
    assert configs.settings.strategy.name == "fu_formation"

    # Risk gate initialization with config
    gate = ProductionRiskGate(risk_config=configs.risk)

    assert gate.risk_per_trade_pct == 0.5
    assert gate.daily_loss_limit_pct == 2.0
    assert gate.weekly_loss_limit_pct == 4.0
    assert gate.kill_switch_dd_pct == 12.0
    assert gate.max_daily_trades == 5
    assert gate.consecutive_losses_cooldown == 3
    assert gate.cooldown_minutes == 60
    assert gate.max_spread_points == 450.0

    # FU formation profile
    assert gate.max_setup_risk_usd == 25.0
    assert gate.fixed_lot_per_leg == 0.01
    assert gate.max_open_setups == 1
    assert gate.be_offset_pips == 0.0


def test_demo_data_collection_profile_wiring():
    """Verify demo_data_collection profile overrides max_daily_trades and cooldown."""
    configs = load_all_configs()
    gate = ProductionRiskGate(risk_config=configs.risk, demo_profile=True)

    assert gate.max_daily_trades == 30
    assert gate.consecutive_losses_cooldown == 999999
    assert gate.cooldown_minutes == 0
    # Core capital protection remains active
    assert gate.daily_loss_limit_pct == 2.0
    assert gate.kill_switch_dd_pct == 12.0


def test_demo_profile_blocked_on_real_account():
    """Verify demo profile raises LiveTradingBlockedError on REAL accounts."""
    configs = load_all_configs()
    gate = ProductionRiskGate(risk_config=configs.risk, demo_profile=True)

    real_acc = MockAccountInfo(login=999999, trade_mode=2, server="Exness-Real")
    account_state = AccountState(
        initial_balance=10000.0,
        equity=10000.0,
        balance=10000.0,
        free_margin=10000.0,
        leverage=100,
    )
    sig = Signal(
        time_utc=datetime.now(timezone.utc),
        action="BUY",
        sl=2640.0,
        legs=[SignalLeg(leg_id="A", volume=0.01, tp_pips=20.0)],
    )

    with pytest.raises(LiveTradingBlockedError):
        gate.evaluate(
            signal=sig,
            account=account_state,
            current_spread_pts=200.0,
            raw_account_info=real_acc,
            execution_price=2645.0,
        )


def test_strategy_timeframe_strictly_m3():
    """Verify that any timeframe other than M3 fails pydantic validation."""
    with pytest.raises(ValidationError):
        StrategySettingsConfig(timeframe="M1")

    with pytest.raises(ValidationError):
        StrategySettingsConfig(timeframe="M5")

    # M3 must succeed
    valid_strat = StrategySettingsConfig(timeframe="M3")
    assert valid_strat.timeframe == "M3"
