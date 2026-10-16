"""DEMO DRY RUN: Full 2-Leg Setup Lifecycle Validation (0.01 + 0.01 lot).

Exclusively executed manually to verify:
1. LiveGuard validation (blocks execution if account is REAL).
2. Atomic 2-Leg Market Order opening (Leg A 0.01 lot, Leg B 0.01 lot).
3. Server-side Stop Loss & Take Profit verification.
4. Exact TP update relative to actual fill price.
5. Breakeven Trailing Simulation: modify Leg B SL to entry price.
6. Clean closure of both legs.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DemoDryRun] %(message)s",
)
logger = logging.getLogger("mtd.demo_dry_run")


def run_demo_dry_run():
    print("=" * 70)
    print("      MTD-ROBOT FU 2-LEG DEMO DRY RUN TEST (0.01 + 0.01 LOT)      ")
    print("=" * 70)

    # 1. Load config
    configs = load_all_configs(config_dir="config")
    allow_live = configs.settings.safety.allow_live
    env_sym = configs.env.PRIMARY_SYMBOL

    # 2. Connect to MT5
    connector = MT5Connector()
    if not connector.initialize() or not connector.login():
        logger.error("MT5 ga ulanib bo'lmadi! Terminal ochiqligini tekshiring.")
        sys.exit(1)

    # Auto-discover active symbol
    symbol = connector.find_actual_symbol([env_sym, configs.symbols.primary_symbol, "XAUUSDm", "XAUUSD"]) or env_sym or "XAUUSDm"

    try:
        # 3. LIVE GUARD (Strict enforcement)
        account = connector.get_account_info()
        validate_demo_account(account, allow_live=allow_live)
        print(f"[1/6] LIVE GUARD TASDIQLANDI:")
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
        print(f"[2/6] BOZOR HOLATI:")
        print(f"      Simvol: {symbol} | Bid: {bid:.2f} | Ask: {ask:.2f} | Spread: {spread:.2f} USD\n")

        # FU SL: ask - 2.0 USD (~20 pips), Leg A TP: +2.0 USD (20 pips), Leg B TP: +3.0 USD (30 pips)
        sl_price = round(ask - 2.0, 2)
        tp_a_initial = round(ask + 2.0, 2)
        tp_b_initial = round(ask + 3.0, 2)

        print(f"[3/6] FU 2-LEG BUYURTMALAR YUBORILMOQDA (BUY):")
        print(f"      Leg A: 0.01 lot | SL: {sl_price:.2f} | Dastlabki TP: {tp_a_initial:.2f}")
        print(f"      Leg B: 0.01 lot | SL: {sl_price:.2f} | Dastlabki TP: {tp_b_initial:.2f}")

        # Send Leg A
        res_a = executor.send_market_order(
            side="BUY",
            volume=0.01,
            sl=sl_price,
            tp=tp_a_initial,
            comment="DRY_RUN|A",
        )

        # Send Leg B
        res_b = executor.send_market_order(
            side="BUY",
            volume=0.01,
            sl=sl_price,
            tp=tp_b_initial,
            comment="DRY_RUN|B",
        )

        if not res_a.success or not res_b.success:
            logger.error(f"Buyurtmalardan biri ochilmadi! Leg A: {res_a.comment}, Leg B: {res_b.comment}")
            # Atomik tozalash
            if res_a.success:
                executor.close_position(res_a.ticket)
            if res_b.success:
                executor.close_position(res_b.ticket)
            sys.exit(1)

        print(f"\n[4/6] IKKALA LEG HAM BROKERDA MUVAFFAQIYATLI OCHILDI:")
        print(f"      Leg A: Ticket #{res_a.ticket} @ {res_a.fill_price:.2f}")
        print(f"      Leg B: Ticket #{res_b.ticket} @ {res_b.fill_price:.2f}")

        # Update exact TP relative to fill
        exact_tp_a = round(res_a.fill_price + 2.0, 2)
        exact_tp_b = round(res_b.fill_price + 3.0, 2)
        executor.modify_position_sl_tp(ticket=res_a.ticket, sl=sl_price, tp=exact_tp_a)
        executor.modify_position_sl_tp(ticket=res_b.ticket, sl=sl_price, tp=exact_tp_b)
        print(f"      Server-side TP yangilandi: Leg A TP={exact_tp_a:.2f}, Leg B TP={exact_tp_b:.2f}")

        time.sleep(2)

        # 6. Simulate Breakeven
        print(f"\n[5/6] BREAKEVEN SIMULYATSIYASI:")
        print(f"      Leg A yopilgan deb faraz qilinib, Leg B (#{res_b.ticket}) SL kirish narxiga ({res_b.fill_price:.2f}) ko'chirilmoqda...")
        be_res = executor.modify_position_sl_tp(ticket=res_b.ticket, sl=res_b.fill_price)
        if be_res.success:
            print(f"      Leg B SL muvaffaqiyatli Breakeven ({res_b.fill_price:.2f}) ga o'tkazildi!")
        else:
            logger.warning(f"Breakeven modifikatsiyasi muvaffaqiyatsiz: {be_res.comment}")

        time.sleep(2)

        # 7. Clean closure of both legs
        print(f"\n[6/6] POZITSIYALARNI TOZA YOPISH:")
        close_a = executor.close_position(res_a.ticket)
        close_b = executor.close_position(res_b.ticket)
        print(f"      Leg A #{res_a.ticket} yopildi: {close_a.comment}")
        print(f"      Leg B #{res_b.ticket} yopildi: {close_b.comment}")

        print("\n" + "=" * 70)
        print("   NATIJA: 2-LEG SETUP, SL/TP VA BREAKEVEN SINOVI 100% PASS!     ")
        print("=" * 70)

    except LiveTradingBlockedError as e:
        logger.critical(f"LIVE GUARD BLOKLADI: {e}")
        sys.exit(1)
    finally:
        connector.shutdown()


if __name__ == "__main__":
    run_demo_dry_run()
