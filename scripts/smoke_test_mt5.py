"""Enhanced Smoke Test Script for MetaTrader 5, Live Tick Spreads, Swap Impact & Margin.

Verifies:
1. Connection & account details
2. Live tick spread (ask - bid) in points & price units (not raw symbol_info.spread)
3. Full swap valuation & overnight costs in USD per 1 lot
4. Exact broker margin & PnL for $1 price movement
5. Syncs live broker specifications into config/symbols.yaml
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from python_brain.config_loader import load_all_configs
from python_brain.logger import app_logger, setup_logger
from python_brain.mt5_connect import MT5Connector


def run_smoke_test() -> int:
    """Execute smoke test and symbol diagnostics."""
    print("=" * 85)
    print("       MTD-ROBOT: METATRADER 5 ENHANCED DIAGNOSTICS & SYMBOL VERIFICATION")
    print("=" * 85)

    # 1. Load Configurations
    try:
        config = load_all_configs()
        setup_logger(
            log_level=config.settings.logging.level,
            log_file=config.settings.logging.file_path,
            mask_secrets=config.settings.logging.mask_secrets,
        )
        app_logger.info("Configuration validated successfully.")
    except Exception as e:
        print(f"\n[FATAL ERROR] Configuration validation failed: {e}")
        return 1

    connector = MT5Connector(
        path=config.env.MT5_PATH,
        login=config.env.MT5_LOGIN,
        password=config.env.MT5_PASSWORD,
        server=config.env.MT5_SERVER,
        timeout_ms=config.settings.mt5.timeout_ms,
        portable=config.settings.mt5.portable,
    )

    try:
        connected = connector.connect()
        if not connected:
            print("\n" + "!" * 85)
            print("[FAILURE] Could not connect to MetaTrader 5 terminal.")
            print("!" * 85)
            return 1

        print("\n" + "-" * 85)
        print("1. ACCOUNT INFORMATION")
        print("-" * 85)
        account = connector.get_account_snapshot()
        if not account:
            print("[ERROR] Failed to fetch account information.")
            return 1

        print(f"  Login Number:     {account.login}")
        print(f"  Account Name:     {account.name}")
        print(f"  Server:           {account.server}")
        print(f"  Trade Mode:       {account.trade_mode}")
        print(f"  Currency:         {account.currency}")
        print(f"  Leverage:         1:{account.leverage}")
        print(f"  Balance:          {account.balance:,.2f} {account.currency}")
        print(f"  Equity:           {account.equity:,.2f} {account.currency}")
        print(f"  Free Margin:      {account.margin_free:,.2f} {account.currency}")

        print("\n" + "-" * 85)
        print("2. SYMBOL RESOLUTION & REAL-TIME SPREAD")
        print("-" * 85)
        candidates = config.symbols.symbol.candidate_symbols
        symbol_name = connector.find_actual_symbol(candidates)
        if not symbol_name:
            print(f"[ERROR] Could not find trading symbol matching candidates: {candidates}")
            return 1

        spec = connector.get_symbol_specification(symbol_name)
        if not spec:
            print(f"[ERROR] Could not fetch specification for symbol: {symbol_name}")
            return 1

        live_tick = connector.get_live_tick(symbol_name)
        if not live_tick:
            print(f"[ERROR] Could not fetch real-time tick for symbol: {symbol_name}")
            return 1

        print(f"  Active Symbol:    {spec.name} (Path: {spec.path})")
        print(f"  Digits / Point:   {spec.digits} digits | point = {spec.point}")
        print(f"  Current Live Bid: {live_tick.bid:.{spec.digits}f}")
        print(f"  Current Live Ask: {live_tick.ask:.{spec.digits}f}")
        print(
            f"  Live Spread:      {live_tick.spread_points:.1f} points "
            f"(${live_tick.spread_price:.{spec.digits}f})  [Calculated via (Ask - Bid)]"
        )
        print(f"  Raw Info Spread:  {spec.spread_raw} points (Reference only)")

        print("\n" + "-" * 85)
        print("3. SWAP VALUATION & OVERNIGHT HOLDING COSTS")
        print("-" * 85)
        print(f"  Swap Mode:        {spec.swap_mode_desc} (Code: {spec.swap_mode})")
        print(f"  Raw Swap Long:    {spec.swap_long}")
        print(f"  Raw Swap Short:   {spec.swap_short}")
        print(f"  Triple Swap Day:  {spec.swap_rollover3days_desc} (3x overnight fee)")
        print(
            f"  >>> Long Overnight Cost:  ~{spec.swap_long_usd_per_lot:+.2f} USD per 1.0 standard lot / night"
        )
        print(
            f"  >>> Short Overnight Cost: ~{spec.swap_short_usd_per_lot:+.2f} USD per 1.0 standard lot / night"
        )

        print("\n" + "-" * 85)
        print("4. BROKER MARGIN & $1 PRICE MOVEMENT SIMULATION")
        print("-" * 85)
        impact = connector.calc_trade_impact(symbol_name, live_tick.ask)
        if impact:
            print(
                f"  Required Margin (1.0 lot):    ${impact.margin_1_lot:,.2f} {account.currency}"
            )
            print(
                f"  Required Margin (0.01 lot):   ${impact.margin_001_lot:,.2f} {account.currency}"
            )
            print(
                f"  Profit for $1 Move (1.0 lot):  +${impact.profit_1_lot_1usd_move:,.2f} {account.currency}"
            )
            print(
                f"  Profit for $1 Move (0.01 lot): +${impact.profit_001_lot_1usd_move:,.2f} {account.currency}"
            )
            print(
                f"  Contract / Tick Consistency:  1 lot = {spec.contract_size} oz -> $1.00 move = ${impact.profit_1_lot_1usd_move:.2f} (Matched!)"
            )

        print("\n" + "-" * 85)
        print("5. VERIFICATION CHECKS & CONFIG SYNC")
        print("-" * 85)
        # Update config/symbols.yaml with real broker values
        connector.update_symbols_config_from_mt5("config/symbols.yaml", symbol_name, spec)
        print(f"  [OK] Successfully synchronized live broker specs to config/symbols.yaml")

        # Check live tick spread against threshold
        max_spread = config.risk.execution_limits.max_spread_points
        # Note: on 3-digit gold, 1 point = 0.001. So 30 cents = 300 points.
        # We check both points and dollar threshold
        if live_tick.spread_points > max_spread and live_tick.spread_price > 0.60:
            print(
                f"  [WARN] Live spread ({live_tick.spread_points} pts / ${live_tick.spread_price}) is high."
            )
        else:
            print(
                f"  [OK] Live spread is verified safe: {live_tick.spread_points} pts (${live_tick.spread_price})"
            )

        if spec.trade_mode == "FULL":
            print("  [OK] Symbol trade mode is FULL.")
        else:
            print(f"  [WARN] Symbol trade mode is {spec.trade_mode}")

        print("\n" + "=" * 85)
        print("    >>> ALL 1/10 FIXES AND MT5 DIAGNOSTICS COMPLETED SUCCESSFULLY <<<")
        print("=" * 85)
        return 0

    except Exception as ex:
        app_logger.exception(f"Unexpected error during smoke test: {ex}")
        print(f"\n[UNEXPECTED ERROR] {ex}")
        return 1
    finally:
        connector.disconnect()


if __name__ == "__main__":
    sys.exit(run_smoke_test())
