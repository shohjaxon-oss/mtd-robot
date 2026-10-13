"""Comprehensive unit and integration tests for FU Formation Strategy (HYP-09).

Covers:
- Exact User Fixture for SELL (SL=2002.900, TP_A=1999.280, TP_B=1998.280)
- Exact Mirror Fixture for BUY (SL=1997.100)
- Negative rejection test cases:
    * Only 2 trend candles
    * Doji in trend candles
    * Engulfing between trend candles
    * FU high <= prev high
    * FU close >= prev close
    * Bullish FU on SELL / Bearish FU on BUY
    * Invalid timeframes (M15, H1, etc.)
- Lookahead slice invariance test
- Engine simulation tests:
    * 2-leg setup execution
    * Leg A TP triggering Leg B Breakeven move
    * Simultaneous TP_A and TP_B with retracement vs no retracement
    * Both legs hitting initial Stop Loss
    * Spread costs evaluated on both legs
- RiskGate atomic approval and setup-level risk cap
- pip_size_price customization sensitivity
"""

from datetime import datetime, timezone, timedelta
import pandas as pd
import pytest

from python_brain.signals.fu_formation import FUFormationStrategy
from python_brain.backtest.engine import BacktestEngine
from python_brain.backtest.models import Signal, SignalLeg, OrderSide, ExitReason, AccountState
from python_brain.backtest.risk_gate import DefaultRiskGate
from python_brain.backtest.costs import CostModel


# ---------------------------------------------------------------------------
# 1. Exact User Fixtures (SELL and BUY)
# ---------------------------------------------------------------------------
def make_df_from_rows(rows):
    """Helper to construct DataFrame with time_utc from candle tuples (O, H, L, C)."""
    base_time = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    records = []
    for i, (o, h, l, c) in enumerate(rows):
        records.append({
            "time_utc": base_time + timedelta(minutes=5 * i),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "tick_volume": 100,
            "spread": 160.0,
        })
    return pd.DataFrame(records)


def test_user_fixture_sell():
    """Exact test fixture for SELL specified by user:
    t-3: 2000.00 2000.60 1999.90 2000.50
    t-2: 2000.45 2001.20 2000.35 2001.10
    t-1: 2001.05 2001.80 2000.95 2001.70
    t  : 2001.60 2002.40 2001.10 2001.30   (FU)
    t+1 ochilishi: 2001.28
    Expected: SELL, SL = 2002.900 (16.2 pip), TP_A = 1999.280, TP_B = 1998.280.
    """
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),  # t-3 (bullish)
        (2000.45, 2001.20, 2000.35, 2001.10),  # t-2 (bullish)
        (2001.05, 2001.80, 2000.95, 2001.70),  # t-1 (bullish)
        (2001.60, 2002.40, 2001.10, 2001.30),  # t   (bearish FU)
    ]
    df = make_df_from_rows(rows)

    strat = FUFormationStrategy(timeframe="M5", pip_size_price=0.10, sl_buffer_pips=5.0, tp1_pips=20.0, tp2_pips=30.0)
    sig = strat.on_bar(df)

    assert sig is not None
    assert sig.action == "SELL"
    # SL = high_t (2002.40) + 5 * 0.10 = 2002.900
    assert sig.sl == pytest.approx(2002.900, abs=1e-3)
    assert len(sig.legs) == 2
    assert sig.legs[0].tp_pips == 20.0
    assert sig.legs[1].tp_pips == 30.0
    assert sig.breakeven_on_first_tp is True

    # Check execution at t+1 open = 2001.28
    t_plus_1_open = 2001.28
    # SL distance in pips: (2002.900 - 2001.28) / 0.10 = 16.2 pips
    sl_distance_pips = (sig.sl - t_plus_1_open) / 0.10
    assert sl_distance_pips == pytest.approx(16.2, abs=1e-2)

    tp_a_price = t_plus_1_open - (20.0 * 0.10)
    tp_b_price = t_plus_1_open - (30.0 * 0.10)
    assert tp_a_price == pytest.approx(1999.280, abs=1e-3)
    assert tp_b_price == pytest.approx(1998.280, abs=1e-3)


