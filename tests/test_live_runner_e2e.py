"""End-to-End and Unit Tests for LiveRunner FU-M3 Execution Logic."""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

from python_brain.main import LiveRunner, build_account_state, explain_fu_condition
from python_brain.backtest.models import Signal, SignalLeg, OrderSide
from python_brain.execution.broker_executor import ExecutionResult


class MockTick:
    def __init__(self, ask=2650.20, bid=2650.00, time_val=None):
        self.ask = ask
        self.bid = bid
        self.time = time_val or int(datetime.now(timezone.utc).timestamp())


class MockSymbolInfo:
    def __init__(self, stops_level=10, point=0.001, filling_mode=2):
        self.stops_level = stops_level
        self.point = point
        self.filling_mode = filling_mode


class MockAccount:
    def __init__(self):
        self.login = 123456
        self.trade_mode = 0  # DEMO
        self.server = "MetaQuotes-Demo"
        self.balance = 10000.0
        self.equity = 10000.0
        self.margin_free = 10000.0
        self.leverage = 100


@pytest.fixture
def mock_mt5_env(tmp_path):
    """Sets up a comprehensive mocked MT5 environment."""
    mock_mt5 = MagicMock()
    mock_mt5.TIMEFRAME_M3 = 3
    mock_mt5.account_info.return_value = MockAccount()
    mock_mt5.symbol_info.return_value = MockSymbolInfo(stops_level=20, point=0.001, filling_mode=2)
    mock_mt5.symbol_info_tick.return_value = MockTick()
    mock_mt5.positions_get.return_value = []
    mock_mt5.history_deals_get.return_value = []

    # Mock order_send
    mock_send_res = MagicMock()
    mock_send_res.retcode = 10009
    mock_send_res.order = 101
    mock_send_res.price = 2650.20
    mock_send_res.comment = "Done"
    mock_mt5.order_send.return_value = mock_send_res

    return mock_mt5


def create_fu_sell_df(base_time: datetime) -> pd.DataFrame:
    """Creates synthetic DataFrame that triggers FU SELL."""
    rows = [
        {"open": 2640.0, "high": 2642.0, "low": 2639.0, "close": 2641.5},  # t-4 bullish
        {"open": 2641.5, "high": 2644.0, "low": 2641.0, "close": 2643.5},  # t-3 bullish
        {"open": 2643.5, "high": 2646.0, "low": 2643.0, "close": 2645.5},  # t-2 bullish
        {"open": 2645.5, "high": 2648.0, "low": 2645.0, "close": 2647.5},  # t-1 trend candle
        {"open": 2647.5, "high": 2650.0, "low": 2644.0, "close": 2646.0},  # t FU bearish candle (sweep high, close < prev close)
    ]
    df = pd.DataFrame(rows)
    times = [base_time - timedelta(minutes=3 * (4 - i)) for i in range(5)]
    df["time_utc"] = times
    df["time"] = [int(t.timestamp()) for t in times]
    return df


def test_explain_fu_condition():
    """Verify explain_fu_condition returns accurate diagnostic messages."""
    base_time = datetime.now(timezone.utc)
    df_sell = create_fu_sell_df(base_time)
    explanation = explain_fu_condition(df_sell, min_trend_candles=3)
    assert explanation == "FU_SELL_FORMED"

    # Not enough trend candles
    df_notrend = df_sell.copy()
    df_notrend.loc[1, "close"] = 2640.0  # bearish instead of bullish
    explanation_nt = explain_fu_condition(df_notrend, min_trend_candles=3)
    assert "NO_TREND" in explanation_nt


@patch("python_brain.main.mt5")
@patch("python_brain.main.MT5Connector")
def test_two_leg_order_execution_and_tp_modify(mock_conn_cls, mock_mt5, tmp_path):
    """Test full atomic execution of Leg A and Leg B with server-side TP modify."""
    mock_conn = MagicMock()
    mock_conn.initialize.return_value = True
    mock_conn.login.return_value = True
    mock_conn.get_account_info.return_value = MockAccount()
    mock_conn.find_actual_symbol.return_value = "XAUUSDm"
    now_ts = int(datetime.now(timezone.utc).timestamp())
    mock_conn.get_symbol_info_tick.return_value = MockTick(ask=2650.0, bid=2649.8, time_val=now_ts)
    mock_mt5.symbol_info.return_value = MockSymbolInfo(stops_level=20, point=0.001)
    mock_mt5.positions_get.return_value = []
    mock_conn._mt5 = mock_mt5
    mock_conn_cls.return_value = mock_conn

    # Setup Runner
    runner = LiveRunner(single_pass=True, timeframe="M3")
    runner.state_file_path = tmp_path / "runner_state.json"

    # Mock historical rates to trigger FU SELL
    df = create_fu_sell_df(datetime.now(timezone.utc))
    runner.get_history_dataframe = MagicMock(return_value=df)

    # Mock executor send_market_order
    res_a = ExecutionResult(success=True, retcode=10009, comment="Done", ticket=101, fill_price=2650.0)
    res_b = ExecutionResult(success=True, retcode=10009, comment="Done", ticket=102, fill_price=2650.0)
    runner.executor.send_market_order = MagicMock(side_effect=[res_a, res_b])
    runner.executor.modify_position_sl_tp = MagicMock(return_value=ExecutionResult(success=True, retcode=10009, comment="Done"))

    # Mock copy_rates_from_pos for latest bar (just closed, new bar just opened)
    mock_mt5.copy_rates_from_pos.return_value = [
        {"time": now_ts - 180},
        {"time": now_ts},
    ]

    # Run cycle
    runner.run_cycle()

    # Verify both legs sent
    assert runner.executor.send_market_order.call_count == 2
    # Verify both TPs modified to exact prices based on fill
    assert runner.executor.modify_position_sl_tp.call_count == 2
    # Verify active setup stored
    assert runner.active_setup is not None
    assert runner.active_setup["leg_a_ticket"] == 101
    assert runner.active_setup["leg_b_ticket"] == 102


