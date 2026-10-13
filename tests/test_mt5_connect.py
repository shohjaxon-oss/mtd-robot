"""Mocked tests for MetaTrader 5 connector, live tick spread, and specification extractor."""

from unittest.mock import MagicMock, patch
import pytest
from python_brain.mt5_connect import MT5Connector


@pytest.fixture
def mock_mt5():
    """Create a mock MetaTrader5 module fixture."""
    mock = MagicMock()

    # Mock account info
    acc = MagicMock()
    acc.login = 12345678
    acc.trade_mode = 0  # DEMO
    acc.name = "Standard"
    acc.server = "Exness-MT5Trial15"
    acc.currency = "USD"
    acc.leverage = 2000
    acc.balance = 5000.0
    acc.equity = 5000.0
    acc.profit = 0.0
    acc.margin = 0.0
    acc.margin_free = 5000.0
    acc.margin_level = 0.0
    mock.account_info.return_value = acc

    # Mock terminal info
    term = MagicMock()
    term.name = "MetaTrader 5"
    mock.terminal_info.return_value = term

    mock.initialize.return_value = True
    mock.login.return_value = True
    mock.last_error.return_value = (1, "Success")

    return mock


def test_mt5_connection_success(mock_mt5):
    """Test successful initialization and connection."""
    with patch("python_brain.mt5_connect.mt5", mock_mt5):
        connector = MT5Connector(
            login=12345678,
            password="test_demo_password",
            server="Exness-MT5Trial15",
        )
        assert connector.connect() is True
        assert connector.is_connected is True

        snapshot = connector.get_account_snapshot()
        assert snapshot is not None
        assert snapshot.login == 12345678
        assert snapshot.trade_mode == "DEMO"
        assert snapshot.leverage == 2000

        connector.disconnect()
        assert connector.is_connected is False


def test_mt5_connection_failure(mock_mt5):
    """Test handling of terminal initialization failure."""
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (-1, "Terminal not found")

    with patch("python_brain.mt5_connect.mt5", mock_mt5):
        connector = MT5Connector()
        assert connector.connect() is False
        assert connector.is_connected is False


def test_find_actual_symbol_priority(mock_mt5):
    """Test discovering actual instrument name (e.g. XAUUSDm on Standard account)."""
    def symbol_info_side_effect(name):
        if name == "XAUUSDm":
            sym = MagicMock()
            sym.name = "XAUUSDm"
            sym.visible = True
            return sym
        return None

    mock_mt5.symbol_info.side_effect = symbol_info_side_effect

    with patch("python_brain.mt5_connect.mt5", mock_mt5):
        connector = MT5Connector()
        connector.is_connected = True

        actual_symbol = connector.find_actual_symbol(["XAUUSD", "XAUUSDm", "XAUUSD.c"])
        assert actual_symbol == "XAUUSDm"


def test_get_live_tick_spread(mock_mt5):
    """Verify live spread calculation directly from ask - bid."""
    sym = MagicMock()
    sym.digits = 3
    sym.point = 0.001
    mock_mt5.symbol_info.return_value = sym

    tick = MagicMock()
    tick.bid = 2700.100
    tick.ask = 2700.340
    tick.time = 1700000000
    mock_mt5.symbol_info_tick.return_value = tick

    with patch("python_brain.mt5_connect.mt5", mock_mt5):
        connector = MT5Connector()
        connector.is_connected = True

        live_tick = connector.get_live_tick("XAUUSDm")
        assert live_tick is not None
        assert live_tick.bid == 2700.100
        assert live_tick.ask == 2700.340
        assert live_tick.spread_price == 0.24
        assert live_tick.spread_points == 240.0


def test_get_symbol_specification_and_swaps(mock_mt5):
    """Test symbol specification mapping including swap calculation."""
    sym = MagicMock()
    sym.name = "XAUUSDm"
    sym.visible = True
    sym.path = "Standard\\Forex\\XAUUSDm"
    sym.digits = 3
    sym.point = 0.001
    sym.spread = 240
    sym.trade_mode = 4  # FULL
    sym.trade_contract_size = 100.0
    sym.trade_tick_size = 0.001
    sym.trade_tick_value = 0.1
    sym.volume_min = 0.01
    sym.volume_max = 500.0
    sym.volume_step = 0.01
    sym.trade_stops_level = 0
    sym.swap_mode = 1  # Points
    sym.swap_long = -523.3
    sym.swap_short = 0.0
    sym.swap_rollover3days = 3  # Wednesday/Thursday 3x rollover

    mock_mt5.symbol_info.return_value = sym

    with patch("python_brain.mt5_connect.mt5", mock_mt5):
        connector = MT5Connector()
        connector.is_connected = True

        spec = connector.get_symbol_specification("XAUUSDm")
        assert spec is not None
        assert spec.name == "XAUUSDm"
        assert spec.digits == 3
        assert spec.point == 0.001
        assert spec.contract_size == 100.0
        assert spec.swap_mode_desc == "Points"
        assert spec.swap_long_usd_per_lot == -52.33
        assert spec.swap_short_usd_per_lot == 0.0


def test_calc_trade_impact(mock_mt5):
    """Test margin calculation and $1 move profit simulation."""
    sym = MagicMock()
    sym.trade_tick_value = 0.1
    mock_mt5.symbol_info.return_value = sym

    mock_mt5.order_calc_margin.side_effect = lambda action, sym, vol, p: 200.0 * vol
    mock_mt5.order_calc_profit.side_effect = lambda action, sym, vol, p1, p2: (p2 - p1) * 100.0 * vol

    with patch("python_brain.mt5_connect.mt5", mock_mt5):
        connector = MT5Connector()
        connector.is_connected = True

        impact = connector.calc_trade_impact("XAUUSDm", test_price=2700.0)
        assert impact is not None
        assert impact.margin_1_lot == 200.0
        assert impact.margin_001_lot == 2.0
        assert impact.profit_1_lot_1usd_move == 100.0
        assert impact.profit_001_lot_1usd_move == 1.0
