"""High-fidelity event-driven backtesting engine for XAUUSDm trading systems.

Strict execution guarantees:
1. Zero-Lookahead: Signal generated on bar t close is strictly executed at bar t+1 OPEN.
2. Bid/Ask Mechanics: Buy opens at Ask (Open + Spread), Sells at Bid (Open).
   Buy SL/TP evaluated against Bid prices; Sell SL/TP evaluated against Ask prices.
3. Conservative Intrabar Conflict Resolution: If both SL and TP are touched within the same bar,
   STOP LOSS is unconditionally executed first.
4. Realistic Multi-factor Costs:
   - A1: Single accounting of Swap and Commission (no double-deduction).
   - A2: Rollover blackout strictly enforced at execution bar open time (21:00-22:00 UTC).
   - A3: Gap-down/Gap-up Stop Loss fill protection (min/max with bar_open + slippage).
   - A5: Configurable spread modes (auto, median, mean, p95 stress, empirical sample).
   - A6: Intrabar worst-point equity drawdown tracking.
   - A9: Full economic news blackout calendar integration.
"""

from datetime import datetime
from typing import Any, List, Optional
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
        calendar: Optional[Any] = None,  # NewsCalendar or None (A9)
        news_before_minutes: int = 15,
        news_after_minutes: int = 15,
        lookback_bars: int = 300,
    ):
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.contract_size = contract_size
        self.point = point
        self.stop_out_level_pct = stop_out_level_pct
        self.calendar = calendar
        self.news_before_minutes = news_before_minutes
        self.news_after_minutes = news_after_minutes
        self.lookback_bars = lookback_bars

    def run(
        self,
        df: pd.DataFrame,
        strategy: Strategy,
        risk_gate: Optional[RiskGate] = None,
        cost_model: Optional[CostModel] = None,
        stress_multiplier: Optional[float] = None,
    ) -> AccountState:
        """Execute full event-driven simulation over the provided candle history."""
        if df.empty:
            raise ValueError("Input candle DataFrame is empty!")

        gate = risk_gate or DefaultRiskGate()
        costs = cost_model or CostModel(point=self.point, contract_size=self.contract_size)
        if stress_multiplier is not None:
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

            # Day and week tracking for drawdown limits
            bar_date_str = bar_time.strftime("%Y-%m-%d")
            bar_week_num = bar_time.isocalendar()[1]

            if prev_date is not None and bar_date_str != prev_date:
                account.daily_realized_pnl = 0.0

            if prev_week is not None and bar_week_num != prev_week:
                account.weekly_realized_pnl = 0.0

            prev_date = bar_date_str
            prev_week = bar_week_num

            # A9: Check Economic News Blackout window
            is_news_blackout = False
            if self.calendar is not None:
                is_news_blackout = self.calendar.is_blackout(
                    bar_time,
                    before_minutes=self.news_before_minutes,
                    after_minutes=self.news_after_minutes,
                )

            # Calculate effective spread for this bar
            spread_pts, spread_price = costs.get_effective_spread(
                time_utc=bar_time,
                bar_spread=bar_spread,
                is_news_blackout=is_news_blackout,
            )

            # -------------------------------------------------------------
            # STEP 1: EXECUTE PENDING ORDER FROM PREVIOUS BAR CLOSE
            # Strictly executed at current bar OPEN
            # -------------------------------------------------------------
            if pending_signal is not None:
                # A2: Rollover blackout check on EXECUTION BAR OPEN TIME
                # 21:00-22:00 UTC da yangi pozitsiya ochilmasin
                is_rollover_now = bar_time.hour in [21, 22]

                # A9: News blackout check on execution time
                if is_rollover_now or is_news_blackout:
                    # Cancel pending signal during blackout illiquidity
                    pending_signal = None
                else:
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
                        if pending_signal.legs and len(pending_signal.legs) > 0:
                            # Multi-leg setup execution
                            group_id = pending_signal.group_id or f"GRP_{current_ticket}"
                            pip_size = getattr(pending_signal, "pip_size_price", 0.10)
                            for leg in pending_signal.legs:
                                if leg.tp is not None:
                                    leg_tp = leg.tp
                                elif leg.tp_pips is not None:
                                    leg_tp = round(
                                        exec_price + (leg.tp_pips * pip_size) if is_buy else exec_price - (leg.tp_pips * pip_size),
                                        3,
                                    )
                                else:
                                    leg_tp = None

                                pos = Position(
                                    ticket=current_ticket,
                                    symbol="XAUUSDm",
                                    side=approved_order.side,
                                    volume=leg.volume,
                                    open_price=round(exec_price, 3),
                                    open_time_utc=bar_time,
                                    sl=approved_order.sl,
                                    tp=leg_tp,
                                    comment=f"{approved_order.comment}|{leg.leg_id}" if leg.leg_id else approved_order.comment,
                                    commission=costs.calculate_commission(leg.volume),
                                    spread_cost=spread_price * self.contract_size * leg.volume,
                                    group_id=group_id,
                                    leg_id=leg.leg_id,
                                    breakeven_on_first_tp=pending_signal.breakeven_on_first_tp,
                                    original_sl=approved_order.sl,
                                )
                                current_ticket += 1
                                account.open_positions.append(pos)
                        else:
                            commission = costs.calculate_commission(approved_order.volume)
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

            def finalize_close(p: Position, c_price: float, exit_r: ExitReason):
                p.is_closed = True
                p.close_price = round(c_price, 3)
                p.close_time_utc = bar_time
                p.exit_reason = exit_r

                if p.side == OrderSide.BUY:
                    price_diff = p.close_price - p.open_price
                else:
                    price_diff = p.open_price - p.close_price

                gross_pnl = price_diff * self.contract_size * p.volume
                p.gross_pnl = round(gross_pnl + p.slippage_cost + p.spread_cost, 2)
                p.realized_pnl = round(gross_pnl + p.accumulated_swap - p.commission, 2)

                account.balance += p.realized_pnl
                account.daily_realized_pnl += p.realized_pnl
                account.weekly_realized_pnl += p.realized_pnl
                account.closed_positions.append(p)

            # Separate multi-leg groups vs standalone positions
            groups: Dict[str, List[Position]] = {}
            standalone: List[Position] = []
            for p in account.open_positions:
                if p.group_id and p.breakeven_on_first_tp:
                    groups.setdefault(p.group_id, []).append(p)
                else:
                    standalone.append(p)

            # Evaluate multi-leg groups
            for gid, legs in groups.items():
                legs.sort(key=lambda x: x.leg_id or "")
                # Both Leg A and Leg B open
                if len(legs) >= 2:
                    leg_a, leg_b = legs[0], legs[1]
                    is_buy = leg_a.side == OrderSide.BUY

                    ask_open = bar_open + spread_price
                    ask_high = bar_high + spread_price
                    ask_low = bar_low + spread_price

                    if is_buy:
                        hit_initial_sl = bar_low <= leg_a.sl
                        hit_tp_a = (leg_a.tp is not None) and (bar_high >= leg_a.tp)
                        hit_tp_b = (leg_b.tp is not None) and (bar_high >= leg_b.tp)
                    else:
                        hit_initial_sl = ask_high >= leg_a.sl
                        hit_tp_a = (leg_a.tp is not None) and (ask_low <= leg_a.tp)
                        hit_tp_b = (leg_b.tp is not None) and (ask_low <= leg_b.tp)

                    # (iv) Boshlang'ich SL tegsa, ikkala leg ham SL da yopiladi
                    if hit_initial_sl:
                        for leg in [leg_a, leg_b]:
                            if hit_tp_a or hit_tp_b:
                                leg.is_ambiguous_exit = True
                            slip = costs.get_slippage_penalty(leg.side.value, True, spread_price, local_atr)
                            leg.slippage_cost = round(slip * self.contract_size * leg.volume, 2)
                            fill_base = min(leg.sl, bar_open) if is_buy else max(leg.sl, ask_open)
                            c_price = fill_base - slip if is_buy else fill_base + slip
                            finalize_close(leg, c_price, ExitReason.STOP_LOSS)
                    elif hit_tp_a:
                        # Leg A TP da yopiladi
                        finalize_close(leg_a, leg_a.tp, ExitReason.TAKE_PROFIT)

                        # (iii) Bitta barda TP_A va TP_B ikkalasiga tegsa
                        if hit_tp_b:
                            retraced = (bar_low <= leg_b.open_price) if is_buy else (ask_high >= leg_b.open_price)
                            if retraced:
                                # B breakeven da yopilgan hisoblanadi va setup ambiguous bo'ladi
                                slip = costs.get_slippage_penalty(leg_b.side.value, True, spread_price, local_atr)
                                leg_b.slippage_cost = round(slip * self.contract_size * leg_b.volume, 2)
                                fill_base = min(leg_b.open_price, bar_open) if is_buy else max(leg_b.open_price, ask_open)
                                c_price = fill_base - slip if is_buy else fill_base + slip
                                leg_b.is_ambiguous_exit = True
                                finalize_close(leg_b, c_price, ExitReason.STOP_LOSS)
                            else:
                                finalize_close(leg_b, leg_b.tp, ExitReason.TAKE_PROFIT)
                        else:
                            # (ii) Breakeven SL keyingi bardan kuchga kiradi
                            leg_b.sl = leg_b.open_price
                            leg_b.breakeven_activated = True
                            active_positions.append(leg_b)
                    else:
                        # Neither initial SL nor TP_A hit
                        active_positions.append(leg_a)
                        active_positions.append(leg_b)

                elif len(legs) == 1:
                    # Only one leg remaining (Leg B with BE active)
                    standalone.append(legs[0])

            # Evaluate standalone positions (and remaining single legs)
            for pos in standalone:
                is_closed = False
                close_price = 0.0
                reason = None

                if pos.side == OrderSide.BUY:
                    hit_sl = bar_low <= pos.sl
                    hit_tp = (pos.tp is not None) and (bar_high >= pos.tp)

                    if hit_sl and hit_tp:
                        pos.is_ambiguous_exit = True

                    if hit_sl:
                        slip = costs.get_slippage_penalty("BUY", True, spread_price, local_atr)
                        pos.slippage_cost = round(slip * self.contract_size * pos.volume, 2)
                        fill_base = min(pos.sl, bar_open)
                        close_price = fill_base - slip
                        reason = ExitReason.STOP_LOSS
                        is_closed = True
                    elif hit_tp:
                        close_price = pos.tp
                        reason = ExitReason.TAKE_PROFIT
                        is_closed = True

                else:  # SELL Position
                    ask_open = bar_open + spread_price
                    ask_high = bar_high + spread_price
                    ask_low = bar_low + spread_price

                    hit_sl = ask_high >= pos.sl
                    hit_tp = (pos.tp is not None) and (ask_low <= pos.tp)

                    if hit_sl and hit_tp:
                        pos.is_ambiguous_exit = True

                    if hit_sl:
                        slip = costs.get_slippage_penalty("SELL", True, spread_price, local_atr)
                        pos.slippage_cost = round(slip * self.contract_size * pos.volume, 2)
                        fill_base = max(pos.sl, ask_open)
                        close_price = fill_base + slip
                        reason = ExitReason.STOP_LOSS
                        is_closed = True
                    elif hit_tp:
                        close_price = pos.tp
                        reason = ExitReason.TAKE_PROFIT
                        is_closed = True

                if is_closed:
                    finalize_close(pos, close_price, reason)
                else:
                    active_positions.append(pos)

            # Update swap & mark-to-market valuation for all remaining active positions
            for pos in active_positions:
                if bar_time.hour == 0 and bar_time.minute == 0:
                    swap_cost = costs.calculate_swap(pos.side.value, pos.volume, bar_time)
                    pos.accumulated_swap += swap_cost

                current_bid = bar_close
                current_ask = bar_close + spread_price
                pos.current_price = current_bid if pos.side == OrderSide.BUY else current_ask

                if pos.side == OrderSide.BUY:
                    unrealized = (current_bid - pos.open_price) * self.contract_size * pos.volume
                else:
                    unrealized = (pos.open_price - current_ask) * self.contract_size * pos.volume

                pos.unrealized_pnl = unrealized + pos.accumulated_swap - pos.commission

            account.open_positions = active_positions

            # -------------------------------------------------------------
            # STEP 3: UPDATE ACCOUNT EQUITY, MARGIN & INTRABAR DRAWDOWN (A6)
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

            # A6: Calculate worst intrabar equity for realistic peak-to-trough DD
            intrabar_worst_unrealized = 0.0
            for p in account.open_positions:
                if p.side == OrderSide.BUY:
                    worst_bid = bar_low
                    diff = (worst_bid - p.open_price) * self.contract_size * p.volume
                else:
                    worst_ask = bar_high + spread_price
                    diff = (p.open_price - worst_ask) * self.contract_size * p.volume
                intrabar_worst_unrealized += (diff + p.accumulated_swap - p.commission)

            intrabar_worst_equity = account.balance + intrabar_worst_unrealized
            account.update_peak(current_time=bar_time, intrabar_worst_equity=intrabar_worst_equity)

            # Stop-Out protection
            if total_used_margin > 0 and account.margin_level_pct <= self.stop_out_level_pct:
                for p in account.open_positions:
                    p.is_closed = True
                    p.close_price = bar_close
                    p.close_time_utc = bar_time
                    p.exit_reason = ExitReason.STOP_OUT
                    p.realized_pnl = round(p.unrealized_pnl, 2)
                    account.balance += p.realized_pnl
                    account.closed_positions.append(p)
                account.open_positions = []

            # -------------------------------------------------------------
            # STEP 4: STRATEGY EVALUATION ON BAR CLOSE
            # -------------------------------------------------------------
            # Strategy ONLY sees candles up to bar i (Zero-Lookahead Guarantee)
            start_idx = max(0, i + 1 - self.lookback_bars)
            history_slice = data.iloc[start_idx : i + 1]
            signal = strategy.on_bar(history_slice)

            if signal is not None and signal.action in ["BUY", "SELL"]:
                pending_signal = signal

        return account