@patch("python_brain.main.mt5")
@patch("python_brain.main.MT5Connector")
def test_atomic_execution_failure_closes_opened_leg(mock_conn_cls, mock_mt5, tmp_path):
    """Test that if Leg B fails, opened Leg A is immediately closed."""
    mock_conn = MagicMock()
    mock_conn.initialize.return_value = True
    mock_conn.login.return_value = True
    mock_conn.get_account_info.return_value = MockAccount()
    mock_conn.find_actual_symbol.return_value = "XAUUSDm"
    now_ts = int(datetime.now(timezone.utc).timestamp())
    mock_conn.get_symbol_info_tick.return_value = MockTick(ask=2650.0, bid=2649.8, time_val=now_ts)
    mock_mt5.symbol_info.return_value = MockSymbolInfo(stops_level=20, point=0.001)
    mock_mt5.positions_get.return_value = []
    mock_conn._mt5 = mock_mt5
    mock_conn_cls.return_value = mock_conn

    runner = LiveRunner(single_pass=True, timeframe="M3")
    runner.state_file_path = tmp_path / "runner_state.json"

    df = create_fu_sell_df(datetime.now(timezone.utc))
    runner.get_history_dataframe = MagicMock(return_value=df)

    # Leg A succeeds, Leg B fails
    res_a = ExecutionResult(success=True, retcode=10009, comment="Done", ticket=101, fill_price=2650.0)
    res_b = ExecutionResult(success=False, retcode=10019, comment="No money")
    runner.executor.send_market_order = MagicMock(side_effect=[res_a, res_b])
    runner.executor.close_position = MagicMock(return_value=ExecutionResult(success=True, retcode=10009, comment="Closed"))

    mock_mt5.copy_rates_from_pos.return_value = [
        {"time": now_ts - 180},
        {"time": now_ts},
    ]

    runner.run_cycle()

    # Verify close_position was called for Leg A ticket 101
    runner.executor.close_position.assert_called_once_with(101)
    assert runner.active_setup is None


@patch("python_brain.main.mt5")
@patch("python_brain.main.MT5Connector")
def test_breakeven_trailing_triggered_on_leg_a_tp(mock_conn_cls, mock_mt5, tmp_path):
    """Test that when Leg A closes with TP, Leg B SL is moved to entry price."""
    mock_conn = MagicMock()
    mock_conn.initialize.return_value = True
    mock_conn.login.return_value = True
    mock_conn.get_account_info.return_value = MockAccount()
    mock_conn.find_actual_symbol.return_value = "XAUUSDm"
    mock_conn.get_symbol_info_tick.return_value = MockTick()
    mock_conn._mt5 = mock_mt5
    mock_conn_cls.return_value = mock_conn

    runner = LiveRunner(single_pass=True, timeframe="M3")
    runner.state_file_path = tmp_path / "runner_state.json"

    # Set active setup
    runner.active_setup = {
        "leg_a_ticket": 101,
        "leg_b_ticket": 102,
        "entry_price": 2650.0,
        "side": "SELL",
        "be_applied": False,
    }

    # Reconcile open positions: only Leg B is open (Leg A is closed)
    runner.executor.reconcile_open_positions = MagicMock(return_value=[
        {"ticket": 102, "symbol": "XAUUSDm", "type": "SELL", "open_price": 2650.0}
    ])
    # Leg A closed by TP
    runner._check_if_leg_closed_by_tp = MagicMock(return_value=True)
    runner.executor.modify_position_sl_tp = MagicMock(return_value=ExecutionResult(success=True, retcode=10009, comment="Done"))

    runner.check_breakeven_and_closures()

    # Verify modify_position_sl_tp was called with entry_price
    runner.executor.modify_position_sl_tp.assert_called_once_with(ticket=102, sl=2650.0)
    assert runner.active_setup["be_applied"] is True


