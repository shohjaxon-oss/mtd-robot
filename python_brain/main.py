"""MTD-ROBOT FU-M3 Live Forward Runner (DEMO Only).

Arxitektura va Qat'iy Qoidalar:
- Faqat M3 (Zero-Lookahead, yangi yopilgan barlarda).
- Live Guard strictly enforces DEMO account (Real savdo mutlaqo bloklangan).
- Production Risk Gate with SQLite persistence.
- Bitta setup qoidasi: brokerda faol setup bo'lsa, yangi signal tashlab ketiladi.
- 2-Leg Atomik ijro (Leg A 0.01 lot TP 20 pip, Leg B 0.01 lot TP 30 pip, SL FU wick +/- 5 pip).
- Server-side Stop Loss & Take Profit (fill narxidan aniq yangilanadi).
- Breakeven Trailing: Leg A TP bilan yopilganda Leg B ning SL i kirish narxiga ko'chiriladi.
- Runner holati diskka yoziladi (State reconciliation).
- Har yopilgan barda bitta aniq, tushunarli log qatori.
- Heartbeat mustaqil alohida oqimda (Thread).
- Server va lokal soat drifti > 5s bo'lsa savdo to'xtatiladi.
"""

from __future__ import annotations

import os
import sys
import time
import json
import signal
import argparse
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from loguru import logger

from python_brain.config_loader import load_all_configs
from python_brain.logger import setup_logger
from python_brain.mt5_connect import MT5Connector
from python_brain.risk.live_guard import validate_demo_account, LiveTradingBlockedError
from python_brain.risk.gate import ProductionRiskGate
from python_brain.risk.state_store import RiskStateStore
from python_brain.execution.broker_executor import MT5BrokerExecutor
from python_brain.monitoring.heartbeat import HeartbeatEmitter
from python_brain.monitoring.telegram_notifier import TelegramNotifier
from python_brain.signals.fu_formation import FUFormationStrategy
from python_brain.backtest.models import AccountState, Signal, OrderSide


def build_account_state(
    connector: MT5Connector,
    symbol: str,
    initial_balance: Optional[float] = None,
    peak_equity_tracker: Optional[Dict[str, float]] = None,
) -> AccountState:
    """MT5 ma'lumotlaridan va deal tarixidan haqiqiy AccountState quradi."""
    acc = connector.get_account_info()
    if acc is None:
        raise RuntimeError("MT5 account_info qaytarmadi!")

    now_utc = datetime.now(timezone.utc)
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    week_start = today_start - timedelta(days=now_utc.weekday())

    # MT5 deals history
    daily_pnl = 0.0
    weekly_pnl = 0.0
    mt5_inst = getattr(connector, "_mt5", mt5)

    if mt5_inst is not None:
        try:
            today_deals = mt5_inst.history_deals_get(today_start, now_utc)
            if today_deals:
                # entry == 1 (DEAL_ENTRY_OUT)
                daily_pnl = sum(
                    getattr(d, "profit", 0.0) + getattr(d, "swap", 0.0) + getattr(d, "commission", 0.0)
                    for d in today_deals
                    if getattr(d, "entry", 0) == 1
                )
        except Exception as e:
            logger.warning(f"Bugungi deals tarixini o'qishda xatolik: {e}")

        try:
            week_deals = mt5_inst.history_deals_get(week_start, now_utc)
            if week_deals:
                weekly_pnl = sum(
                    getattr(d, "profit", 0.0) + getattr(d, "swap", 0.0) + getattr(d, "commission", 0.0)
                    for d in week_deals
                    if getattr(d, "entry", 0) == 1
                )
        except Exception as e:
            logger.warning(f"Haftalik deals tarixini o'qishda xatolik: {e}")

    init_bal = initial_balance if initial_balance is not None else acc.balance
    equity = acc.equity

    if peak_equity_tracker is not None:
        if "peak_equity" not in peak_equity_tracker or equity > peak_equity_tracker["peak_equity"]:
            peak_equity_tracker["peak_equity"] = equity
        peak_eq = peak_equity_tracker["peak_equity"]
    else:
        peak_eq = max(equity, init_bal)

    max_dd_pct = ((peak_eq - equity) / peak_eq * 100.0) if peak_eq > 0 else 0.0

    return AccountState(
        initial_balance=init_bal,
        equity=equity,
        balance=acc.balance,
        free_margin=acc.margin_free,
        leverage=acc.leverage,
        daily_realized_pnl=daily_pnl,
        weekly_realized_pnl=weekly_pnl,
        peak_equity=peak_eq,
        max_equity_drawdown_pct=max_dd_pct,
    )


