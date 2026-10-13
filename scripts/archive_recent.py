"""Incremental data archiver for XAUUSDm M1 candles and raw ticks.

Designed to be executed periodically (e.g. weekly via Windows Task Scheduler)
to accumulate proprietary deep M1 and tick archives that the broker server purges.
Appends new bars/ticks without duplicates and saves them into data/archive/ in Parquet format.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from python_brain.config_loader import load_all_configs
from python_brain.logger import app_logger, setup_logger
from python_brain.mt5_connect import MT5Connector

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


def archive_m1_bars(symbol: str = "XAUUSDm", archive_root: str = "data/archive") -> int:
    """Fetch recent M1 bars and append deduplicated to archive."""
    out_dir = Path(archive_root) / symbol / "M1"
    out_dir.mkdir(parents=True, exist_ok=True)

    app_logger.info(f"Archiving recent M1 bars for {symbol}...")
    # Fetch latest 50,000 bars
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50000)
    if rates is None or len(rates) == 0:
        app_logger.warning("No M1 bars returned from MT5.")
        return 0

    df_new = pd.DataFrame(rates)
    df_new["broker_time"] = pd.to_datetime(df_new["time"], unit="s")
    df_new["time_utc"] = df_new["broker_time"]  # Exness is UTC+0

    cols = ["time_utc", "broker_time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    df_new = df_new[cols]

    # Partition by month
    df_new["year_month"] = df_new["time_utc"].dt.strftime("%Y_%m")
    total_added = 0

    for ym, group in df_new.groupby("year_month"):
        file_path = out_dir / f"{ym}.parquet"
        if file_path.exists():
            existing = pd.read_parquet(file_path, engine="pyarrow")
            combined = pd.concat([existing, group[cols]], ignore_index=True)
            combined = combined.drop_duplicates(subset=["time_utc"]).sort_values("time_utc").reset_index(drop=True)
            new_count = len(combined) - len(existing)
            combined.to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
            total_added += max(0, new_count)
        else:
            group[cols].to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
            total_added += len(group)

    app_logger.info(f"M1 Archive updated: added {total_added} new unique bars.")
    return total_added


def archive_ticks(symbol: str = "XAUUSDm", archive_root: str = "data/archive", days_back: int = 7) -> int:
    """Fetch recent ticks (last N days) and append deduplicated to archive."""
    out_dir = Path(archive_root) / symbol / "ticks"
    out_dir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(days=days_back)

    app_logger.info(f"Archiving ticks for {symbol} from {start_utc.strftime('%Y-%m-%d')} to {now_utc.strftime('%Y-%m-%d')}...")
    ticks = mt5.copy_ticks_range(symbol, start_utc, now_utc, mt5.COPY_TICKS_ALL)
    if ticks is None or len(ticks) == 0:
        app_logger.warning("No ticks returned from MT5.")
        return 0

    df_ticks = pd.DataFrame(ticks)
    df_ticks["time_utc"] = pd.to_datetime(df_ticks["time"], unit="s")
    df_ticks["time_msc_utc"] = pd.to_datetime(df_ticks["time_msc"], unit="ms")

    # Partition by week
    df_ticks["year_week"] = df_ticks["time_utc"].dt.strftime("%Y_W%W")
    cols = ["time_utc", "time_msc_utc", "bid", "ask", "last", "volume", "flags"]
    total_added = 0

    for yw, group in df_ticks.groupby("year_week"):
        file_path = out_dir / f"{yw}.parquet"
        if file_path.exists():
            existing = pd.read_parquet(file_path, engine="pyarrow")
            combined = pd.concat([existing, group[cols]], ignore_index=True)
            combined = combined.drop_duplicates(subset=["time_msc_utc", "bid", "ask"]).sort_values("time_msc_utc").reset_index(drop=True)
            new_count = len(combined) - len(existing)
            combined.to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
            total_added += max(0, new_count)
        else:
            group[cols].to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
            total_added += len(group)

    app_logger.info(f"Tick Archive updated: added {total_added} new unique ticks.")
    return total_added


def main():
    config = load_all_configs()
    setup_logger(log_level="INFO", mask_secrets=True)

    connector = MT5Connector(
        path=config.env.MT5_PATH,
        login=config.env.MT5_LOGIN,
        password=config.env.MT5_PASSWORD,
        server=config.env.MT5_SERVER,
    )

    if not connector.connect():
        print("[ERROR] Failed to connect to MT5 for archiving.")
        return 1

    symbol = "XAUUSDm"
    try:
        added_m1 = archive_m1_bars(symbol)
        added_ticks = archive_ticks(symbol, days_back=7)
        print(f"\n[OK] Archiving completed successfully: +{added_m1} M1 bars, +{added_ticks} ticks.")
        return 0
    finally:
        connector.disconnect()


if __name__ == "__main__":
    sys.exit(main())
