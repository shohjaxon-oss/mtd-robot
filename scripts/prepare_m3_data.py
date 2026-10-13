"""Prepares M3 data for FU Formation strategy.

1. Resamples M1 data (UTC aligned :00, :03, :06, ...) to build synthetic M3.
2. Queries MT5 broker TIMEFRAME_M3 to extract native broker M3 history.
3. Compares both and stores under data/raw/XAUUSDm/M3/ (partitioned) and data/raw/XAUUSDm/M3_broker/.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_brain.data.downloader import HistoricalDataDownloader
from python_brain.mt5_connect import MT5Connector
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


def prepare_m3_data():
    print("=== PREPARING M3 DATA FOR FU FORMATION ===")
    downloader = HistoricalDataDownloader(symbol="XAUUSDm")

    # 1. Load M1 data
    df_m1 = downloader.load_timeframe_data("M1")
    print(f"Loaded {len(df_m1)} M1 bars from {df_m1['time_utc'].min()} to {df_m1['time_utc'].max()}")

    # 2. Resample M1 to M3 (:00, :03, :06, ...)
    df_m1["time_utc"] = pd.to_datetime(df_m1["time_utc"])
    df_m1_indexed = df_m1.set_index("time_utc").sort_index()

    m3_resampled = df_m1_indexed.resample("3min", closed="left", label="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "tick_volume": "sum",
        "spread": "last",
        "real_volume": "sum",
    }).dropna(subset=["open", "close"])

    # Filter out empty zero-volume periods (weekends, holidays)
    m3_resampled = m3_resampled[m3_resampled["tick_volume"] > 0].reset_index()
    m3_resampled["broker_time"] = m3_resampled["time_utc"]  # UTC+0 on Exness

    out_resampled_dir = Path("data/raw/XAUUSDm/M3")
    out_resampled_dir.mkdir(parents=True, exist_ok=True)

    # Save by month partition matching downloader schema
    m3_resampled["year_month"] = m3_resampled["time_utc"].dt.strftime("%Y_%m")
    for ym, group in m3_resampled.groupby("year_month"):
        file_path = out_resampled_dir / f"{ym}.parquet"
        group.drop(columns=["year_month"]).to_parquet(file_path, index=False, engine="pyarrow")

    print(f"Resampled M3 saved: {len(m3_resampled)} bars across {m3_resampled['year_month'].nunique()} monthly partitions.")

    # 3. Query native Broker M3 from MT5
    broker_m3_count = 0
    if mt5 is not None:
        connector = MT5Connector()
        if connector.connect():
            rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_M3, 0, 100000)
            if rates is not None and len(rates) > 0:
                df_bm3 = pd.DataFrame(rates)
                df_bm3["time_utc"] = pd.to_datetime(df_bm3["time"], unit="s", utc=True).dt.tz_localize(None)
                df_bm3["broker_time"] = df_bm3["time_utc"]
                broker_m3_count = len(df_bm3)

                out_broker_dir = Path("data/raw/XAUUSDm/M3_broker")
                out_broker_dir.mkdir(parents=True, exist_ok=True)
                df_bm3.to_parquet(out_broker_dir / "data.parquet", index=False, engine="pyarrow")
                print(f"Native Broker M3 saved: {len(df_bm3)} bars from {df_bm3['time_utc'].min()} to {df_bm3['time_utc'].max()}")
            connector.disconnect()

    print("=== M3 DATA PREPARATION COMPLETE ===")
    return len(m3_resampled), broker_m3_count


if __name__ == "__main__":
    prepare_m3_data()