def explain_fu_condition(df: pd.DataFrame, min_trend_candles: int = 3, engulf_mode: str = "body") -> str:
    """Bar bo'yicha FU tekshiruvining aniq holatini matn ko'rinishida beradi."""
    if df is None or len(df) < (min_trend_candles + 1):
        return f"INSUFFICIENT_BARS ({len(df) if df is not None else 0}/{min_trend_candles + 1})"

    recent = df.iloc[-(min_trend_candles + 1):]
    opens = recent["open"].values
    highs = recent["high"].values
    lows = recent["low"].values
    closes = recent["close"].values

    fu_o, fu_h, fu_l, fu_c = opens[-1], highs[-1], lows[-1], closes[-1]
    prev_h, prev_l, prev_c = highs[-2], lows[-2], closes[-2]

    is_fu_bearish = fu_c < fu_o
    is_fu_bullish = fu_c > fu_o

    # 1. Sell tekshiruvi
    if is_fu_bearish:
        bullish_count = sum(1 for i in range(min_trend_candles) if closes[-2 - i] > opens[-2 - i])
        if bullish_count < min_trend_candles:
            return f"NO_TREND ({bullish_count}/{min_trend_candles} bullish trend candles)"
        # engulfing
        has_engulf = False
        for i in range(min_trend_candles - 1):
            k, p = -2 - i, -3 - i
            min_k, max_k = min(opens[k], closes[k]), max(opens[k], closes[k])
            min_p, max_p = min(opens[p], closes[p]), max(opens[p], closes[p])
            if (min_k <= min_p) and (max_k >= max_p):
                has_engulf = True
                break
        if has_engulf:
            return "ENGULFING_FOUND (in trend candles)"
        if fu_h <= prev_h:
            return f"NO_HIGH_SWEEP (FU High {fu_h:.2f} <= Prev {prev_h:.2f})"
        if fu_c >= prev_c:
            return f"NO_CLOSE_BELOW (FU Close {fu_c:.2f} >= Prev {prev_c:.2f})"
        return "FU_SELL_FORMED"

    # 2. Buy tekshiruvi
    if is_fu_bullish:
        bearish_count = sum(1 for i in range(min_trend_candles) if closes[-2 - i] < opens[-2 - i])
        if bearish_count < min_trend_candles:
            return f"NO_TREND ({bearish_count}/{min_trend_candles} bearish trend candles)"
        has_engulf = False
        for i in range(min_trend_candles - 1):
            k, p = -2 - i, -3 - i
            min_k, max_k = min(opens[k], closes[k]), max(opens[k], closes[k])
            min_p, max_p = min(opens[p], closes[p]), max(opens[p], closes[p])
            if (min_k <= min_p) and (max_k >= max_p):
                has_engulf = True
                break
        if has_engulf:
            return "ENGULFING_FOUND (in trend candles)"
        if fu_l >= prev_l:
            return f"NO_LOW_SWEEP (FU Low {fu_l:.2f} >= Prev {prev_l:.2f})"
        if fu_c <= prev_c:
            return f"NO_CLOSE_ABOVE (FU Close {fu_c:.2f} <= Prev {prev_c:.2f})"
        return "FU_BUY_FORMED"

    return "DOJI_CANDLE (No direction)"


