"""MetaTrader 5 connection, tick extraction, and symbol specification module.

Handles terminal initialization, authentication, symbol discovery (e.g. XAUUSD vs XAUUSDm),
real-time tick spread calculation, swap valuation, and margin/profit simulation.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from python_brain.logger import app_logger, register_secret_to_mask

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


@dataclass
class AccountSnapshot:
    login: int
    trade_mode: str  # DEMO | REAL | CONTEST
    name: str
    server: str
    currency: str
    leverage: int
    balance: float
    equity: float
    profit: float
    margin: float
    margin_free: float
    margin_level: float


@dataclass
class LiveTick:
    bid: float
    ask: float
    spread_price: float
    spread_points: float
    time: int


@dataclass
class TradeImpactCalc:
    margin_1_lot: float
    margin_001_lot: float
    profit_1_lot_1usd_move: float
    profit_001_lot_1usd_move: float
    tick_value: float


@dataclass
class SymbolSpecification:
    name: str
    visible: bool
    path: str
    digits: int
    point: float
    spread_raw: int  # symbol_info().spread
    trade_mode: str  # FULL | CLOSEONLY | DISABLED
    contract_size: float
    tick_size: float
    tick_value: float
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level: int
    swap_mode: int
    swap_mode_desc: str
    swap_long: float
    swap_short: float
    swap_rollover3days: int
    swap_rollover3days_desc: str
    swap_long_usd_per_lot: float
    swap_short_usd_per_lot: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MT5Connector:
    """Manages MetaTrader 5 terminal initialization, live ticks, and symbol inspections."""

    SWAP_MODES = {
        0: "Disabled (No Swap)",
        1: "Points",
        2: "Base Currency",
        3: "Margin Currency",
        4: "Deposit Currency",
        5: "Annual Interest (Current)",
        6: "Annual Interest (Open Price)",
        7: "Reopen Current",
        8: "Reopen Bid",
    }

    WEEKDAYS = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    }

    def __init__(
        self,
        path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        timeout_ms: int = 60000,
        portable: bool = False,
    ):
        self.path = path
        self.login = login
        self.password = password
        self.server = server
        self.timeout_ms = timeout_ms
        self.portable = portable
        self.is_connected = False

        if self.password:
            register_secret_to_mask(self.password)
        if self.login:
            register_secret_to_mask(str(self.login))

    def connect(self) -> bool:
        """Initialize connection to MT5 terminal."""
        if mt5 is None:
            raise RuntimeError(
                "MetaTrader5 Python package is not installed! Run `pip install MetaTrader5`."
            )

        app_logger.info("Initializing MetaTrader 5 connection...")

        init_kwargs: Dict[str, Any] = {"timeout": self.timeout_ms, "portable": self.portable}
        if self.path:
            init_kwargs["path"] = self.path

        if self.login and self.password and self.server:
            init_kwargs["login"] = int(self.login)
            init_kwargs["password"] = self.password
            init_kwargs["server"] = self.server
            app_logger.info(
                f"Attempting login to account #{self.login} on server '{self.server}'..."
            )

        initialized = mt5.initialize(**init_kwargs)

        if not initialized:
            error_code, error_desc = mt5.last_error()
            app_logger.warning(
                f"MT5 initialize with explicit credentials failed (Code: {error_code}, Desc: {error_desc}). "
                "Attempting fallback attach to active running MT5 terminal instance..."
            )
            if self.path:
                initialized = mt5.initialize(path=self.path, timeout=self.timeout_ms)
            else:
                initialized = mt5.initialize(timeout=self.timeout_ms)

            if not initialized:
                err_code, err_desc = mt5.last_error()
                app_logger.error(
                    f"Fallback MT5 connection also failed! Code: {err_code}, Description: {err_desc}"
                )
                return False
            app_logger.info("Successfully attached to active running MT5 terminal instance.")

        terminal_info = mt5.terminal_info()
        terminal_name = terminal_info.name if terminal_info else "Unknown"
        app_logger.info(f"Successfully connected to MT5 ({terminal_name})")
        self.is_connected = True
        return True

    def initialize(self) -> bool:
        """Alias for connect() for standard API consistency."""
        return self.connect()

    def login(self) -> bool:
        """Alias checking connection and authentication status."""
        return self.is_connected or self.connect()

    def get_account_info(self) -> Any:
        """Fetch MT5 AccountInfo object (or fallback to AccountSnapshot)."""
        if mt5 is not None:
            acc = mt5.account_info()
            if acc is not None:
                return acc
        return self.get_account_snapshot()

    def get_account_snapshot(self) -> Optional[AccountSnapshot]:
        """Fetch current account status, balance, equity, and leverage."""
        if not self.is_connected:
            raise ConnectionError("MT5 is not connected! Call connect() first.")

        acc = mt5.account_info()
        if acc is None:
            err = mt5.last_error()
            app_logger.error(f"Failed to retrieve account info: {err}")
            return None

        trade_modes = {0: "DEMO", 1: "CONTEST", 2: "REAL"}
        mode_str = trade_modes.get(acc.trade_mode, f"UNKNOWN({acc.trade_mode})")

        return AccountSnapshot(
            login=acc.login,
            trade_mode=mode_str,
            name=acc.name,
            server=acc.server,
            currency=acc.currency,
            leverage=acc.leverage,
            balance=acc.balance,
            equity=acc.equity,
            profit=acc.profit,
            margin=acc.margin,
            margin_free=acc.margin_free,
            margin_level=acc.margin_level,
        )

    def find_actual_symbol(self, candidates: List[str]) -> Optional[str]:
        """Check list of candidate symbol names (e.g. XAUUSD, XAUUSDm) and return the available one."""
        if not self.is_connected:
            raise ConnectionError("MT5 is not connected!")

        for symbol_name in candidates:
            info = mt5.symbol_info(symbol_name)
            if info is not None:
                if not info.visible:
                    mt5.symbol_select(symbol_name, True)
                app_logger.info(f"Verified active trading symbol: '{symbol_name}'")
                return symbol_name

        all_symbols = mt5.symbols_get()
        if all_symbols:
            for s in all_symbols:
                if "XAUUSD" in s.name.upper():
                    mt5.symbol_select(s.name, True)
                    app_logger.info(f"Discovered matching symbol from broker list: '{s.name}'")
                    return s.name

        app_logger.warning(f"Could not find any symbol matching candidates: {candidates}")
        return None

    def get_live_tick(self, symbol_name: str) -> Optional[LiveTick]:
        """Calculate real-time spread from actual live tick (ask - bid) in points and price units."""
        if not self.is_connected:
            raise ConnectionError("MT5 is not connected!")

        info = mt5.symbol_info(symbol_name)
        if info is None:
            return None

        tick = mt5.symbol_info_tick(symbol_name)
        if tick is None or tick.bid <= 0 or tick.ask <= 0:
            return None

        point = info.point if info.point > 0 else 0.001
        spread_price = round(tick.ask - tick.bid, info.digits)
        spread_points = round((tick.ask - tick.bid) / point, 1)

        return LiveTick(
            bid=tick.bid,
            ask=tick.ask,
            spread_price=spread_price,
            spread_points=spread_points,
            time=int(tick.time),
        )

    def get_symbol_specification(self, symbol_name: str) -> Optional[SymbolSpecification]:
        """Extract complete trading specifications, real swap impact, and contract parameters."""
        if not self.is_connected:
            raise ConnectionError("MT5 is not connected!")

        info = mt5.symbol_info(symbol_name)
        if info is None:
            err = mt5.last_error()
            app_logger.error(f"symbol_info('{symbol_name}') failed: {err}")
            return None

        trade_modes = {
            0: "DISABLED",
            1: "LONGONLY",
            2: "SHORTONLY",
            3: "CLOSEONLY",
            4: "FULL",
        }
        trade_mode_str = trade_modes.get(info.trade_mode, f"UNKNOWN({info.trade_mode})")

        swap_mode_desc = self.SWAP_MODES.get(info.swap_mode, f"Custom({info.swap_mode})")
        rollover_day_desc = self.WEEKDAYS.get(
            info.swap_rollover3days, f"Day {info.swap_rollover3days}"
        )

        # Calculate estimated overnight USD swap for 1.0 standard lot
        # For points mode (1): swap_points * tick_value_per_point * volume
        # Or swap_points * point * contract_size
        point = info.point if info.point > 0 else 0.001
        tick_val = info.trade_tick_value if info.trade_tick_value > 0 else 1.0
        tick_sz = info.trade_tick_size if info.trade_tick_size > 0 else 0.001

        if info.swap_mode == 1:  # SYMBOL_SWAP_MODE_POINTS
            # 1 point worth = (point / tick_sz) * tick_val
            usd_per_point_1lot = (point / tick_sz) * tick_val
            swap_long_usd = round(info.swap_long * usd_per_point_1lot, 2)
            swap_short_usd = round(info.swap_short * usd_per_point_1lot, 2)
        elif info.swap_mode == 4:  # Deposit currency directly
            swap_long_usd = round(info.swap_long, 2)
            swap_short_usd = round(info.swap_short, 2)
        else:
            swap_long_usd = round(info.swap_long, 2)
            swap_short_usd = round(info.swap_short, 2)

        spec = SymbolSpecification(
            name=info.name,
            visible=info.visible,
            path=info.path,
            digits=info.digits,
            point=info.point,
            spread_raw=info.spread,
            trade_mode=trade_mode_str,
            contract_size=info.trade_contract_size,
            tick_size=info.trade_tick_size,
            tick_value=info.trade_tick_value,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
            stops_level=info.trade_stops_level,
            swap_mode=info.swap_mode,
            swap_mode_desc=swap_mode_desc,
            swap_long=info.swap_long,
            swap_short=info.swap_short,
            swap_rollover3days=info.swap_rollover3days,
            swap_rollover3days_desc=rollover_day_desc,
            swap_long_usd_per_lot=swap_long_usd,
            swap_short_usd_per_lot=swap_short_usd,
        )
        return spec

    def calc_trade_impact(
        self, symbol_name: str, test_price: Optional[float] = None
    ) -> Optional[TradeImpactCalc]:
        """Calculate exact required margin and P&L for $1 price move using broker order_calc API."""
        if not self.is_connected:
            raise ConnectionError("MT5 is not connected!")

        info = mt5.symbol_info(symbol_name)
        if info is None:
            return None

        price = test_price
        if price is None:
            tick = mt5.symbol_info_tick(symbol_name)
            price = tick.ask if tick and tick.ask > 0 else 2700.0

        # Margin calculation for 1.0 lot and 0.01 lot
        margin_1 = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol_name, 1.0, price)
        margin_001 = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol_name, 0.01, price)

        # Profit calculation for $1.00 move upwards
        profit_1 = mt5.order_calc_profit(
            mt5.ORDER_TYPE_BUY, symbol_name, 1.0, price, price + 1.0
        )
        profit_001 = mt5.order_calc_profit(
            mt5.ORDER_TYPE_BUY, symbol_name, 0.01, price, price + 1.0
        )

        return TradeImpactCalc(
            margin_1_lot=round(margin_1 or 0.0, 2),
            margin_001_lot=round(margin_001 or 0.0, 2),
            profit_1_lot_1usd_move=round(profit_1 or 0.0, 2),
            profit_001_lot_1usd_move=round(profit_001 or 0.0, 2),
            tick_value=info.trade_tick_value,
        )

    def update_symbols_config_from_mt5(
        self, yaml_path: str, symbol_name: str, spec: SymbolSpecification
    ) -> None:
        """Update config/symbols.yaml with confirmed live broker instrument specifications."""
        path = Path(yaml_path)
        if not path.exists():
            return

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        sym_sec = data.get("symbol", {})
        sym_sec["base_symbol"] = symbol_name
        sym_sec["active_symbol"] = symbol_name
        sym_sec["path"] = spec.path
        sym_sec["digits"] = spec.digits
        sym_sec["point"] = spec.point
        sym_sec["expected_contract_size"] = spec.contract_size
        sym_sec["tick_size"] = spec.tick_size
        sym_sec["tick_value"] = spec.tick_value
        sym_sec["volume_min"] = spec.volume_min
        sym_sec["volume_max"] = spec.volume_max
        sym_sec["volume_step"] = spec.volume_step
        sym_sec["stops_level"] = spec.stops_level
        sym_sec["swap_mode"] = spec.swap_mode_desc
        sym_sec["swap_long_usd_per_lot"] = spec.swap_long_usd_per_lot
        sym_sec["swap_short_usd_per_lot"] = spec.swap_short_usd_per_lot
        sym_sec["triple_swap_day"] = spec.swap_rollover3days_desc

        data["symbol"] = sym_sec

        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        app_logger.info(
            f"Updated {yaml_path} with live broker specifications for '{symbol_name}'"
        )

    def disconnect(self) -> None:
        """Safely shutdown MT5 connection."""
        if mt5 is not None and self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            app_logger.info("MT5 connection closed gracefully.")