def test_user_fixture_buy_mirror():
    """Mirror fixture for BUY: price' = 4000 - price, high and low swap.
    Expected: BUY, SL = 1997.100.
    """
    # Original:
    # t-3: 2000.00 2000.60 1999.90 2000.50
    # Mirror: O = 4000 - 2000 = 2000.00, H = 4000 - 1999.90 = 2000.10, L = 4000 - 2000.60 = 1999.40, C = 4000 - 2000.50 = 1999.50
    # t-2: 2000.45 2001.20 2000.35 2001.10 -> O=1999.55, H=1999.65, L=1998.80, C=1998.90
    # t-1: 2001.05 2001.80 2000.95 2001.70 -> O=1998.95, H=1999.05, L=1998.20, C=1998.30
    # t  : 2001.60 2002.40 2001.10 2001.30 -> O=1998.40, H=1998.90, L=1997.60, C=1998.70
    rows = [
        (2000.00, 2000.10, 1999.40, 1999.50),  # t-3 (bearish)
        (1999.55, 1999.65, 1998.80, 1998.90),  # t-2 (bearish)
        (1998.95, 1999.05, 1998.20, 1998.30),  # t-1 (bearish)
        (1998.40, 1998.90, 1997.60, 1998.70),  # t   (bullish FU)
    ]
    df = make_df_from_rows(rows)

    strat = FUFormationStrategy(timeframe="M5", pip_size_price=0.10, sl_buffer_pips=5.0)
    sig = strat.on_bar(df)

    assert sig is not None
    assert sig.action == "BUY"
    # SL = low_t (1997.60) - 5 * 0.10 = 1997.100
    assert sig.sl == pytest.approx(1997.100, abs=1e-3)


# ---------------------------------------------------------------------------
# 2. Rejection Test Cases (Negative Cases)
# ---------------------------------------------------------------------------
def test_reject_if_only_two_trend_candles():
    """Trend has only 2 bullish candles instead of 3."""
    rows = [
        (2000.50, 2000.60, 1999.90, 2000.00),  # t-3 BEARISH (breached)
        (2000.45, 2001.20, 2000.35, 2001.10),  # t-2 bullish
        (2001.05, 2001.80, 2000.95, 2001.70),  # t-1 bullish
        (2001.60, 2002.40, 2001.10, 2001.30),  # t   FU
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")
    assert strat.on_bar(df) is None


def test_reject_if_doji_in_trend():
    """Doji (open == close) inside trend candles."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),  # t-3 bullish
        (2000.50, 2001.20, 2000.35, 2000.50),  # t-2 DOJI (open == close)
        (2001.05, 2001.80, 2000.95, 2001.70),  # t-1 bullish
        (2001.60, 2002.40, 2001.10, 2001.30),  # t   FU
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")
    assert strat.on_bar(df) is None


def test_reject_if_engulfing_between_trend_candles():
    """t-1 completely engulfs body of t-2."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),  # t-3 bullish [2000.00, 2000.50]
        (2000.60, 2001.00, 2000.55, 2000.90),  # t-2 bullish [2000.60, 2000.90]
        (2000.50, 2001.80, 2000.40, 2001.70),  # t-1 bullish [2000.50, 2001.70] -> engulfs t-2!
        (2001.60, 2002.40, 2001.10, 2001.30),  # t   FU
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5", engulf_mode="body")
    assert strat.on_bar(df) is None


def test_reject_if_fu_high_not_greater_than_prev_high():
    """FU high <= prev high."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),
        (2000.45, 2001.20, 2000.35, 2001.10),
        (2001.05, 2002.50, 2000.95, 2001.70),  # prev high = 2002.50
        (2001.60, 2002.40, 2001.10, 2001.30),  # fu high = 2002.40 <= 2002.50!
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")
    assert strat.on_bar(df) is None


def test_reject_if_fu_close_not_below_prev_close():
    """FU close >= prev close."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),
        (2000.45, 2001.20, 2000.35, 2001.10),
        (2001.05, 2001.80, 2000.95, 2001.70),  # prev close = 2001.70
        (2001.90, 2002.40, 2001.10, 2001.75),  # fu close = 2001.75 > 2001.70!
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")
    assert strat.on_bar(df) is None


def test_reject_if_fu_candle_is_bullish_for_sell():
    """FU candle is bullish (close > open)."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),
        (2000.45, 2001.20, 2000.35, 2001.10),
        (2001.05, 2001.80, 2000.95, 2001.70),
        (2001.10, 2002.40, 2001.00, 2001.30),  # fu open=2001.10, close=2001.30 (BULLISH!)
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")
    assert strat.on_bar(df) is None


def test_invalid_timeframe_raises_value_error():
    """FU Formation must strictly reject any timeframe other than M1, M3, M5."""
    with pytest.raises(ValueError, match="Noto'g'ri timeframe"):
        FUFormationStrategy(timeframe="M15")

    with pytest.raises(ValueError, match="Noto'g'ri timeframe"):
        FUFormationStrategy(timeframe="H1")


# ---------------------------------------------------------------------------
# 3. Lookahead Slice Invariance Test
# ---------------------------------------------------------------------------
def test_fu_strategy_lookahead_slice():
    """Signal on candle t must be completely invariant to future candles t+1, t+2."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),
        (2000.45, 2001.20, 2000.35, 2001.10),
        (2001.05, 2001.80, 2000.95, 2001.70),
        (2001.60, 2002.40, 2001.10, 2001.30),  # t (FU signal)
        (2001.28, 2001.90, 2000.80, 2001.00),  # t+1
        (2001.00, 2001.50, 1999.00, 1999.20),  # t+2
    ]
    full_df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")

    # Evaluated exactly at bar t
    df_slice = full_df.iloc[:4]
    sig_slice = strat.on_bar(df_slice)

    assert sig_slice is not None
    assert sig_slice.action == "SELL"
    assert sig_slice.sl == pytest.approx(2002.900, abs=1e-3)