class LiveRunner:
    """Manages the main event-driven live trading loop strictly on M3 closed bars."""

    def __init__(
        self,
        config_dir: str = "config",
        single_pass: bool = False,
        timeframe: str = "M3",
        demo_profile: bool = True,
    ):
        # Qat'iy Timeframe tekshiruvi: FAQAT M3
        if timeframe.upper() != "M3":
            raise ValueError(f"QAT'IY QOIDA: FU strategiyasi FAQAT M3 timeframe'da ishlaydi! Berildi: '{timeframe}'")

        self.single_pass = single_pass
        self.running = True
        self.last_bar_time: Optional[int] = None
        self.timeframe_str = "M3"
        self.timeframe_mt5 = getattr(mt5, "TIMEFRAME_M3", 3) if mt5 else 3

        # State persistence yo'li
        self.state_file_path = Path("data") / "state" / "runner_state.json"
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.active_setup: Optional[Dict[str, Any]] = None

        # 1. Config loading & Logger
        self.configs = load_all_configs(config_dir=config_dir)
        setup_logger(
            log_level=self.configs.settings.logging.level,
            log_to_file=self.configs.settings.logging.log_to_file,
            log_file_path=self.configs.settings.logging.file_path,
        )
        logger.info("Initializing MTD-ROBOT FU-M3 Live Runner...")

        # 2. MT5 Connector & Connection
        self.connector = MT5Connector()
        if not self.connector.initialize():
            raise RuntimeError("MT5 initialization failed!")
        if not self.connector.login():
            raise RuntimeError("MT5 login failed!")

        # 3. LIVE GUARD (STRICT SAFETY GATE)
        self.account = self.connector.get_account_info()
        allow_live = self.configs.settings.safety.allow_live
        validate_demo_account(self.account, allow_live=allow_live)
        logger.info(
            f"LIVE GUARD PASSED: Connected to DEMO Account #{self.account.login} "
            f"({self.account.server}) | Balance: ${self.account.balance:.2f}"
        )

        # 4. Monitoring & Heartbeat
        self.notifier = TelegramNotifier()
        self.heartbeat = HeartbeatEmitter(filename="mtd_heartbeat.json")
        self.heartbeat.beat(status="INITIALIZED")

        # Heartbeat background thread
        self._heartbeat_stop_event = threading.Event()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._heartbeat_thread.start()

        # 5. Risk Gate with SQLite State Persistence
        state_db_path = Path("data") / "state" / "risk_state.db"
        state_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_store = RiskStateStore(db_path=state_db_path)
        self.risk_gate = ProductionRiskGate(
            risk_config=self.configs.risk,
            state_store=self.state_store,
            demo_profile=demo_profile,
        )

        # 6. Broker Execution Layer
        env_sym = self.configs.env.PRIMARY_SYMBOL
        self.symbol = (
            self.connector.find_actual_symbol([env_sym, self.configs.symbols.primary_symbol, "XAUUSDm", "XAUUSD"])
            or env_sym
            or "XAUUSDm"
        )
        self.magic_number = self.configs.symbols.symbol.execution.magic_number
        self.executor = MT5BrokerExecutor(
            symbol=self.symbol,
            magic_number=self.magic_number,
            slippage_points=self.configs.symbols.symbol.execution.max_slippage_points,
            allow_live=allow_live,
        )

        # 7. Strategy Initialization (FU Formation for M3)
        self.strategy = FUFormationStrategy(
            timeframe="M3",
            min_trend_candles=3,
            engulf_mode="body",
            sl_buffer_pips=5.0,
            tp1_pips=20.0,
            tp2_pips=30.0,
            lot_per_leg=0.01,
            pip_size_price=0.10,
        )

        # Tracking state
        self.peak_equity_tracker: Dict[str, float] = {"peak_equity": self.account.equity}
        self.initial_balance = self.account.balance

        # 8. Reconcile existing state
        self._load_and_reconcile_state()

        # Check clock drift
        self._check_time_drift()

    def _heartbeat_worker(self):
        """Mustaqil oqimda har 1 soniyada heartbeat yozadi."""
        while not self._heartbeat_stop_event.is_set():
            try:
                status = "RUNNING" if self.running else "STOPPED"
                self.heartbeat.beat(status=status)
            except Exception:
                pass
            time.sleep(1.0)

    def _load_and_reconcile_state(self):
        """Runner holatini diskdan yuklaydi va brokerdagi pozitsiyalar bilan moslashtiradi."""
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_bar_time = data.get("last_bar_time")
                    self.active_setup = data.get("active_setup")
                    logger.info(f"Diskdan holat tiklandi: last_bar={self.last_bar_time}, active_setup={self.active_setup}")
            except Exception as e:
                logger.warning(f"State faylini o'qishda xatolik: {e}")

        # Brokerdagi ochiq pozitsiyalarni tekshirish
        open_pos = self.executor.reconcile_open_positions()
        if not open_pos and self.active_setup:
            logger.info("Brokerda faol pozitsiyalar yo'q. Faol setup tozalanyapti.")
            self.active_setup = None
            self._save_runner_state()
        elif open_pos and not self.active_setup:
            # Agar brokerda ochiq pozitsiyalar bo'lsa, ularni active_setup ga tiklash
            leg_a = next((p for p in open_pos if "|A" in str(p.get("comment", ""))), None)
            leg_b = next((p for p in open_pos if "|B" in str(p.get("comment", ""))), None)
            if leg_a or leg_b:
                self.active_setup = {
                    "leg_a_ticket": leg_a["ticket"] if leg_a else None,
                    "leg_b_ticket": leg_b["ticket"] if leg_b else None,
                    "entry_price": (leg_a or leg_b)["open_price"],
                    "side": (leg_a or leg_b)["type"],
                    "be_applied": False,
                }
                logger.info(f"Broker pozitsiyalaridan active_setup tiklandi: {self.active_setup}")
                self._save_runner_state()

    def _save_runner_state(self):
        """Runner holatini diskka yozadi."""
        try:
            state = {
                "last_bar_time": self.last_bar_time,
                "active_setup": self.active_setup,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"State faylini saqlashda xatolik: {e}")

    def _check_time_drift(self):
        """Verifies broker time alignment with local system UTC (sub-minute clock drift)."""
        try:
            tick = self.connector.get_symbol_info_tick(self.symbol)
            if tick and tick.time:
                local_now_epoch = int(datetime.now(timezone.utc).timestamp())
                raw_drift = abs(local_now_epoch - tick.time)
                # Broker server vaqti odatda EET/EEST (UTC+2/UTC+3) bo'ladi.
                # Shu sababli butun soat farqi (timezone offset) chiqarib tashlanadi va haqiqiy soniya drifti olinadi.
                drift = min(raw_drift % 3600, 3600 - (raw_drift % 3600))
                if drift > 5:
                    err_msg = (
                        f"SOAT DRIFTI XATOSI: Broker server vaqti va lokal UTC orasida {drift}s farq bor! "
                        "Savdo to'xtatildi. Windows soat sinxronizatsiyasini yangilang."
                    )
                    logger.critical(err_msg)
                    self.notifier.send_message(f"⚠️ {err_msg}")
                    raise RuntimeError(err_msg)
                else:
                    logger.info(f"Time sync verified. Sub-minute drift: {drift}s (Limit: <=5s).")
        except Exception as e:
            logger.warning(f"Could not check time drift: {e}")

    def get_history_dataframe(self, count: int = 100) -> Optional[pd.DataFrame]:
        """Fetches the latest count closed bars from MT5 into a DataFrame."""
        if mt5 is None:
            return None
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe_mt5, 1, count)
        if rates is None or len(rates) == 0:
            return None

        df = pd.DataFrame(rates)
        df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df

    def check_breakeven_and_closures(self):
        """Faol setupni nazorat qiladi: Leg A TP bo'lsa Leg B SL ni entry ga ko'chiradi."""
        if not self.active_setup:
            return

        leg_a_ticket = self.active_setup.get("leg_a_ticket")
        leg_b_ticket = self.active_setup.get("leg_b_ticket")
        be_applied = self.active_setup.get("be_applied", False)
        entry_price = self.active_setup.get("entry_price", 0.0)

        # 1. Pozitsiyalar holatini tekshirish
        open_pos = self.executor.reconcile_open_positions()
        pos_tickets = {p["ticket"]: p for p in open_pos}

        leg_a_open = leg_a_ticket in pos_tickets if leg_a_ticket else False
        leg_b_open = leg_b_ticket in pos_tickets if leg_b_ticket else False

        # Agar ikkala leg ham yopilgan bo'lsa
        if not leg_a_open and not leg_b_open:
            logger.info("Setup to'liq yopildi (Ikkala leg ham yopiq).")
            # Deal tarixidan yakuniy PnL hisoblash
            self._process_setup_closure()
            self.active_setup = None
            self._save_runner_state()
            return

        # 2. Leg A yopilgan va Leg B ochiq va BE hali qo'yilmagan bo'lsa
        if not leg_a_open and leg_b_open and not be_applied and leg_a_ticket:
            # Leg A TP bilan yopilganini tasdiqlash
            leg_a_closed_by_tp = self._check_if_leg_closed_by_tp(leg_a_ticket)
            if leg_a_closed_by_tp:
                logger.info(f"Leg A (#{leg_a_ticket}) TP bilan yopildi! Leg B (#{leg_b_ticket}) SL entry {entry_price} ga ko'chirilmoqda...")
                # Modifikatsiya
                be_res = self.executor.modify_position_sl_tp(ticket=leg_b_ticket, sl=entry_price)
                if be_res.success:
                    self.active_setup["be_applied"] = True
                    self._save_runner_state()
                    msg = f"🎯 Leg A TP bilan yopildi! Leg B (#{leg_b_ticket}) SL kirish narxiga ({entry_price}) ko'chirildi (Breakeven)."
                    logger.success(msg)
                    self.notifier.send_message(msg)
                else:
                    err_msg = f"⚠️ Leg B (#{leg_b_ticket}) SL ni Breakeven ga o'tkazishda xatolik: {be_res.comment}"
                    logger.error(err_msg)
                    self.notifier.send_message(err_msg)
            else:
                logger.info(f"Leg A (#{leg_a_ticket}) SL bilan yopilgan. Breakeven o'rnatilmaydi.")

    def _check_if_leg_closed_by_tp(self, ticket: int) -> bool:
        """Leg deal tarixida TP sababi bilan yopilganini tekshiradi."""
        if mt5 is None:
            return False
        try:
            now_utc = datetime.now(timezone.utc)
            deals = mt5.history_deals_get(position=ticket)
            if deals:
                close_deals = [d for d in deals if getattr(d, "entry", 0) == 1]
                if close_deals:
                    d = close_deals[-1]
                    # deal reason: 4 = DEAL_REASON_TP, profit > 0
                    if getattr(d, "reason", 0) == 4 or getattr(d, "profit", 0.0) > 0:
                        return True
        except Exception as e:
            logger.warning(f"Deal sababini tekshirishda xatolik: {e}")
        return False

    def _process_setup_closure(self):
        """Setup yopilganda PnL ni aniqlab risk_gate.record_trade_closure ni chaqiradi."""
        if not self.active_setup:
            return
        tickets = [self.active_setup.get("leg_a_ticket"), self.active_setup.get("leg_b_ticket")]
        total_pnl = 0.0
        if mt5 is not None:
            for t in tickets:
                if t:
                    deals = mt5.history_deals_get(position=t)
                    if deals:
                        for d in deals:
                            if getattr(d, "entry", 0) == 1:
                                total_pnl += (getattr(d, "profit", 0.0) + getattr(d, "swap", 0.0) + getattr(d, "commission", 0.0))
        self.risk_gate.record_trade_closure(total_pnl)
        closure_msg = f"🏁 FU Setup yopildi | Jami PnL: ${total_pnl:.2f}"
        logger.info(closure_msg)
        self.notifier.send_message(closure_msg)

    def run_cycle(self):
        """Performs a single evaluation cycle on newly closed M3 bars."""
        # 1. Check Breakeven and active closures
        self.check_breakeven_and_closures()

        # 2. Check latest M3 bars
        if mt5 is None:
            return

        rates_current = mt5.copy_rates_from_pos(self.symbol, self.timeframe_mt5, 0, 2)
        if rates_current is None or len(rates_current) < 2:
            return

        current_forming_bar_time = int(rates_current[-1]["time"])
        closed_bar_time = int(rates_current[-2]["time"])
        now_epoch = int(datetime.now(timezone.utc).timestamp())

        # Check if a new bar just closed
        if self.last_bar_time is None:
            self.last_bar_time = closed_bar_time
            logger.info(f"Initialized M3 bar tracker at {datetime.fromtimestamp(closed_bar_time, tz=timezone.utc)}")
            self._save_runner_state()
            if not self.single_pass:
                return

        if closed_bar_time > self.last_bar_time or self.single_pass:
            self.last_bar_time = closed_bar_time
            self._save_runner_state()
            bar_dt = datetime.fromtimestamp(closed_bar_time, tz=timezone.utc)

            # Fetch history for evaluation
            history = self.get_history_dataframe(count=100)
            if history is None or len(history) < 4:
                logger.error("Failed to fetch historical M3 bars from MT5.")
                return

            last_closed = history.iloc[-1]
            o, h, l, c = last_closed["open"], last_closed["high"], last_closed["low"], last_closed["close"]

            # Aniq FU holatini tekshirish va loglash
            fu_status = explain_fu_condition(history, min_trend_candles=3, engulf_mode="body")

            # 3. BITTA SETUP QOIDASI: Agar faol setup bo'lsa, yangi signal e'tiborsiz qoldiriladi
            open_pos = self.executor.reconcile_open_positions()
            if len(open_pos) > 0 or self.active_setup is not None:
                log_line = (
                    f"[BAR_EVAL] Time: {bar_dt.strftime('%Y-%m-%d %H:%M')} UTC | "
                    f"O: {o:.2f} H: {h:.2f} L: {l:.2f} C: {c:.2f} | "
                    f"FU: {fu_status} | Risk: SETUP_ACTIVE | Exec: SKIP"
                )
                logger.info(log_line)
                return

            # Strategiya baholash
            signal_obj = self.strategy.on_bar(history)
            if signal_obj is None:
                log_line = (
                    f"[BAR_EVAL] Time: {bar_dt.strftime('%Y-%m-%d %H:%M')} UTC | "
                    f"O: {o:.2f} H: {h:.2f} L: {l:.2f} C: {c:.2f} | "
                    f"FU: {fu_status} | Risk: N/A | Exec: IDLE"
                )
                logger.info(log_line)
                return

            # Signal mavjud!
            # 4. Kirish kechikishi tekshiruvi: yangi bar ochilishidan (current_forming_bar_time) 5 soniya o'tgan bo'lsa SKIP
            entry_delay = now_epoch - current_forming_bar_time
            if entry_delay > 5:
                log_line = (
                    f"[BAR_EVAL] Time: {bar_dt.strftime('%Y-%m-%d %H:%M')} UTC | "
                    f"O: {o:.2f} H: {h:.2f} L: {l:.2f} C: {c:.2f} | "
                    f"FU: {signal_obj.action} (SL={signal_obj.sl}) | "
                    f"Risk: SETUP_SKIPPED_ENTRY_DELAY ({entry_delay}s > 5s) | Exec: SKIP"
                )
                logger.warning(log_line)
                return

            # 5. Stops level va narx tekshiruvi
            tick = self.connector.get_symbol_info_tick(self.symbol)
            if tick is None:
                logger.error("Tick ma'lumoti mavjud emas, ijro bekor qilindi.")
                return

            is_buy = signal_obj.action == "BUY"
            req_price = tick.ask if is_buy else tick.bid
            sym_info = self.connector._mt5.symbol_info(self.symbol)
            stops_level = getattr(sym_info, "stops_level", 0) if sym_info else 0
            point = getattr(sym_info, "point", 0.001) if sym_info else 0.001
            try:
                min_stop_distance = float(stops_level) * float(point)
            except (ValueError, TypeError):
                min_stop_distance = 0.0

            sl_dist = (req_price - signal_obj.sl) if is_buy else (signal_obj.sl - req_price)
            if sl_dist <= 0 or sl_dist < min_stop_distance:
                log_line = (
                    f"[BAR_EVAL] Time: {bar_dt.strftime('%Y-%m-%d %H:%M')} UTC | "
                    f"O: {o:.2f} H: {h:.2f} L: {l:.2f} C: {c:.2f} | "
                    f"FU: {signal_obj.action} | "
                    f"Risk: SETUP_SKIPPED_STOPS_LEVEL (dist {sl_dist:.3f} < min {min_stop_distance:.3f}) | Exec: SKIP"
                )
                logger.warning(log_line)
                return

            # 6. Risk Gate tekshiruvi
            account_state = build_account_state(
                connector=self.connector,
                symbol=self.symbol,
                initial_balance=self.initial_balance,
                peak_equity_tracker=self.peak_equity_tracker,
            )
            raw_acc = self.connector.get_account_info()
            spread_pts = round((tick.ask - tick.bid) / point, 1)

            decision = self.risk_gate.evaluate(
                signal=signal_obj,
                account=account_state,
                current_spread_pts=spread_pts,
                current_time_utc=bar_dt,
                raw_account_info=raw_acc,
                execution_price=req_price,
            )

            if not decision.approved:
                log_line = (
                    f"[BAR_EVAL] Time: {bar_dt.strftime('%Y-%m-%d %H:%M')} UTC | "
                    f"O: {o:.2f} H: {h:.2f} L: {l:.2f} C: {c:.2f} | "
                    f"FU: {signal_obj.action} | Risk: REJECT ({decision.reject_reason}) | Exec: REJECT"
                )
                logger.warning(log_line)
                return

            # 7. 2-Leg Atomik Ijro
            # Dastlabki TP narxini hisoblash (server-side TP har doim mavjud bo'lishi uchun)
            pip_size = getattr(signal_obj, "pip_size_price", 0.10)
            tp_a_initial = round(req_price + (20.0 * pip_size), 3) if is_buy else round(req_price - (20.0 * pip_size), 3)
            tp_b_initial = round(req_price + (30.0 * pip_size), 3) if is_buy else round(req_price - (30.0 * pip_size), 3)

            logger.info(f"RISK APPROVED: FU 2-Leg ochilmoqda: Side={signal_obj.action}, SL={signal_obj.sl}, TP_A={tp_a_initial}, TP_B={tp_b_initial}")

            # Leg A yuborish
            res_a = self.executor.send_market_order(
                side=signal_obj.action,
                volume=0.01,
                sl=signal_obj.sl,
                tp=tp_a_initial,
                comment=f"FU|{closed_bar_time}|A",
            )

            # Leg B yuborish
            res_b = self.executor.send_market_order(
                side=signal_obj.action,
                volume=0.01,
                sl=signal_obj.sl,
                tp=tp_b_initial,
                comment=f"FU|{closed_bar_time}|B",
            )

            # 8. Atomiklik tekshiruvi: biri fail bo'lsa ikkinchisini zudlik bilan yopish
            if res_a.success and not res_b.success:
                err_msg = f"FAVQULODDA: Leg B muvaffaqiyatsiz bo'ldi ({res_b.comment})! Leg A #{res_a.ticket} darhol yopilmoqda (Atomik Setup)..."
                logger.critical(err_msg)
                self.notifier.send_message(f"🚨 {err_msg}")
                self.executor.close_position(res_a.ticket)
                return

            if res_b.success and not res_a.success:
                err_msg = f"FAVQULODDA: Leg A muvaffaqiyatsiz bo'ldi ({res_a.comment})! Leg B #{res_b.ticket} darhol yopilmoqda (Atomik Setup)..."
                logger.critical(err_msg)
                self.notifier.send_message(f"🚨 {err_msg}")
                self.executor.close_position(res_b.ticket)
                return

            if not res_a.success and not res_b.success:
                logger.error(f"Setup ochilmadi: Leg A xatosi='{res_a.comment}', Leg B xatosi='{res_b.comment}'")
                return

            # Ikkala leg ham muvaffaqiyatli ochildi!
            # 9. Haqiqiy fill narxidan aniq TP ni serverda yangilash (modify)
            fill_a = res_a.fill_price
            fill_b = res_b.fill_price
            exact_tp_a = round(fill_a + (20.0 * pip_size), 3) if is_buy else round(fill_a - (20.0 * pip_size), 3)
            exact_tp_b = round(fill_b + (30.0 * pip_size), 3) if is_buy else round(fill_b - (30.0 * pip_size), 3)

            mod_a = self.executor.modify_position_sl_tp(ticket=res_a.ticket, sl=signal_obj.sl, tp=exact_tp_a)
            mod_b = self.executor.modify_position_sl_tp(ticket=res_b.ticket, sl=signal_obj.sl, tp=exact_tp_b)

            if not mod_a.success or not mod_b.success:
                logger.warning(f"TP larni fill narxiga moslashtirishda muammo: A={mod_a.comment}, B={mod_b.comment}")

            # Holatni saqlash
            self.active_setup = {
                "leg_a_ticket": res_a.ticket,
                "leg_b_ticket": res_b.ticket,
                "entry_price": fill_a,
                "side": signal_obj.action,
                "sl": signal_obj.sl,
                "tp_a": exact_tp_a,
                "tp_b": exact_tp_b,
                "be_applied": False,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_runner_state()

            success_msg = (
                f"✅ FU 2-Leg Setup Ochildi!\n"
                f"Yo'nalish: {signal_obj.action}\n"
                f"Leg A: #{res_a.ticket} @ {fill_a:.2f} | TP: {exact_tp_a:.2f} (20 pip)\n"
                f"Leg B: #{res_b.ticket} @ {fill_b:.2f} | TP: {exact_tp_b:.2f} (30 pip)\n"
                f"Umumiy SL: {signal_obj.sl:.2f}"
            )
            logger.success(success_msg)
            self.notifier.send_message(success_msg)

            log_line = (
                f"[BAR_EVAL] Time: {bar_dt.strftime('%Y-%m-%d %H:%M')} UTC | "
                f"O: {o:.2f} H: {h:.2f} L: {l:.2f} C: {c:.2f} | "
                f"FU: {signal_obj.action} | Risk: APPROVED | "
                f"Exec: OPENED (A: #{res_a.ticket}, B: #{res_b.ticket})"
            )
            logger.info(log_line)

    def start(self):
        """Starts the live main loop."""
        logger.info("MTD-ROBOT FU-M3 Live Runner started. Monitoring closed bars...")

        def handle_shutdown(signum, frame):
            logger.info("Shutdown signal received! Initiating graceful stop...")
            self.running = False

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        try:
            while self.running:
                self.run_cycle()
                if self.single_pass:
                    break
                # Faol setup paytida tezroq (0.3s) sikl, faol bo'lmaganda 1.0s
                sleep_time = 0.3 if self.active_setup is not None else 1.0
                time.sleep(sleep_time)
        finally:
            self.shutdown()

    def shutdown(self):
        """Performs graceful shutdown, keeping positions safe on server."""
        logger.info("Performing clean shutdown...")
        self._heartbeat_stop_event.set()
        if self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)
        self.heartbeat.beat(status="STOPPED")
        self.connector.shutdown()
        logger.info(
            "MT5 Disconnected. All broker positions remain actively protected "
            "on the server via hard Stop Loss and Take Profit."
        )


def main():
    parser = argparse.ArgumentParser(description="MTD-ROBOT FU-M3 Live Forward Runner")
    parser.add_argument("--config-dir", default="config", help="Path to config directory")
    parser.add_argument("--single-pass", action="store_true", help="Run a single cycle and exit (for testing)")
    parser.add_argument("--timeframe", default="M3", choices=["M3"], help="Timeframe (FAQAT M3)")
    args = parser.parse_args()

    try:
        runner = LiveRunner(
            config_dir=args.config_dir,
            single_pass=args.single_pass,
            timeframe=args.timeframe,
            demo_profile=True,
        )
        runner.start()
    except LiveTradingBlockedError as e:
        logger.critical(f"FATAL LIVE GUARD SAFETY HALT: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unhandled fatal error in LiveRunner: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
