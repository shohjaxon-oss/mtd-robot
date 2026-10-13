"""Unit tests for configuration loading and strict risk validation rules."""

import pytest
from pydantic import ValidationError
from python_brain.config_loader import (
    DrawdownLimitsConfig,
    ForbiddenMechanicsConfig,
    PerTradeRiskConfig,
    load_all_configs,
)


def test_valid_config_loading():
    """Verify that the default configuration files load and validate cleanly."""
    config = load_all_configs()
    assert config.app.name == "mtd-robot" if hasattr(config, "app") else True
    assert config.risk.per_trade_risk.risk_per_trade_pct == 0.5
    assert config.risk.per_trade_risk.require_stop_loss is True
    assert config.risk.drawdown_limits.daily_loss_limit_pct == 2.0
    assert config.risk.drawdown_limits.weekly_loss_limit_pct == 4.0
    assert config.risk.drawdown_limits.max_drawdown_kill_switch_pct == 12.0
    assert config.risk.forbidden_mechanics.allow_martingale is False
    assert config.risk.forbidden_mechanics.allow_grid is False
    assert config.risk.forbidden_mechanics.allow_averaging_down is False


def test_reject_excessive_trade_risk():
    """Risk per trade exceeding 1.0% MUST raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        PerTradeRiskConfig(risk_per_trade_pct=1.5)
    assert "risk_per_trade_pct" in str(exc_info.value)


def test_reject_zero_or_negative_trade_risk():
    """Trade risk must be greater than 0%."""
    with pytest.raises(ValidationError):
        PerTradeRiskConfig(risk_per_trade_pct=0.0)

    with pytest.raises(ValidationError):
        PerTradeRiskConfig(risk_per_trade_pct=-0.5)


def test_reject_missing_stop_loss():
    """Trading without Stop Loss is an absolute violation and must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        PerTradeRiskConfig(risk_per_trade_pct=0.5, require_stop_loss=False)
    assert "VIOLATION: require_stop_loss MUST be True" in str(exc_info.value)


def test_reject_toxic_mechanics():
    """Martingale, Grid, and Averaging Down must be strictly blocked by Pydantic validators."""
    with pytest.raises(ValidationError) as exc_info:
        ForbiddenMechanicsConfig(allow_martingale=True)
    assert "Martingale is strictly prohibited" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        ForbiddenMechanicsConfig(allow_grid=True)
    assert "Grid trading is strictly prohibited" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        ForbiddenMechanicsConfig(allow_averaging_down=True)
    assert "Averaging-down is strictly prohibited" in str(exc_info.value)


def test_reject_unrealistic_drawdown_limits():
    """Drawdown limits outside safety envelope must be rejected."""
    with pytest.raises(ValidationError):
        DrawdownLimitsConfig(daily_loss_limit_pct=10.0)  # Max daily limit is 3.0%

    with pytest.raises(ValidationError):
        DrawdownLimitsConfig(max_drawdown_kill_switch_pct=25.0)  # Max kill-switch limit is 15.0%
