"""High-fidelity event-driven backtesting engine for XAUUSDm trading systems.

Strict execution guarantees:
1. Zero-Lookahead: Signal generated on bar t close is strictly executed at bar t+1 OPEN.
2. Bid/Ask Mechanics: Buy opens at Ask (Open + Spread), Sells at Bid (Open).
   Buy SL/TP evaluated against Bid prices; Sell SL/TP evaluated against Ask prices.
3. Conservative Intrabar Conflict Resolution: If both SL and TP are touched within the same bar,
   STOP LOSS is unconditionally executed first.
4. Dynamic Costs: Realistic time-dependent spreads, slippage on stops, and overnight holding swaps.
5. RiskGate integration: Every pending order must pass strict risk constraints before execution.
"""

from datetime import datetime
from typing import List, Optional
import numpy as np
import pandas as pd
from python_brain.backtest.costs import CostModel
from python_brain.backtest.models import (
    AccountState,
    ExitReason,
    Order,
    OrderSide,
    Position,
    Signal,
)
from python_brain.backtest.risk_gate import DefaultRiskGate, RiskGate
from python_brain.backtest.strategy_base import Strategy


class BacktestEngine:
    """Event-driven simulator enforcing real-market execution physics."""

    def __init__(
        self,
        initial_balance: float = 10000.0,
        leverage: float = 2000.0,
        contract_size: float = 100.0,
        point: float = 0.001,
        stop_out_level_pct: float = 20.0,
    ):
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.contract_size = contract_size
        self.point = point
        self.stop_out_level_pct = stop_out_level_pct

    def run(
        self,
        df: pd.DataFrame,
        strategy: Strategy,
        risk_gate: Optional[RiskGate] = None,
        cost_model: Optional[CostModel] = None,
        stress_multiplier: float = 1.0,
    ) -> AccountState:
        """Execute full event-driven simulation over the provided candle history."""
        if df.empty:
            raise ValueError("Input candle DataFrame is empty!")

        gate = risk_gate or DefaultRiskGate()
        costs = cost_model or CostModel(point=self.point, contract_size=self.contract_size)
        costs.stress_multiplier = stress_multiplier

        account = AccountState(
            initial_balance=self.initial_balance,
            balance=self.initial_balance,
            equity=self.initial_balance,
            free_margin=self.initial_balance,
            peak_balance=self.initial_balance,
            peak_equity=self.initial_balance,
            leverage=self.leverage,
        )

        pending_signal: Optional[Signal] = None
        current_ticket = 1000
        prev_date: Optional[str] = None
        prev_week: Optional[int] = None

        data = df.copy().reset_index(drop=True)
        data["time_utc"] = pd.to_datetime(data["time_utc"])
        total_bars = len(data)

        # Precompute local ATR for slippage modeling
        tr = np.maximum(
            data["high"] - data["low"],
            np.maximum(
                np.abs(data["high"] - data["close"].shift(1).fillna(data["open"])),
                np.abs(data["low"] - data["close"].shift(1).fillna(data["open"])),
            ),
        )
        atr_14 = tr.rolling(14, min_periods=1).mean().values

        for i in range(total_bars):
            bar = data.iloc[i]
            bar_time: datetime = bar["time_utc"].to_pydatetime()
            bar_open: float = float(bar["open"])
            bar_high: float = float(bar["high"])
            bar_low: float = float(bar["low"])
            bar_close: float = float(bar["close"])
            bar_spread: float = float(bar["spread"]) if "spread" in bar else 240.0
            local_atr: float = float(atr_14[i])

            # Day and week rollover tracking for drawdown limits
            bar_date_str = bar_time.strftime("%Y-%m-%d")
            bar_week_num = bar_time.isocalendar()[1]

            if prev_date is not None and bar_date_str != prev_date:
                # Reset daily realized P&L
                account.daily_realized_pnl = 0.0

            if prev_week is not None and bar_week_num != prev_week:
                # Reset weekly realized P&L
                account.weekly_realized_pnl = 0.0

            prev_date = bar_date_str
            prev_week = bar_week_num

            # Calculate effective spread and price units for this bar
            spread_pts, spread_price = costs.get_effective_spread(bar_time, bar_spread)

            # -------------------------------------------------------------
            # STEP 1: EXECUTE PENDING ORDER FROM PREVIOUS BAR CLOSE
            # Strictly executed at current bar OPEN
            # -------------------------------------------------------------
            if pending_signal is not None:
                is_buy = pending_signal.action == "BUY"
                exec_price = bar_open + spread_price if is_buy else bar_open

                approved_order = gate.approve(
                    signal=pending_signal,
                    execution_price=exec_price,
                    account=account,
                    point=self.point,
                    contract_size=self.contract_size,
                )

                if approved_order is not None:
                    commission = costs.calculate_commission(approved_order.volume)
                    account.balance -= commission

                    pos = Position(
                        ticket=current_ticket,
                        symbol="XAUUSDm",
                        side=approved_order.side,
                        volume=approved_order.volume,
                        open_price=round(exec_price, 3),
                        open_time_utc=bar_time,
                        sl=approved_order.sl,
                        tp=approved_order.tp,
                        comment=approved_order.comment,
                        commission=commission,
                        spread_cost=spread_price * self.contract_size * approved_order.volume,
                    )
                    current_ticket += 1
                    account.open_positions.append(pos)

                pending_signal = None  # Consumed

            # -------------------------------------------------------------
            # STEP 2: CHECK SL / TP / MARGIN STOPS ON OPEN POSITIONS
            # -------------------------------------------------------------
            active_positions: List[Position] = []

            for pos in account.open_positions:
                is_closed = False
                close_price = 0.0
                reason = None
                is_stop_out = False

                if pos.side == OrderSide.BUY:
                    # Buy SL/TP are triggered by Bid price
                    # Conservatism rule: Check SL first!
                    hit_sl = bar_low <= pos.sl
                    hit_tp = (pos.tp is not None) and (bar_high >= pos.tp)

                    if hit_sl:
                        # Slippage applies to Stop Loss
                        slip = costs.get_slippage_penalty("BUY", True, spread_price, local_atr)
                        close_price = pos.sl - slip
                        reason = ExitReason.STOP_LOSS
                        is_closed = True
                    elif hit_tp:
                        close_price = pos.tp  # TP executed at limit without adverse slippage
                        reason = ExitReason.TAKE_PROFIT
                        is_closed = True

                else:  # SELL Position
                    # Sell SL/TP are triggered by Ask price = Bid + Spread
                    ask_high = bar_high + spread_price
                    ask_low = bar_low + spread_price

                    hit_sl = ask_high >= pos.sl
                    hit_tp = (pos.tp is not None) and (ask_low <= pos.tp)

                    if hit_sl:
                        slip = costs.get_slippage_penalty("SELL", True, spread_price, local_atr)
                        close_price = pos.sl + slip
                        reason = ExitReason.STOP_LOSS
                        is_closed = True
                    elif hit_tp:
                        close_price = pos.tp
                        reason = ExitReason.TAKE_PROFIT
                        is_closed = True

                # Overnight Swap calculation (accumulates if position held past 00:00 UTC)
                if not is_closed and bar_time.hour == 0 and bar_time.minute == 0:
                    swap_cost = costs.calculate_swap(pos.side.value, pos.volume, bar_time)
                    pos.accumulated_swap += swap_cost
                    account.balance += swap_cost  # Adds/deducts swap from balance

                if is_closed:
                    pos.is_closed = True
                    pos.close_price = round(close_price, 3)
                    pos.close_time_utc = bar_time
                    pos.exit_reason = reason

                    # Calculate Realized P&L
                    if pos.side == OrderSide.BUY:
                        price_diff = pos.close_price - pos.open_price
                    else:
                        price_diff = pos.open_price - pos.close_price

                    gross_pnl = price_diff * self.contract_size * pos.volume
                    pos.realized_pnl = round(gross_pnl + pos.accumulated_swap - pos.commission, 2)

                    account.balance += pos.realized_pnl
                    account.daily_realized_pnl += pos.realized_pnl
                    account.weekly_realized_pnl += pos.realized_pnl
                    account.closed_positions.append(pos)
                else:
                    # Update mark-to-market valuation
                    current_bid = bar_close
                    current_ask = bar_close + spread_price
                    pos.current_price = current_bid if pos.side == OrderSide.BUY else current_ask

                    if pos.side == OrderSide.BUY:
                        unrealized = (current_bid - pos.open_price) * self.contract_size * pos.volume
                    else:
                        unrealized = (pos.open_price - current_ask) * self.contract_size * pos.volume

                    pos.unrealized_pnl = unrealized + pos.accumulated_swap
                    active_positions.append(pos)

            account.open_positions = active_positions

            # -------------------------------------------------------------
            # STEP 3: UPDATE ACCOUNT EQUITY, MARGIN & DRAWDOWN
            # -------------------------------------------------------------
            total_unrealized = sum(p.unrealized_pnl for p in account.open_positions)
            account.equity = account.balance + total_unrealized

            total_used_margin = sum(
                (p.open_price * self.contract_size * p.volume) / self.leverage
                for p in account.open_positions
            )
            account.margin = total_used_margin
            account.free_margin = account.equity - total_used_margin
            account.margin_level_pct = (
                (account.equity / total_used_margin * 100.0) if total_used_margin > 0 else 999999.0
            )

            account.update_peak()

            # Stop-Out protection
            if total_used_margin > 0 and account.margin_level_pct <= self.stop_out_level_pct:
                for p in account.open_positions:
                    p.is_closed = True
                    p.close_price = bar_close
                    p.close_time_utc = bar_time
                    p.exit_reason = ExitReason.STOP_OUT
                    p.realized_pnl = p.unrealized_pnl
                    account.balance += p.realized_pnl
                    account.closed_positions.append(p)
                account.open_positions = []

            # -------------------------------------------------------------
            # STEP 4: STRATEGY EVALUATION ON BAR CLOSE
            # -------------------------------------------------------------
            # Strategy ONLY sees candles up to bar i (Zero-Lookahead Guarantee)
            # High-performance slicing: passing recent lookback window (e.g. 300 bars)
            lookback = 300
            start_idx = max(0, i + 1 - lookback)
            history_slice = data.iloc[start_idx : i + 1]
            signal = strategy.on_bar(history_slice)

            if signal is not None and signal.action in ["BUY", "SELL"]:
                # Check Rollover blackout window (UTC 21:00-22:00)
                if bar_time.hour in [21, 22]:
                    # Prohibit new entries during severe illiquidity window
                    pass
                else:
                    pending_signal = signal

        return account
