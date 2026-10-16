"""Historical M3 Signal Replay & Diagnostic Utility.

Fetches the last N days of M3 bars directly from MT5, runs them through
the exact same FU-Formation strategy and ProductionRiskGate logic (WITHOUT sending orders),
and prints an intuitive table showing exactly:
- Timestamp (UTC)
- Signal Direction (BUY/SELL)
- Entry Quote / SL / Risk Distance
- Risk Gate Decision & Rejection Reason

Quickly answers: "Why didn't the bot open a position on past candles?"
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import MetaTrader5 as mt5

from python_brain.config_loader import load_all_configs
from python_brain.mt5_connect import MT5Connector
from python_brain.signals.fu_formation import FUFormationStrategy
from python_brain.risk.gate import ProductionRiskGate
from python_brain.backtest.models import AccountState


def replay_signals(days: int = 5):
    print("=" * 80)
    print(f"       MTD-ROBOT FU-M3 HISTORICAL SIGNAL REPLAY (LAST {days} DAYS)       ")
    print("=" * 80)

    # 1. Configs & MT5
    configs = load_all_configs()
    connector = MT5Connector()
    if not connector.initialize():
        print(f"XATOLIK: MT5 terminali bilan bog'lanib bo'lmadi: {connector.last_error}")
        return

    if not connector.login():
        print(f"XATOLIK: MT5 ga kirib bo'lmadi: {connector.last_error}")
        connector.shutdown()
        return

    env_sym = configs.env.PRIMARY_SYMBOL
    symbol = connector.find_actual_symbol([env_sym, configs.symbols.primary_symbol, "XAUUSDm", "XAUUSD"]) or "XAUUSDm"

    # Select symbol
    mt5.symbol_select(symbol, True)
    sym_info = mt5.symbol_info(symbol)
    point = getattr(sym_info, "point", 0.001) if sym_info else 0.001

    # 2. Fetch M3 bars
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(days=days)
    print(f"Ma'lumotlar olinmoqda: {symbol} | Davr: {start_utc.strftime('%Y-%m-%d %H:%M')} dan {now_utc.strftime('%Y-%m-%d %H:%M')} gacha...")

    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M3, start_utc, now_utc)
    if rates is None or len(rates) == 0:
        print("XATOLIK: MT5 dan M3 barlarini olib bo'lmadi!")
        connector.shutdown()
        return

    df_all = pd.DataFrame(rates)
    df_all["time_utc"] = pd.to_datetime(df_all["time"], unit="s", utc=True)
    total_bars = len(df_all)
    print(f"Jami {total_bars} ta M3 bar yuklandi.")

    # 3. Strategy & Risk Gate Initialization
    strategy = FUFormationStrategy(
        timeframe="M3",
        min_trend_candles=3,
        engulf_mode="body",
        sl_buffer_pips=5.0,
        tp1_pips=20.0,
        tp2_pips=30.0,
        lot_per_leg=0.01,
        pip_size_price=0.10,
    )

    acc = connector.get_account_info()
    init_balance = getattr(acc, "balance", 10000.0)
    gate = ProductionRiskGate(
        risk_config=configs.risk,
        demo_profile=True,
    )

    signals_found = []
    
    # 4. Iterate over bars (simulating closed bars step by step)
    for i in range(10, total_bars):
        slice_df = df_all.iloc[:i]
        sig = strategy.on_bar(slice_df)
        if sig is not None:
            bar_time = sig.time_utc
            close_price = slice_df.iloc[-1]["close"]
            sl_price = sig.sl
            dist = abs(close_price - sl_price)
            dist_pips = dist / 0.10

            # Mock account state for evaluation
            mock_account = AccountState(
                initial_balance=init_balance,
                equity=init_balance,
                balance=init_balance,
                free_margin=init_balance,
                leverage=getattr(acc, "leverage", 100),
                daily_realized_pnl=0.0,
                weekly_realized_pnl=0.0,
            )

            # Evaluate through Risk Gate
            # Typical spread ~220 points
            decision = gate.evaluate(
                signal=sig,
                account=mock_account,
                current_spread_pts=220.0,
                current_time_utc=bar_time,
                execution_price=close_price,
            )

            signals_found.append({
                "time": bar_time.strftime("%Y-%m-%d %H:%M"),
                "action": sig.action,
                "price": close_price,
                "sl": sl_price,
                "dist_pips": round(dist_pips, 1),
                "approved": decision.approved,
                "reason": "APPROVED" if decision.approved else decision.reject_reason,
            })

    connector.shutdown()

    # 5. Output Summary Table
    print("\n" + "=" * 95)
    header_dir = "Yonalish"
    print(f"{'Vaqt (UTC)':18s} | {header_dir:9s} | {'Narx':8s} | {'SL':8s} | {'SL (pip)':8s} | {'Risk Gate Qarori':30s}")
    print("-" * 95)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not signals_found:
        print(f"Oxirgi {days} kun davomida birorta ham FU Formation signali topilmadi.")
    else:
        for s in signals_found:
            status_symbol = "[OK]    " if s["approved"] else "[REJECT]"
            action_colored = f"{s['action']:5s}"
            print(
                f"{s['time']:18s} | {action_colored}     | {s['price']:8.2f} | {s['sl']:8.2f} | "
                f"{s['dist_pips']:6.1f} p | {status_symbol} {s['reason'][:35]}"
            )

    print("=" * 95)
    approved_count = sum(1 for s in signals_found if s["approved"])
    rejected_count = len(signals_found) - approved_count
    print(f"JAMI SIGNALLAR: {len(signals_found)} ta | TASDIQLANDI: {approved_count} ta | RAD ETILDI: {rejected_count} ta")
    print("=" * 95)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay historical M3 signals and check Risk Gate decisions")
    parser.add_argument("--days", type=int, default=5, help="Number of historical days to inspect (default: 5)")
    args = parser.parse_args()

    replay_signals(days=args.days)
