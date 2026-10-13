"""Holdout, Monte Carlo va Walk-Forward modullari testlari."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import pytest

from python_brain.backtest.holdout import HoldoutManager
from python_brain.backtest.models import ExitReason, OrderSide, Position
from python_brain.backtest.montecarlo import MonteCarloEngine
from python_brain.backtest.walkforward import WalkForwardSplitter


def _create_sample_df_days(days: int = 1000) -> pd.DataFrame:
    base_time = datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(days):
        records.append({
            "time_utc": base_time + timedelta(days=i),
            "open": 2000.0,
            "high": 2010.0,
            "low": 1990.0,
            "close": 2005.0,
        })
    return pd.DataFrame(records)


def test_holdout_manager_locking(tmp_path: Path):
    test_log = tmp_path / "holdout_log.md"
    hm = HoldoutManager(log_path=test_log)
    df = _create_sample_df_days(100)

    # 1. Standart rejimda (allow_holdout=False): Holdout berilmaydi
    train_df, holdout_df = hm.split(df, timeframe="H1", allow_holdout=False)
    assert len(train_df) == 80
    assert holdout_df is None

    # 2. To'g'ridan-to'g'ri holdout so'ralsa PermissionError chiqishi kerak
    with pytest.raises(PermissionError):
        hm.get_holdout_data(df, timeframe="H1", allow_holdout=False, reason="Dev test")

    # 3. allow_holdout=True bilan ochilganda
    _, holdout_df = hm.split(df, timeframe="H1", allow_holdout=True, reason="Final Test")
    assert holdout_df is not None
    assert len(holdout_df) == 20

    # 4. Audit log yozilganini tekshirish
    assert test_log.exists()
    content = test_log.read_text(encoding="utf-8")
    assert "Final Test" in content
    assert "H1" in content


def test_monte_carlo_engine():
    mc = MonteCarloEngine(initial_balance=10000.0)

    positions = []
    base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(20):
        is_win = (i % 2 == 0)
        pnl = 100.0 if is_win else -80.0
        pos = Position(
            ticket=i,
            symbol="XAUUSDm",
            side=OrderSide.BUY,
            volume=0.1,
            open_price=2000.0,
            open_time_utc=base_t + timedelta(days=i),
            sl=1990.0,
            tp=2010.0,
            close_price=2001.0 if is_win else 1999.0,
            close_time_utc=base_t + timedelta(days=i, hours=2),
            exit_reason=ExitReason.TAKE_PROFIT if is_win else ExitReason.STOP_LOSS,
            realized_pnl=pnl,
            spread_cost=8.0,
            slippage_cost=2.0,
            accumulated_swap=0.0,
            commission=0.0,
        )
        positions.append(pos)

    res = mc.analyze(positions, iterations=200, random_seed=42)
    assert res.iterations == 200
    assert res.dd_worst >= res.dd_p95 >= res.dd_p50 >= res.dd_p5
    # Xarajat stress testi: 2.0x xarajatda net profit 1.0x dan kam bo'lishi kerak
    assert res.cost_stress_2_0x < res.cost_stress_1_5x < res.cost_stress_1_0x


def test_walk_forward_splitter():
    df = _create_sample_df_days(1100)
    splitter = WalkForwardSplitter(timeframe="H1", is_days=365, oos_days=90, step_days=90)
    windows = splitter.generate_windows(df)

    assert len(windows) > 0
    for w in windows:
        assert w.is_start < w.is_end
        assert w.is_end <= w.oos_start
        assert w.oos_start < w.oos_end
        assert w.is_bars > 0
        assert w.oos_bars > 0
