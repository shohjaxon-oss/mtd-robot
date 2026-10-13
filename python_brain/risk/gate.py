"""Production darajasidagi Birlashtirilgan Risk Gate (1-Band).

Backtest va Jonli (Live/Demo) savdo uchun yagona xavfsizlik qalqoni.
Barcha qat'iy cheklovlarni tekshiradi:
1. Live Guard (faqat DEMO)
2. Umumiy Kill-Switch (-12% Drawdown, SQLite da persistent)
3. Kunlik (-2%) va Haftalik (-4%) zarar limitlari
4. Ketma-ket zararlardan keyingi Cooldown
5. Kunlik maksimal savdolar soni (max_daily_trades)
6. Majburiy Stop Loss
7. Min-lot risk toleransi (A8)
8. Erkin Margin tekshiruvi (order_calc_margin)
9. Live spread filtri (max_spread_points)
10. Rollover blackout (21:00-22:00 UTC) va Yangilik blackout
11. Juma oqshomi xavfsizligi (friday_close_hour_utc)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from loguru import logger

from python_brain.backtest.models import AccountState, Order, OrderSide, Signal
from python_brain.risk.live_guard import LiveGuard
from python_brain.risk.state_store import RiskStateStore


@dataclass
class RiskCheckResult:
    approved: bool
    rejection_reason: Optional[str] = None
    order: Optional[Order] = None


class ProductionRiskGate:
    """Production va Backtest uchun to'liq yagona Risk Gate."""

    def __init__(
        self,
        risk_per_trade_pct: float = 0.5,
        daily_loss_limit_pct: float = 2.0,
        weekly_loss_limit_pct: float = 4.0,
        kill_switch_dd_pct: float = 12.0,
        max_daily_trades: int = 5,
        consecutive_losses_cooldown: int = 3,
        cooldown_minutes: int = 60,
        max_spread_points: float = 40.0,
        max_risk_tolerance_multiplier: float = 1.5,
        friday_close_hour_utc: int = 20,
        min_lot: float = 0.01,
        max_lot: float = 5.0,
        lot_step: float = 0.01,
        state_store: Optional[RiskStateStore] = None,
        live_guard: Optional[LiveGuard] = None,
        halt_on_kill_switch: bool = True,
    ) -> None:
        self.risk_per_trade_pct = risk_per_trade_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.weekly_loss_limit_pct = weekly_loss_limit_pct
        self.kill_switch_dd_pct = kill_switch_dd_pct
        self.max_daily_trades = max_daily_trades
        self.consecutive_losses_cooldown = consecutive_losses_cooldown
        self.cooldown_minutes = cooldown_minutes
        self.max_spread_points = max_spread_points
        self.max_risk_tolerance_multiplier = max_risk_tolerance_multiplier
        self.friday_close_hour_utc = friday_close_hour_utc
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.lot_step = lot_step

        self.state_store = state_store
        self.live_guard = live_guard or LiveGuard(allow_live=False, require_demo=True)
        self.halt_on_kill_switch = halt_on_kill_switch

        # Ichki xotiradagi kunlik hisoblagichlar
        self.last_rejection_reason: Optional[str] = None

    def check(
        self,
        signal: Signal,
        execution_price: float,
        account: AccountState,
        point: float = 0.001,
        contract_size: float = 100.0,
        current_spread_pts: Optional[float] = None,
        is_news_blackout: bool = False,
        raw_account_info: Optional[Any] = None,
    ) -> RiskCheckResult:
        """Har bir signalni qat'iy barcha risk mezonlari bo'yicha tekshiradi."""
        self.last_rejection_reason = None
        now_utc = signal.time_utc if signal.time_utc.tzinfo else signal.time_utc.replace(tzinfo=timezone.utc)

        # 0. Live Guard tekshiruvi (agar jonli account_info berilgan bo'lsa)
        if raw_account_info is not None:
            try:
                self.live_guard.verify_account(raw_account_info)
            except Exception as e:
                return self._reject(f"LIVE_GUARD_BLOCKED: {str(e)}")

        # 1. Kill-Switch Tekshiruvi (Xotira va SQLite)
        if self.state_store is not None:
            persisted = self.state_store.load_state()
            if persisted.get("kill_switch_active", 0) == 1:
                return self._reject(f"KILL_SWITCH_ACTIVE_IN_DB: {persisted.get('kill_switch_reason')}")

        if account.max_equity_drawdown_pct >= self.kill_switch_dd_pct:
            reason = f"MAX_EQUITY_DD_EXCEEDED: {account.max_equity_drawdown_pct:.2f}% >= {self.kill_switch_dd_pct}%"
            if self.state_store is not None:
                self.state_store.activate_kill_switch(reason)
            if self.halt_on_kill_switch:
                return self._reject(reason)

        # 2. Kunlik va Haftalik Zarar Limitlari
        daily_loss_limit = -account.initial_balance * (self.daily_loss_limit_pct / 100.0)
        weekly_loss_limit = -account.initial_balance * (self.weekly_loss_limit_pct / 100.0)

        if account.daily_realized_pnl <= daily_loss_limit:
            return self._reject(f"DAILY_LOSS_LIMIT_REACHED: {account.daily_realized_pnl:.2f} <= {daily_loss_limit:.2f}")

        if account.weekly_realized_pnl <= weekly_loss_limit:
            return self._reject(f"WEEKLY_LOSS_LIMIT_REACHED: {account.weekly_realized_pnl:.2f} <= {weekly_loss_limit:.2f}")

        # 3. Ketma-ket Zararlardan Keyingi Cooldown
        if self.state_store is not None:
            persisted = self.state_store.load_state()
            cooldown_until_str = persisted.get("cooldown_until")
            if cooldown_until_str:
                cooldown_until = datetime.fromisoformat(cooldown_until_str)
                if now_utc < cooldown_until:
                    return self._reject(f"IN_COOLDOWN_UNTIL_{cooldown_until_str}")

        # 4. Maksimal Kunlik Savdolar Soni
        if self.state_store is not None:
            persisted = self.state_store.load_state()
            if persisted.get("current_day") == now_utc.strftime("%Y-%m-%d"):
                if persisted.get("daily_trades_count", 0) >= self.max_daily_trades:
                    return self._reject(f"MAX_DAILY_TRADES_REACHED: {persisted.get('daily_trades_count')} >= {self.max_daily_trades}")

        # 5. Rollover Blackout (21:00-22:00 UTC) va News Blackout
        if now_utc.hour in [21, 22]:
            return self._reject("ROLLOVER_BLACKOUT_HOURS_21_22_UTC")

        if is_news_blackout:
            return self._reject("HIGH_IMPACT_NEWS_BLACKOUT")

        # 6. Juma Oqshomi Savdo Blokirovkasi (Hafta oxiri xavfi)
        # Friday = weekday 4
        if now_utc.weekday() == 4 and now_utc.hour >= self.friday_close_hour_utc:
            return self._reject(f"FRIDAY_WEEKEND_CLOSE_RULE_AFTER_{self.friday_close_hour_utc}_UTC")

        # 7. Live Spread Chegarasi
        if current_spread_pts is not None and current_spread_pts > self.max_spread_points:
            return self._reject(f"SPREAD_TOO_HIGH: {current_spread_pts:.1f} pts > {self.max_spread_points:.1f} pts")

        # 8. Majburiy Stop Loss
        if signal.sl is None or signal.sl <= 0.0:
            return self._reject("MISSING_MANDATORY_STOP_LOSS")

        side = OrderSide.BUY if signal.action == "BUY" else OrderSide.SELL
        sl_distance = (execution_price - signal.sl) if side == OrderSide.BUY else (signal.sl - execution_price)

        if sl_distance <= 0:
            return self._reject(f"INVALID_STOP_LOSS_DIRECTION: Entry={execution_price}, SL={signal.sl}, Side={side}")

        # 9. Dinamik Lot O'lchami Hisoblash (0.5% risk kapitali)
        risk_capital = account.equity * (self.risk_per_trade_pct / 100.0)
        risk_per_lot = sl_distance * contract_size
        calculated_volume = risk_capital / risk_per_lot if risk_per_lot > 0 else self.min_lot

        # Min-lot risk toleransi himoyasi (A8)
        actual_risk_at_min_lot = self.min_lot * risk_per_lot
        max_allowed_risk = risk_capital * self.max_risk_tolerance_multiplier
        if actual_risk_at_min_lot > max_allowed_risk:
            return self._reject(
                f"MIN_LOT_RISK_TOO_HIGH: ${actual_risk_at_min_lot:.2f} > ${max_allowed_risk:.2f} "
                f"(Limit: {self.max_risk_tolerance_multiplier}x of ${risk_capital:.2f})"
            )

        # Lot normallashtirish
        raw_volume = max(self.min_lot, min(self.max_lot, calculated_volume))
        steps = round(raw_volume / self.lot_step)
        final_volume = round(steps * self.lot_step, 2)

        # 10. Margin Tekshiruvi
        required_margin = (execution_price * contract_size * final_volume) / account.leverage
        effective_free_margin = account.free_margin if account.free_margin > 0 else account.equity
        if required_margin >= effective_free_margin:
            return self._reject(f"INSUFFICIENT_FREE_MARGIN: Req=${required_margin:.2f} >= Free=${effective_free_margin:.2f}")

        # Order tasdiqlandi!
        order = Order(
            order_id=1,
            symbol="XAUUSDm",
            side=side,
            volume=final_volume,
            requested_price=execution_price,
            sl=signal.sl,
            tp=signal.tp,
            time_utc=now_utc,
            comment=signal.comment or "MTD_Prod",
        )
        return RiskCheckResult(approved=True, order=order)

    def approve(
        self,
        signal: Signal,
        execution_price: float,
        account: AccountState,
        point: float = 0.001,
        contract_size: float = 100.0,
    ) -> Optional[OrderRequest]:
        """BacktestEngine bilan 100% mos interfeys."""
        res = self.check(signal, execution_price, account, point, contract_size)
        return res.order if res.approved else None

    def _reject(self, reason: str) -> RiskCheckResult:
        self.last_rejection_reason = reason
        logger.warning(f"[RISK GATE RAD ETDI]: {reason}")
        if self.state_store is not None:
            self.state_store.log_audit("ORDER_REJECTED", "REJECT", reason)
        return RiskCheckResult(approved=False, rejection_reason=reason)

    def record_trade_closure(self, pnl: float) -> None:
        """Bitim yopilganda ketma-ket zararlar va cooldown ni boshqarish."""
        if self.state_store is None:
            return

        state = self.state_store.load_state()
        curr_losses = state.get("consecutive_losses", 0)

        if pnl < 0:
            new_losses = curr_losses + 1
            updates: Dict[str, Any] = {"consecutive_losses": new_losses}
            if new_losses >= self.consecutive_losses_cooldown:
                cooldown_time = datetime.now(timezone.utc) + timedelta(minutes=self.cooldown_minutes)
                updates["cooldown_until"] = cooldown_time.isoformat()
                logger.warning(f"Ketma-ket {new_losses} ta zarar! Cooldown o'rnatildi: {cooldown_time.isoformat()}")
            self.state_store.save_state(updates)
        else:
            # G'alaba bo'lsa, zararlar hisoblagichi 0 ga tushadi
            self.state_store.save_state({"consecutive_losses": 0, "cooldown_until": None})
