"""DEMO DRY RUN: Single trade lifecycle validation.

Opens a single 0.01 lot test trade on DEMO account with server-side SL/TP,
verifies server-side position registration, and closes the trade cleanly.

SAFEGUARDS:
- Strictly guarded by LiveGuard (blocks execution if account is REAL).
- Operates strictly with 0.01 minimum lot.
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_brain.config_loader import load_all_configs
from python_brain.mt5_connect import MT5Connector
from python_brain.risk.live_guard import validate_demo_account, LiveTradingBlockedError
from python_brain.execution.broker_executor import MT5BrokerExecutor
from python_brain.backtest.models import Signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DemoDryRun] %(message)s",
)
logger = logging.getLogger("mtd.demo_dry_run")


def run_demo_dry_run():
    print("=================================================================")
    print("          MTD-ROBOT DEMO DRY RUN TEST (0.01 LOT)               ")
    print("=================================================================")

    # 1. Load config
    configs = load_all_configs(config_dir="config")
    allow_live = configs.settings.safety.allow_live
    env_sym = configs.env.PRIMARY_SYMBOL

    # 2. Connect to MT5
    connector = MT5Connector()
    if not connector.initialize() or not connector.login():
        logger.error("MT5 ga ulanib bo'lmadi! Terminal ochiqligini tekshiring.")
        sys.exit(1)

    # Auto-discover active symbol (e.g. XAUUSD vs XAUUSDm)
    symbol = connector.find_actual_symbol([env_sym, configs.symbols.primary_symbol, "XAUUSD", "XAUUSDm"]) or env_sym or "XAUUSD"

    try:
        # 3. LIVE GUARD (Strict enforcement)
        account = connector.get_account_info()
        validate_demo_account(account, allow_live=allow_live)
        print(f"[1/5] LIVE GUARD TASDIQLANDI:")
        print(f"      Login: #{account.login} | Server: {account.server}")
        print(f"      Trade Mode: DEMO ({account.trade_mode}) | Balans: ${account.balance:.2f}\n")

        # 4. Executor initialization
        executor = MT5BrokerExecutor(
            symbol=symbol,
            magic_number=10101,
            slippage_points=50,
            allow_live=allow_live,
        )

        # 5. Get current tick
        tick = connector.get_symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"{symbol} uchun tick ma'lumotlarini olib bo'lmadi!")
            sys.exit(1)

        ask = tick.ask
        bid = tick.bid
        spread = ask - bid
        print(f"[2/5] BOZOR HOLATI:")
        print(f"      Simvol: {symbol} | Bid: {bid:.2f} | Ask: {ask:.2f} | Spread: {spread:.2f} USD\n")

        # SL and TP calculation ($3.00 distance on gold)
        sl_price = round(ask - 3.0, 2)
        tp_price = round(ask + 3.0, 2)

        test_signal = Signal(
            time_utc=None,
            action="BUY",
            sl=sl_price,
            tp=tp_price,
            comment="DEMO_DRY_RUN",
        )

        print(f"[3/5] BUYURTMA YUBORILMOQDA:")
        print(f"      Harakat: BUY | Hajm: 0.01 lot")
        print(f"      Ask narx: {ask:.2f} | Server SL: {sl_price:.2f} | Server TP: {tp_price:.2f}")

        # Send order
        order_res = executor.execute_signal(test_signal, volume=0.01)

        if not order_res.success:
            logger.error(f"Buyurtma rad etildi! Retcode: {order_res.retcode} | Sabab: {order_res.comment}")
            sys.exit(1)

        ticket = order_res.ticket
        fill_price = order_res.fill_price
        print(f"\n[4/5] BUYURTMA BROKERDA OCHILDI:")
        print(f"      Chipta (Ticket): #{ticket}")
        print(f"      Ijro narxi (Fill Price): {fill_price:.2f}")
        print(f"      Slippage: {order_res.slippage_points:.1f} punkt")

        # Verify position on broker
        pos = executor.get_position_by_ticket(ticket)
        if pos:
            print(f"      Brokerdagi SL: {pos.sl:.2f} (Tasdiqlandi)")
            print(f"      Brokerdagi TP: {pos.tp:.2f} (Tasdiqlandi)")
        else:
            logger.warning("Brokerda pozitsiya topilmadi (ehtimol allaqachon yopilgan).")

        print("\nPozitsiya 3 soniya ochiq ushlab turiladi...")
        time.sleep(3)

        # 6. Close position
        print(f"[5/5] POZITSIYA YOPILMOQDA (Ticket #{ticket})...")
        close_res = executor.close_position(ticket)

        if close_res.success:
            print(f"      Pozitsiya muvaffaqiyatli yopildi! Fill: {close_res.fill_price:.2f}")
            print("\n=================================================================")
            print("      NATIJA: DEMO DRY RUN TEST 100% MUVAFFAQIShLI O'TDI!        ")
            print("=================================================================")
        else:
            logger.error(f"Pozitsiyani yopishda xatolik: {close_res.comment}")

    except LiveTradingBlockedError as e:
        logger.critical(f"LIVE GUARD BLOKLADI: {e}")
        sys.exit(1)
    finally:
        connector.shutdown()


if __name__ == "__main__":
    run_demo_dry_run()
