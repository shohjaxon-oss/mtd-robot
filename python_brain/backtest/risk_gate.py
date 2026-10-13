"""RiskGate protocol and production risk validation gate for backtesting and live trading.

Enforces:
- Compulsory Stop Loss check (zero tolerance for naked trades).
- Fractional capital risk sizing (0.5% per trade default).
- Strict daily (-2.0%), weekly (-4.0%), and overall account kill-switch (-12.0%) drawdown blocks.
- A4: Configurable halt_on_kill_switch (disabled during strategy discovery to measure full history).
- A8: Strict min-lot risk guard (rejects if forced min_lot exceeds 1.5x risk tolerance).
- Margin availability and single-position execution guard.
"""

from abc import ABC, abstractmethod
from typing import Optional
from python_brain.backtest.models import AccountState, Order, OrderSide, Signal


class RiskGate(ABC):
    """Abstract interface for risk approval. Backtest and live engine share this exact contract."""

    @abstractmethod
    def approve(
        self,
        signal: Signal,
        execution_price: float,
        account: AccountState,
        point: float = 0.001,
        contract_size: float = 100.0,
    ) -> Optional[Order]:
        """Validates signal against risk constraints and returns sized Order or None if rejected."""
        pass


class DefaultRiskGate(RiskGate):
    """Production implementation of Phase 6/10 risk parameters for backtesting."""

    def __init__(
        self,
        risk_per_trade_pct: float = 0.5,
        max_daily_loss_pct: float = 2.0,
        max_weekly_loss_pct: float = 4.0,
        kill_switch_dd_pct: float = 12.0,
        halt_on_kill_switch: bool = False,  # A4: Disabled during strategy discovery, enabled in live/risk tests
        max_risk_tolerance_multiplier: float = 1.5,  # A8: Max allowable risk multiplier on forced min-lot
        max_open_positions: int = 1,
        min_lot: float = 0.01,
        max_lot: float = 500.0,
        step_lot: float = 0.01,
        require_stop_loss: bool = True,
    ):
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_weekly_loss_pct = max_weekly_loss_pct
        self.kill_switch_dd_pct = kill_switch_dd_pct
        self.halt_on_kill_switch = halt_on_kill_switch
        self.max_risk_tolerance_multiplier = max_risk_tolerance_multiplier
        self.max_open_positions = max_open_positions
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.step_lot = step_lot
        self.require_stop_loss = require_stop_loss
        self.order_counter = 1

    def approve(
        self,
        signal: Signal,
        execution_price: float,
        account: AccountState,
        point: float = 0.001,
        contract_size: float = 100.0,
    ) -> Optional[Order]:
        if signal.action not in ["BUY", "SELL"]:
            return None

        # 1. Position limit (counted per setup/group)
        active_groups = {pos.group_id for pos in account.open_positions if pos.group_id}
        single_positions = [pos for pos in account.open_positions if not pos.group_id]
        total_active_setups = len(active_groups) + len(single_positions)
        if total_active_setups >= self.max_open_positions:
            return None

        # 2. Stop Loss mandatory check
        if self.require_stop_loss and (signal.sl is None or signal.sl <= 0):
            return None

        # 3. Overall Portfolio Kill-Switch check (-12.0% DD)
        if self.halt_on_kill_switch and account.max_equity_drawdown_pct >= self.kill_switch_dd_pct:
            return None

        # 4. Daily drawdown limit check (-2.0%)
        daily_loss_pct = abs(min(0.0, account.daily_realized_pnl)) / account.initial_balance * 100.0
        if self.halt_on_kill_switch and daily_loss_pct >= self.max_daily_loss_pct:
            return None

        # 5. Weekly drawdown limit check (-4.0%)
        weekly_loss_pct = abs(min(0.0, account.weekly_realized_pnl)) / account.initial_balance * 100.0
        if self.halt_on_kill_switch and weekly_loss_pct >= self.max_weekly_loss_pct:
            return None

        # 6. Sizing and Risk Checks
        sl_distance_price = abs(execution_price - signal.sl)
        if sl_distance_price <= 0:
            return None

        loss_per_1lot = sl_distance_price * contract_size
        if loss_per_1lot <= 0:
            return None

        # MULTI-LEG SETUP (Fixed Lot per leg, Atomic Approval)
        if signal.legs and len(signal.legs) > 0:
            total_volume = round(sum(leg.volume for leg in signal.legs), 2)
            actual_risk_usd = total_volume * loss_per_1lot
            # Hard limit: max_allowed_risk_per_trade_pct (1.0% of balance)
            max_allowed_risk_pct = getattr(self, "max_allowed_risk_per_trade_pct", 1.0)
            max_allowed_risk_usd = account.balance * (max_allowed_risk_pct / 100.0)
            if actual_risk_usd > max_allowed_risk_usd:
                return None  # Total setup risk exceeds max allowed tolerance

            required_margin = (execution_price * contract_size * total_volume) / account.leverage
            effective_free_margin = account.free_margin if account.free_margin > 0 else account.balance
            if required_margin > effective_free_margin * 0.90:
                return None

            order = Order(
                order_id=self.order_counter,
                symbol="XAUUSDm",
                side=OrderSide.BUY if signal.action == "BUY" else OrderSide.SELL,
                volume=total_volume,
                requested_price=execution_price,
                sl=signal.sl,
                tp=signal.tp,
                time_utc=signal.time_utc,
                comment=signal.comment,
                legs=signal.legs,
                group_id=signal.group_id,
            )
            self.order_counter += 1
            return order

        # SINGLE LEG (Fractional risk sizing)
        risk_capital_usd = account.balance * (self.risk_per_trade_pct / 100.0)
        raw_lot = risk_capital_usd / loss_per_1lot

        # Round down to valid lot step
        steps = int(raw_lot / self.step_lot)
        sized_lot = round(steps * self.step_lot, 2)

        # Clamping
        if sized_lot < self.min_lot:
            sized_lot = self.min_lot
        if sized_lot > self.max_lot:
            sized_lot = self.max_lot

        # A8: Min lot risk guard
        actual_risk_usd = sized_lot * loss_per_1lot
        max_allowed_risk_usd = risk_capital_usd * self.max_risk_tolerance_multiplier
        if actual_risk_usd > max_allowed_risk_usd:
            return None

        # 7. Margin availability check
        required_margin = (execution_price * contract_size * sized_lot) / account.leverage
        effective_free_margin = account.free_margin if account.free_margin > 0 else account.balance
        if required_margin > effective_free_margin * 0.90:
            return None

        order = Order(
            order_id=self.order_counter,
            symbol="XAUUSDm",
            side=OrderSide.BUY if signal.action == "BUY" else OrderSide.SELL,
            volume=sized_lot,
            requested_price=execution_price,
            sl=signal.sl,
            tp=signal.tp,
            time_utc=signal.time_utc,
            comment=signal.comment,
        )
        self.order_counter += 1
        return order