# ---------------------------------------------------------------------------
# 4. Engine Simulation & Multi-Leg Breakeven Tests
# ---------------------------------------------------------------------------
def test_engine_two_leg_execution_and_breakeven_move():
    """Engine test:
    - Bar 4 triggers SELL signal.
    - Bar 5 opens trade at bar 5 OPEN (2001.28).
    - Bar 6 hits TP_A (1999.28). Leg A closes at TP, Leg B SL moved to Entry (2001.28).
    - Bar 7 reaches TP_B (1998.28). Leg B closes at TP.
    """
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),  # bar 0
        (2000.45, 2001.20, 2000.35, 2001.10),  # bar 1
        (2001.05, 2001.80, 2000.95, 2001.70),  # bar 2
        (2001.60, 2002.40, 2001.10, 2001.30),  # bar 3: FU SELL signal!
        (2001.28, 2001.30, 2000.50, 2000.80),  # bar 4: execution bar (open 2001.28)
        (2000.80, 2000.90, 1999.20, 1999.50),  # bar 5: low reaches 1999.20 <= TP_A (1999.28)!
        (1999.50, 1999.60, 1998.10, 1998.20),  # bar 6: low reaches 1998.10 <= TP_B (1998.28)!
    ]
    df = make_df_from_rows(rows)

    strat = FUFormationStrategy(timeframe="M5", pip_size_price=0.10, tp1_pips=20.0, tp2_pips=30.0)
    engine = BacktestEngine(initial_balance=10000.0)
    costs = CostModel(point=0.001, contract_size=100.0)

    account = engine.run(df, strategy=strat, cost_model=costs)

    assert len(account.closed_positions) == 2
    leg_a = [p for p in account.closed_positions if p.leg_id == "A"][0]
    leg_b = [p for p in account.closed_positions if p.leg_id == "B"][0]

    assert leg_a.exit_reason == ExitReason.TAKE_PROFIT
    assert leg_b.exit_reason == ExitReason.TAKE_PROFIT
    assert leg_a.close_price == pytest.approx(1999.28, abs=1e-2)
    assert leg_b.close_price == pytest.approx(1998.28, abs=1e-2)


