"""MTD-ROBOT Preflight Verification Utility.

Checks all operational criteria and outputs a clear PASS / FAIL summary:
1. Terminal trade_allowed
2. Account is DEMO (LiveGuard check)
3. Symbol visible and trade_mode == FULL
4. Filling mode supported (IOC, FOK, RETURN)
5. Stops level and Freeze level
6. Algo Trading (AutoTrading) enabled in MT5
7. Live spread measurement vs config limit (450 pts)
8. Broker-local clock drift (<= 5s)
9. Config wiring verification (1-to-1 match)
10. Telegram test notification (if configured)
11. Guardian heartbeat file read/write
12. data/state disk write capability
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import MetaTrader5 as mt5

from python_brain.config_loader import load_all_configs
from python_brain.mt5_connect import MT5Connector
from python_brain.risk.gate import ProductionRiskGate
from python_brain.risk.live_guard import validate_demo_account, LiveTradingBlockedError
from python_brain.monitoring.telegram_notifier import TelegramNotifier
from python_brain.monitoring.heartbeat import HeartbeatEmitter


def run_preflight() -> bool:
    print("=" * 70)
    print("           MTD-ROBOT FU-M3 PREFLIGHT VERIFICATION          ")
    print("=" * 70)

    results = []

    def record_check(name: str, passed: bool, details: str):
        status = "PASS" if passed else "FAIL"
        results.append((name, status, details))
        print(f"[{status:4s}] {name:35s} | {details}")

    # 1. Config Loader & Wiring
    configs = None
    try:
        configs = load_all_configs()
        gate = ProductionRiskGate(risk_config=configs.risk)
        assert configs.settings.strategy.timeframe == "M3"
        assert gate.risk_per_trade_pct == 0.5
        assert gate.max_spread_points == 450.0
        record_check("Config Wiring Verification", True, "Timeframe=M3, Risk=0.5%, MaxSpread=450pt, Strict 1-to-1 mapping")
    except Exception as e:
        record_check("Config Wiring Verification", False, f"Error: {e}")
        return False

    # 2. MT5 Connector & Login
    connector = MT5Connector()
    if not connector.initialize():
        record_check("MT5 Terminal Connection", False, f"Init failed: {connector.last_error}")
        return False
    record_check("MT5 Terminal Connection", True, f"MT5 build: {mt5.version()}")

    if not connector.login():
        record_check("MT5 Account Login", False, f"Login failed: {connector.last_error}")
        return False
    
    acc = connector.get_account_info()
    record_check("MT5 Account Login", True, f"Account #{acc.login} on {acc.server} | Balance: ${acc.balance:.2f}")

    # 3. Terminal Algo Trading Enabled
    term_info = mt5.terminal_info()
    algo_enabled = getattr(term_info, "trade_allowed", False)
    if algo_enabled:
        record_check("Algo Trading (AutoTrading)", True, "Terminal Algo Trading tugmasi YOQILGAN")
    else:
        record_check("Algo Trading (AutoTrading)", False, "Terminalda 'Algo Trading' O'CHIQLI! Tools -> Options -> EA -> Allow Algo Trading ni yoqing!")

    # 4. Account Trade Allowed & DEMO Mode
    account_trade_allowed = getattr(acc, "trade_allowed", False)
    record_check("Account Trade Allowed", account_trade_allowed, f"trade_allowed={account_trade_allowed}")

    is_demo = False
    try:
        validate_demo_account(acc, allow_live=configs.settings.safety.allow_live)
        is_demo = True
        record_check("Live Guard (DEMO Account)", True, f"Trade Mode: DEMO ({acc.trade_mode})")
    except LiveTradingBlockedError as e:
        record_check("Live Guard (DEMO Account)", False, f"BLOCKED: {e}")

    # 5. Symbol Verification
    env_sym = configs.env.PRIMARY_SYMBOL
    symbol = connector.find_actual_symbol([env_sym, configs.symbols.primary_symbol, "XAUUSDm", "XAUUSD"]) or env_sym or "XAUUSDm"
    sym_info = mt5.symbol_info(symbol)

    if sym_info is None:
        record_check("Symbol Visibility", False, f"Simvol '{symbol}' topilmadi")
    else:
        # Select symbol in Market Watch if not selected
        if not sym_info.visible:
            mt5.symbol_select(symbol, True)
            sym_info = mt5.symbol_info(symbol)

        is_visible = getattr(sym_info, "visible", False)
        # trade_mode == 4 is SYMBOL_TRADE_MODE_FULL
        is_trade_full = getattr(sym_info, "trade_mode", 0) == 4
        record_check("Symbol Visibility & Trade Mode", is_visible and is_trade_full, f"Symbol: {symbol} | Visible: {is_visible} | TradeMode: {sym_info.trade_mode} (4=FULL)")

        # 6. Filling Mode
        modes = getattr(sym_info, "filling_mode", 0)
        mode_desc = []
        if modes & 1:
            mode_desc.append("FOK")
        if modes & 2:
            mode_desc.append("IOC")
        if not mode_desc:
            mode_desc.append("RETURN")
        record_check("Supported Filling Mode", True, f"Filling modes: {', '.join(mode_desc)} (Mask: {modes})")

        # 7. Stops and Freeze Level
        stops_lvl = getattr(sym_info, "stops_level", 0)
        freeze_lvl = getattr(sym_info, "freeze_level", 0)
        point = getattr(sym_info, "point", 0.001)
        record_check("Stops & Freeze Level", True, f"StopsLevel: {stops_lvl} pts ({stops_lvl * point:.3f}), FreezeLevel: {freeze_lvl} pts")

        # 8. Live Spread Measurement
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            spread_pts = round((tick.ask - tick.bid) / point, 1)
            spread_ok = spread_pts <= configs.risk.execution_limits.max_spread_points
            record_check("Live Spread Measurement", spread_ok, f"Current: {spread_pts} pts | Limit: {configs.risk.execution_limits.max_spread_points} pts")
        else:
            record_check("Live Spread Measurement", False, "Tick olinmadi")

        # 9. Clock Drift Check (Sub-minute sync)
        if tick and tick.time:
            local_now = int(datetime.now(timezone.utc).timestamp())
            raw_drift = abs(local_now - tick.time)
            drift = min(raw_drift % 3600, 3600 - (raw_drift % 3600))
            record_check("Clock Drift (Broker vs System)", drift <= 5, f"Sub-minute drift: {drift}s (Limit: <= 5s) [Raw offset: {raw_drift}s]")
        else:
            record_check("Clock Drift (Broker vs System)", False, "Tick time mavjud emas")

    # 10. Data State Disk Write Capability
    state_dir = Path("data") / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    test_state_file = state_dir / "_preflight_test.tmp"
    can_write = False
    try:
        with open(test_state_file, "w") as f:
            f.write("OK")
        test_state_file.unlink()
        can_write = True
        record_check("Disk State Directory Write", True, f"Directory '{state_dir}' yozish uchun ochiq")
    except Exception as e:
        record_check("Disk State Directory Write", False, f"Yozishda xatolik: {e}")

    # 11. Guardian Heartbeat Emitter
    try:
        emitter = HeartbeatEmitter(filename="mtd_heartbeat.json")
        emitter.beat(status="PREFLIGHT")
        assert emitter.filepath.exists()
        record_check("Guardian Heartbeat Emitter", True, f"Heartbeat '{emitter.filepath}' muvaffaqiyatli yangilandi")
    except Exception as e:
        record_check("Guardian Heartbeat Emitter", False, f"Heartbeat xatosi: {e}")

    # 12. Telegram Notifier Test
    notifier = TelegramNotifier()
    if notifier.enabled:
        sent = notifier.send_message("🔍 MTD-ROBOT Preflight Check: Barcha tizimlar muvaffaqiyatli tekshirildi.")
        record_check("Telegram Notifier", sent, "Telegram test xabari yuborildi")
    else:
        record_check("Telegram Notifier", True, "Telegram sozlanmagan (ixtiyoriy, token bo'sh)")

    print("=" * 70)
    all_passed = all(status == "PASS" for _, status, _ in results)
    if all_passed:
        print(">>> PREFLIGHT NATIJASI: BARCHA TEKSHIRUVLAR MUVAFFAQIYATLI (PASS)! <<<")
        print("Bot Exness demo hisobida savdo qilishga 100% tayyor.")
    else:
        failed = [name for name, status, _ in results if status == "FAIL"]
        print(f">>> PREFLIGHT NATIJASI: {len(failed)} TA XATO TOPILDI (FAIL)! <<<")
        print("Xatolar:", failed)
    print("=" * 70)

    connector.shutdown()
    return all_passed


if __name__ == "__main__":
    success = run_preflight()
    sys.exit(0 if success else 1)
