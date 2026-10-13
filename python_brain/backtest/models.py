"""Core data structures and state models for event-driven backtesting."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    SIGNAL_EXIT = "SIGNAL_EXIT"
    KILL_SWITCH = "KILL_SWITCH"
    DAILY_LIMIT = "DAILY_LIMIT"
    STOP_OUT = "STOP_OUT"


@dataclass
class Signal:
    time_utc: datetime
    action: str  # BUY | SELL | CLOSE | HOLD
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = ""


@dataclass
class Order:
    order_id: int
    symbol: str
    side: OrderSide
    volume: float
    requested_price: float
    sl: float
    tp: Optional[float]
    time_utc: datetime
    comment: str = ""


@dataclass
class Position:
    ticket: int
    symbol: str
    side: OrderSide
    volume: float
    open_price: float
    open_time_utc: datetime
    sl: float
    tp: Optional[float]
    comment: str = ""

    # Dynamic tracking
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    accumulated_swap: float = 0.0
    commission: float = 0.0

    # Closure
    is_closed: bool = False
    close_price: Optional[float] = None
    close_time_utc: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    realized_pnl: float = 0.0
    gross_pnl: float = 0.0
    slippage_cost: float = 0.0
    spread_cost: float = 0.0
    is_ambiguous_exit: bool = False


@dataclass
class AccountState:
    initial_balance: float
    balance: float
    equity: float
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level_pct: float = 0.0
    leverage: float = 2000.0

    # Drawdown tracking
    peak_equity: float = 0.0
    peak_balance: float = 0.0
    max_equity_drawdown_pct: float = 0.0
    max_balance_drawdown_pct: float = 0.0

    # P&L tracking
    daily_realized_pnl: float = 0.0
    weekly_realized_pnl: float = 0.0
    current_day: Optional[str] = None
    current_week: Optional[str] = None

    # Kill-switch audit tracking (A4)
    kill_switch_triggered: bool = False
    kill_switch_triggered_at: Optional[datetime] = None

    open_positions: List[Position] = field(default_factory=list)
    closed_positions: List[Position] = field(default_factory=list)

    def update_peak(self, current_time: Optional[datetime] = None, intrabar_worst_equity: Optional[float] = None) -> None:
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance

        # A6: Intrabar worst equity or close equity for maximum realistic DD
        evaluated_equity = intrabar_worst_equity if (intrabar_worst_equity is not None and intrabar_worst_equity < self.equity) else self.equity

        if self.peak_equity > 0:
            dd_eq = (self.peak_equity - evaluated_equity) / self.peak_equity * 100.0
            if dd_eq > self.max_equity_drawdown_pct:
                self.max_equity_drawdown_pct = dd_eq

        if self.peak_balance > 0:
            dd_bal = (self.peak_balance - self.balance) / self.peak_balance * 100.0
            if dd_bal > self.max_balance_drawdown_pct:
                self.max_balance_drawdown_pct = dd_bal

        # A4: Record first kill-switch trigger timestamp
        if not self.kill_switch_triggered and self.max_equity_drawdown_pct >= 12.0:
            self.kill_switch_triggered = True
            self.kill_switch_triggered_at = current_time