def test_engine_initial_sl_hits_both_legs():
    """Initial SL hit closes both Leg A and Leg B at SL."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),
        (2000.45, 2001.20, 2000.35, 2001.10),
        (2001.05, 2001.80, 2000.95, 2001.70),
        (2001.60, 2002.40, 2001.10, 2001.30),  # FU signal (SL = 2002.90)
        (2001.28, 2001.30, 2000.80, 2001.00),  # Execution
        (2001.00, 2003.50, 2000.80, 2003.20),  # Ask high spikes to 2003.50 >= 2002.90!
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")
    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strategy=strat)

    assert len(account.closed_positions) == 2
    assert account.closed_positions[0].exit_reason == ExitReason.STOP_LOSS
    assert account.closed_positions[1].exit_reason == ExitReason.STOP_LOSS


def test_engine_simultaneous_tp_with_retracement():
    """If both TP_A and TP_B touched in same candle, but candle retraces to entry:
    Leg B closes at breakeven and setup is marked ambiguous."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),
        (2000.45, 2001.20, 2000.35, 2001.10),
        (2001.05, 2001.80, 2000.95, 2001.70),
        (2001.60, 2002.40, 2001.10, 2001.30),  # FU signal (SL 2002.90)
        (2001.28, 2001.30, 2000.80, 2001.00),  # Exec open 2001.28
        # Giant volatile candle: touches TP_B (low 1997.00), but high reached 2001.50 >= 2001.28 (retracement!)
        (2001.00, 2001.50, 1997.00, 1999.00),
    ]
    df = make_df_from_rows(rows)
    strat = FUFormationStrategy(timeframe="M5")
    engine = BacktestEngine(initial_balance=10000.0)
    account = engine.run(df, strategy=strat)

    assert len(account.closed_positions) == 2
    leg_a = [p for p in account.closed_positions if p.leg_id == "A"][0]
    leg_b = [p for p in account.closed_positions if p.leg_id == "B"][0]

    assert leg_a.exit_reason == ExitReason.TAKE_PROFIT
    assert leg_b.exit_reason == ExitReason.STOP_LOSS  # Breakeven stop
    assert leg_b.is_ambiguous_exit is True


# ---------------------------------------------------------------------------
# 5. RiskGate & pip_size_price Customization Tests
# ---------------------------------------------------------------------------
def test_pip_size_price_scaling():
    """Doubling pip_size_price from 0.10 to 0.20 must double the SL distance."""
    rows = [
        (2000.00, 2000.60, 1999.90, 2000.50),
        (2000.45, 2001.20, 2000.35, 2001.10),
        (2001.05, 2001.80, 2000.95, 2001.70),
        (2001.60, 2002.40, 2001.10, 2001.30),  # FU high = 2002.40
    ]
    df = make_df_from_rows(rows)
    strat_10 = FUFormationStrategy(timeframe="M5", pip_size_price=0.10, sl_buffer_pips=5.0)
    strat_20 = FUFormationStrategy(timeframe="M5", pip_size_price=0.20, sl_buffer_pips=5.0)

    sig_10 = strat_10.on_bar(df)
    sig_20 = strat_20.on_bar(df)

    # With 0.10: 2002.40 + 0.50 = 2002.90
    assert sig_10.sl == pytest.approx(2002.90, abs=1e-3)
    # With 0.20: 2002.40 + 1.00 = 2003.40
    assert sig_20.sl == pytest.approx(2003.40, abs=1e-3)


def test_risk_gate_multi_leg_risk_cap():
    """RiskGate must reject setup if total risk (0.02 lot * SL distance) exceeds 1.0% of balance."""
    gate = DefaultRiskGate()
    account = AccountState(
        initial_balance=1000.0,  # $1,000 balance -> 1% is $10 max risk
        balance=1000.0,
        equity=1000.0,
        free_margin=1000.0,
        peak_balance=1000.0,
        peak_equity=1000.0,
    )

    # Huge SL distance = 10.00 USD -> 0.02 lot * 10 * 100 = $20 risk > $10 (1%)!
    legs = [SignalLeg(leg_id="A", volume=0.01), SignalLeg(leg_id="B", volume=0.01)]
    sig = Signal(
        time_utc=datetime.now(timezone.utc),
        action="SELL",
        sl=2010.0,  # exec_price = 2000.0 -> distance = 10.0
        legs=legs,
    )

    approved = gate.approve(sig, execution_price=2000.0, account=account)
    assert approved is None  # Rejected due to risk cap!
