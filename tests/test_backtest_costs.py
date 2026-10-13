"""Xarajatlar modeli (CostModel) unit testlari."""

from datetime import datetime, timezone
import pytest

from python_brain.backtest.costs import CostModel


def test_spread_hourly_profile():
    cost_model = CostModel(base_spread_points=240.0, point=0.001)

    # 1. Tinch soat (masalan UTC 14:00)
    t_normal = datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc)
    spread_pts_normal, spread_price_normal = cost_model.get_effective_spread(t_normal)
    assert spread_pts_normal > 0
    assert spread_price_normal == spread_pts_normal * 0.001

    # 2. Rollover soati (UTC 22:00)
    t_rollover = datetime(2026, 3, 10, 22, 15, tzinfo=timezone.utc)
    spread_pts_rollover, _ = cost_model.get_effective_spread(t_rollover)
    # Rollover payti spread kengayishi (agar profil bo'lsa yoki p95)
    assert spread_pts_rollover >= spread_pts_normal


def test_slippage_model():
    cost_model = CostModel()

    # Limit / TP order slippage = 0
    slip_limit = cost_model.get_slippage_penalty("BUY", is_stop_order=False, spread_price=0.24, local_atr=1.5)
    assert slip_limit == 0.0

    # Stop order (Stop Loss / Stop Entry) slippage > 0
    slip_stop = cost_model.get_slippage_penalty("BUY", is_stop_order=True, spread_price=0.24, local_atr=1.5)
    assert slip_stop > 0.0
    # Formula: 0.20 * spread + 0.05 * atr = 0.20 * 0.24 + 0.05 * 1.5 = 0.048 + 0.075 = 0.123
    expected = 0.20 * 0.24 + 0.05 * 1.5
    assert pytest.approx(slip_stop, rel=1e-3) == expected


def test_swap_calculation_and_triple_swap():
    cost_model = CostModel(
        swap_long_usd_per_lot=-52.33,
        swap_short_usd_per_lot=0.0,
        triple_swap_weekday=3,  # Thursday
    )

    # 1. Dushanbadan Seshanbaga o'tish (Weekday 0 = Monday, 1x swap)
    t_mon = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
    swap_long_1x = cost_model.calculate_swap(side="BUY", volume=1.0, rollover_time=t_mon)
    assert swap_long_1x == -52.33

    # Short swap 0 (swap-free)
    swap_short = cost_model.calculate_swap(side="SELL", volume=1.0, rollover_time=t_mon)
    assert swap_short == 0.0

    # 2. Payshanbadan Jumaga o'tish (Weekday 3 = Thursday, 3x swap)
    t_thu = datetime(2026, 3, 12, 0, 0, tzinfo=timezone.utc)
    assert t_thu.weekday() == 3
    swap_long_3x = cost_model.calculate_swap(side="BUY", volume=1.0, rollover_time=t_thu)
    assert pytest.approx(swap_long_3x, rel=1e-3) == -52.33 * 3.0
