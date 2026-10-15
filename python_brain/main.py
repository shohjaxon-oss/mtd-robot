"""MTD-ROBOT Live Forward Runner (DEMO Only).

Architecture Principle:
- Driven exclusively by newly closed bars (no intra-candle noise/tick thrashing).
- Live Guard strictly enforces DEMO account (real trading blocked).
- Production Risk Gate with SQLite persistence.
- Server-side Stop Loss & Take Profit on all orders.
- Heartbeat synchronization with MTD_Guardian EA.
- Graceful shutdown preserving server-side protection.
"""

import os
import sys
import time
import signal
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import MetaTrader5 as mt5

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

logger = logging.getLogger("mtd.live_runner")


class LiveRunner:
    """Manages the main event-driven live trading loop on closed bars."""

    def __init__(self, config_dir: str = "config", single_pass: bool = False, timeframe: str = "M3"):
        self.single_pass = single_pass
        self.running = True
        self.last_bar_time: Optional[int] = None
        self.timeframe_str = timeframe.upper()
        self.timeframe_mt5 = getattr(mt5, f"TIMEFRAME_{self.timeframe_str}", mt5.TIMEFRAME_M3)


        # 1. Config loading & Logger
        self.configs = load_all_configs(config_dir=config_dir)
        setup_logger(
            log_level=self.configs.settings.logging.level,
            log_to_file=self.configs.settings.logging.log_to_file,
            log_file_path=self.configs.settings.logging.file_path,
        )
        logger.info("Initializing MTD-ROBOT Live Runner...")

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

        # 5. Risk Gate with SQLite State Persistence
        state_db_path = Path("data") / "state" / "risk_state.db"
        self.state_store = RiskStateStore(db_path=state_db_path)
        self.risk_gate = ProductionRiskGate(
            risk_config=self.configs.risk,
            state_store=self.state_store,
        )

        # 6. Broker Execution Layer
        env_sym = self.configs.env.PRIMARY_SYMBOL
        self.symbol = (
            self.connector.find_actual_symbol([env_sym, self.configs.symbols.primary_symbol, "XAUUSD", "XAUUSDm"])
            or env_sym
            or "XAUUSD"
        )
        self.executor = MT5BrokerExecutor(
            symbol=self.symbol,
            magic_number=10101,
            slippage_points=50,
            allow_live=allow_live,
        )

        # Reconcile existing positions
        existing_pos = self.executor.reconcile_open_positions()
        logger.info(f"State Reconciliation: Found {len(existing_pos)} active positions on broker.")

        # 7. Strategy Initialization (FU Formation for Live Demo)
        self.strategy = FUFormationStrategy(
            timeframe=self.timeframe_str,
            min_trend_candles=3,
            engulf_mode="body",
            sl_buffer_pips=5.0,
            tp1_pips=20.0,
            tp2_pips=30.0,
            lot_per_leg=0.01,
            pip_size_price=0.10,
        )
        logger.info(f"Initialized FUFormationStrategy on timeframe {self.timeframe_str}.")

        # Check clock drift
        self._check_time_drift()

    def _check_time_drift(self):
        """Verifies broker time alignment with local system UTC."""
        try:
            tick = self.connector.get_symbol_info_tick(self.symbol)
            if tick and tick.time:
                local_now_epoch = int(datetime.now(timezone.utc).timestamp())
                drift = abs(local_now_epoch - tick.time)
                if drift > 15:
                    logger.warning(
                        f"TIME DRIFT WARNING: Broker tick time and local UTC drift by {drift} seconds! "
                        "Ensure Windows time sync is active."
                    )
                else:
                    logger.info(f"Time sync verified. Drift: {drift}s.")
        except Exception as e:
            logger.warning(f"Could not check time drift: {e}")

    def get_history_dataframe(self, count: int = 100) -> Optional[pd.DataFrame]:
        """Fetches the latest count closed bars from MT5 into a DataFrame."""
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe_mt5, 1, count)
        if rates is None or len(rates) == 0:
            return None

        df = pd.DataFrame(rates)
        df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df

    def check_breakeven_trailing(self):
        """Monitors open FU positions: if Leg A is closed, moves Leg B SL to entry price."""
        try:
            open_pos = self.executor.reconcile_open_positions()
            leg_b_positions = [p for p in open_pos if "|B" in str(p.get("comment", ""))]
            leg_a_positions = [p for p in open_pos if "|A" in str(p.get("comment", ""))]

            for pos_b in leg_b_positions:
                tag = pos_b["comment"].split("|")[1] if "|" in pos_b["comment"] else None
                has_open_leg_a = any(tag and tag in p["comment"] for p in leg_a_positions)
                if not has_open_leg_a:
                    entry_price = pos_b["open_price"]
                    current_sl = pos_b["sl"]
                    if abs(current_sl - entry_price) > 0.05:
                        logger.info(f"BREAKEVEN TRIGGERED: Leg A closed. Moving Leg B (#{pos_b['ticket']}) SL to entry {entry_price}...")
                        self.executor.modify_position_sl_tp(ticket=pos_b["ticket"], sl=entry_price)
        except Exception as e:
            logger.warning(f"Error checking breakeven trailing: {e}")

    def run_cycle(self):
        """Performs a single evaluation cycle on newly closed bars."""
        # 1. Update heartbeat
        self.heartbeat.beat(status="RUNNING")

        # 2. Check and trail breakeven for active Leg B positions
        self.check_breakeven_trailing()

        # 3. Check latest bar
        rates_current = mt5.copy_rates_from_pos(self.symbol, self.timeframe_mt5, 0, 2)
        if rates_current is None or len(rates_current) < 2:
            return

        current_forming_bar_time = int(rates_current[-1]["time"])
        closed_bar_time = int(rates_current[-2]["time"])

        # Check if a new bar just closed
        if self.last_bar_time is None:
            self.last_bar_time = closed_bar_time
            logger.info(f"Initialized {self.timeframe_str} bar tracker at {datetime.fromtimestamp(closed_bar_time, tz=timezone.utc)}")
            if not self.single_pass:
                return

        if closed_bar_time > self.last_bar_time or self.single_pass:
            self.last_bar_time = closed_bar_time
            bar_dt = datetime.fromtimestamp(closed_bar_time, tz=timezone.utc)
            logger.info(f"=== NEW {self.timeframe_str} BAR CLOSED: {bar_dt} ===")

            # Fetch history
            history = self.get_history_dataframe(count=100)
            if history is None:
                logger.error(f"Failed to fetch historical {self.timeframe_str} bars from MT5.")
                return

            # Evaluate strategy
            signal = self.strategy.on_bar(history)
            if signal is None:
                logger.info(f"Strategy on_bar: No trade signal on candle {bar_dt}.")
                return

            logger.info(f"STRATEGY SIGNAL: {signal.action} | SL: {signal.sl} | TP: {signal.tp}")

            # Risk Gate Evaluation
            acc_info = self.connector.get_account_info()
            tick = self.connector.get_symbol_info_tick(self.symbol)
            spread = (tick.ask - tick.bid) if tick else 0.0

            decision = self.risk_gate.evaluate(
                signal=signal,
                account=acc_info,
                current_spread=spread,
                current_time_utc=bar_dt,
            )

            if not decision.approved:
                logger.warning(f"RISK REJECTION: {decision.reject_reason}")
                return

            # Execution
            if hasattr(signal, "legs") and signal.legs and len(signal.legs) >= 2:
                leg_a = signal.legs[0]
                leg_b = signal.legs[1]
                logger.info(f"RISK APPROVED: Executing FU 2-Leg setup (0.01 lot each)...")
                res_a = self.executor.send_market_order(
                    side=signal.action,
                    volume=leg_a.volume,
                    sl=signal.sl or 0.0,
                    tp=leg_a.tp,
                    comment=f"FU|{closed_bar_time}|A",
                )
                res_b = self.executor.send_market_order(
                    side=signal.action,
                    volume=leg_b.volume,
                    sl=signal.sl or 0.0,
                    tp=leg_b.tp,
                    comment=f"FU|{closed_bar_time}|B",
                )
                if res_a.success:
                    logger.info(f"Leg A Ochildi: Ticket #{res_a.ticket} @ {res_a.fill_price}, TP={leg_a.tp}")
                if res_b.success:
                    logger.info(f"Leg B Ochildi: Ticket #{res_b.ticket} @ {res_b.fill_price}, TP={leg_b.tp}")
            else:
                logger.info(f"RISK APPROVED: Volume {decision.allocated_volume} lot. Sending to broker...")
                order_res = self.executor.execute_signal(
                    signal=signal,
                    volume=decision.allocated_volume,
                )
                if order_res.success:
                    logger.info(f"ORDER EXECUTED: Ticket #{order_res.ticket} at {order_res.fill_price}")


    def start(self):
        """Starts the live main loop."""
        logger.info("MTD-ROBOT Live Runner started. Monitoring closed bars...")

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
                time.sleep(2)
        finally:
            self.shutdown()

    def shutdown(self):
        """Performs graceful shutdown, keeping positions safe on server."""
        logger.info("Performing clean shutdown...")
        self.heartbeat.beat(status="STOPPED")
        self.connector.shutdown()
        logger.info(
            "MT5 Disconnected. All broker positions remain actively protected "
            "on the server via hard Stop Loss and Take Profit."
        )


def main():
    parser = argparse.ArgumentParser(description="MTD-ROBOT Live Forward Runner")
    parser.add_argument("--config-dir", default="config", help="Path to config directory")
    parser.add_argument("--single-pass", action="store_true", help="Run a single cycle and exit (for testing)")
    parser.add_argument("--timeframe", default="M3", help="Timeframe (M1, M3, M5, default: M3)")
    args = parser.parse_args()

    try:
        runner = LiveRunner(
            config_dir=args.config_dir,
            single_pass=args.single_pass,
            timeframe=args.timeframe,
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