@patch("python_brain.main.mt5")
@patch("python_brain.main.MT5Connector")
def test_single_setup_rule_skips_new_signals(mock_conn_cls, mock_mt5, tmp_path):
    """Test that if an active setup exists, any new signal is strictly skipped."""
    mock_conn = MagicMock()
    mock_conn.initialize.return_value = True
    mock_conn.login.return_value = True
    mock_conn.get_account_info.return_value = MockAccount()
    mock_conn.find_actual_symbol.return_value = "XAUUSDm"
    now_ts = int(datetime.now(timezone.utc).timestamp())
    mock_conn.get_symbol_info_tick.return_value = MockTick(time_val=now_ts)
    mock_conn._mt5 = mock_mt5
    mock_conn_cls.return_value = mock_conn

    runner = LiveRunner(single_pass=True, timeframe="M3")
    runner.state_file_path = tmp_path / "runner_state.json"

    # Broker has open positions
    runner.executor.reconcile_open_positions = MagicMock(return_value=[{"ticket": 999}])
    runner.executor.send_market_order = MagicMock()

    mock_mt5.copy_rates_from_pos.return_value = [
        {"time": now_ts - 360},
        {"time": now_ts - 180},
    ]

    df = create_fu_sell_df(datetime.now(timezone.utc))
    runner.get_history_dataframe = MagicMock(return_value=df)

    runner.run_cycle()

    # send_market_order must NOT be called
    runner.executor.send_market_order.assert_not_called()


@patch("python_brain.main.mt5")
@patch("python_brain.main.MT5Connector")
def test_entry_delay_over_5s_skips_setup(mock_conn_cls, mock_mt5, tmp_path):
    """Test that if >5 seconds passed since bar open, setup is skipped."""
    mock_conn = MagicMock()
    mock_conn.initialize.return_value = True
    mock_conn.login.return_value = True
    mock_conn.get_account_info.return_value = MockAccount()
    mock_conn.find_actual_symbol.return_value = "XAUUSDm"
    now_ts = int(datetime.now(timezone.utc).timestamp())
    mock_conn.get_symbol_info_tick.return_value = MockTick(time_val=now_ts)
    mock_conn._mt5 = mock_mt5
    mock_conn_cls.return_value = mock_conn

    runner = LiveRunner(single_pass=True, timeframe="M3")
    runner.state_file_path = tmp_path / "runner_state.json"
    runner.executor.reconcile_open_positions = MagicMock(return_value=[])
    runner.executor.send_market_order = MagicMock()

    # Closed bar was at now_ts - 200, new forming bar opened at now_ts - 20 (> 5s ago)
    mock_mt5.copy_rates_from_pos.return_value = [
        {"time": now_ts - 200},
        {"time": now_ts - 20},
    ]
    df = create_fu_sell_df(datetime.now(timezone.utc))
    runner.get_history_dataframe = MagicMock(return_value=df)

    runner.run_cycle()

    # Must be skipped due to delay
    runner.executor.send_market_order.assert_not_called()


@patch("python_brain.main.mt5")
@patch("python_brain.main.MT5Connector")
def test_stops_level_inside_skips_setup(mock_conn_cls, mock_mt5, tmp_path):
    """Test that if SL distance is within broker stops_level, setup is skipped."""
    mock_conn = MagicMock()
    mock_conn.initialize.return_value = True
    mock_conn.login.return_value = True
    mock_conn.get_account_info.return_value = MockAccount()
    mock_conn.find_actual_symbol.return_value = "XAUUSDm"
    now_ts = int(datetime.now(timezone.utc).timestamp())
    mock_conn.get_symbol_info_tick.return_value = MockTick(ask=2650.0, bid=2649.8, time_val=now_ts)
    # stops_level = 5000 points = 5.0 USD (wider than SL buffer 0.5 USD)
    mock_mt5.symbol_info.return_value = MockSymbolInfo(stops_level=5000, point=0.001)
    mock_mt5.positions_get.return_value = []
    mock_conn._mt5 = mock_mt5
    mock_conn_cls.return_value = mock_conn

    runner = LiveRunner(single_pass=True, timeframe="M3")
    runner.state_file_path = tmp_path / "runner_state.json"
    runner.executor.send_market_order = MagicMock()

    mock_mt5.copy_rates_from_pos.return_value = [
        {"time": now_ts - 180},
        {"time": now_ts},
    ]

    df = create_fu_sell_df(datetime.now(timezone.utc))
    runner.get_history_dataframe = MagicMock(return_value=df)

    runner.run_cycle()

    # Must be skipped due to stops_level
    runner.executor.send_market_order.assert_not_called()


def test_retcode_10027_and_10030_clear_descriptions():
    """Verify MT5BrokerExecutor handles retcode 10027 and 10030 with user-friendly descriptions."""
    from python_brain.execution.broker_executor import MT5BrokerExecutor, RETCODE_MAP

    assert 10027 in RETCODE_MAP
    assert "Allow Algo Trading" in RETCODE_MAP[10027]
    assert 10030 in RETCODE_MAP
    assert "Unsupported filling mode" in RETCODE_MAP[10030]
    assert 10016 in RETCODE_MAP
    assert "stops_level" in RETCODE_MAP[10016]
