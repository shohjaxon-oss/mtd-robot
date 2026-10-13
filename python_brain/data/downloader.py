"""Production-grade historical bar downloader for MetaTrader 5 symbols.

Features:
- Robust chunking (by monthly or yearly slices) to bypass MT5 API bar limits.
- Guaranteed UTC conversion with original broker time preserved.
- Resumable and idempotent Parquet storage under data/raw/<symbol>/<tf>/.
- Stores full bar attributes: time_utc, broker_time, open, high, low, close, tick_volume, spread, real_volume.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from python_brain.logger import app_logger

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


TIMEFRAME_MAP = {
    "M1": (mt5.TIMEFRAME_M1 if mt5 else 1, "M1", "month"),
    "M3": (getattr(mt5, "TIMEFRAME_M3", 3) if mt5 else 3, "M3", "month"),
    "M5": (mt5.TIMEFRAME_M5 if mt5 else 5, "M5", "month"),
    "M15": (mt5.TIMEFRAME_M15 if mt5 else 15, "M15", "year"),
    "H1": (mt5.TIMEFRAME_H1 if mt5 else 16385, "H1", "year"),
    "H4": (mt5.TIMEFRAME_H4 if mt5 else 16388, "H4", "year"),
    "D1": (mt5.TIMEFRAME_D1 if mt5 else 16408, "D1", "year"),
}


class HistoricalDataDownloader:
    """Manages chunked downloading and partitioned Parquet storage of MT5 candle data."""

    def __init__(
        self,
        symbol: str = "XAUUSDm",
        base_dir: str = "data/raw",
        broker_utc_offset_hours: float = 0.0,
    ):
        self.symbol = symbol
        self.base_dir = Path(base_dir)
        self.broker_utc_offset_hours = broker_utc_offset_hours

    def _convert_rates_to_df(self, rates: pd.DataFrame) -> pd.DataFrame:
        """Convert numpy structured array from MT5 to clean UTC DataFrame."""
        df = pd.DataFrame(rates)
        if df.empty:
            return df

        # Broker timestamp to datetime
        broker_dt = pd.to_datetime(df["time"], unit="s")
        # Offset adjustment to strict UTC
        utc_dt = broker_dt - pd.to_timedelta(self.broker_utc_offset_hours, unit="h")

        df["broker_time"] = broker_dt
        df["time_utc"] = utc_dt

        # Ensure correct column ordering and precision
        cols = [
            "time_utc",
            "broker_time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ]
        return df[cols].sort_values("time_utc").reset_index(drop=True)

    def download_range(
        self,
        timeframe_code: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> Optional[pd.DataFrame]:
        """Download candles between start_dt and end_dt."""
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not available!")

        rates = mt5.copy_rates_range(self.symbol, timeframe_code, start_dt, end_dt)
        if rates is None or len(rates) == 0:
            return None

        return self._convert_rates_to_df(rates)

    def download_and_save_timeframe(
        self,
        tf_name: str,
        start_year: int = 2022,
        end_year: Optional[int] = None,
        force_reload: bool = False,
    ) -> Dict[str, Any]:
        """Download historical bars in monthly/yearly chunks and save as partitioned Parquet files."""
        if tf_name not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {tf_name}. Available: {list(TIMEFRAME_MAP.keys())}")

        tf_code, _, partition_mode = TIMEFRAME_MAP[tf_name]
        now_utc = datetime.now(timezone.utc)
        target_end_year = end_year or now_utc.year

        output_dir = self.base_dir / self.symbol / tf_name
        output_dir.mkdir(parents=True, exist_ok=True)

        total_bars_downloaded = 0
        saved_files = []

        app_logger.info(
            f"Starting download for {self.symbol} [{tf_name}] from {start_year} to {target_end_year}..."
        )

        for year in range(start_year, target_end_year + 1):
            if partition_mode == "year":
                file_path = output_dir / f"{year}.parquet"
                if file_path.exists() and not force_reload and year < target_end_year:
                    app_logger.debug(f"Skipping existing yearly file: {file_path}")
                    continue

                dt_start = datetime(year, 1, 1, tzinfo=timezone.utc)
                dt_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                if year == target_end_year:
                    dt_end = now_utc

                df = self.download_range(tf_code, dt_start, dt_end)
                if df is not None and not df.empty:
                    df.to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
                    total_bars_downloaded += len(df)
                    saved_files.append(str(file_path))
                    app_logger.info(f"Saved {len(df)} bars to {file_path}")

            else:  # Monthly partitioning (M1, M5)
                for month in range(1, 13):
                    if year == target_end_year and month > now_utc.month:
                        break

                    file_path = output_dir / f"{year}_{month:02d}.parquet"
                    if file_path.exists() and not force_reload:
                        if not (year == target_end_year and month == now_utc.month):
                            app_logger.debug(f"Skipping existing monthly file: {file_path}")
                            continue

                    dt_start = datetime(year, month, 1, tzinfo=timezone.utc)
                    if month == 12:
                        dt_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                    else:
                        dt_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

                    if dt_start > now_utc:
                        break
                    if dt_end > now_utc:
                        dt_end = now_utc

                    df = self.download_range(tf_code, dt_start, dt_end)
                    if df is not None and not df.empty:
                        df.to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
                        total_bars_downloaded += len(df)
                        saved_files.append(str(file_path))
                        app_logger.info(f"Saved {len(df)} bars to {file_path}")

        app_logger.info(
            f"Completed [{tf_name}]: Downloaded {total_bars_downloaded} total bars across {len(saved_files)} files."
        )
        return {
            "timeframe": tf_name,
            "total_bars": total_bars_downloaded,
            "saved_files": saved_files,
        }

    def load_timeframe_data(
        self, tf_name: str, start_dt: Optional[datetime] = None, end_dt: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load and concatenate all stored Parquet chunks for a timeframe into a unified DataFrame."""
        tf_dir = self.base_dir / self.symbol / tf_name
        if not tf_dir.exists():
            return pd.DataFrame()

        parquet_files = sorted(list(tf_dir.glob("*.parquet")))
        if not parquet_files:
            return pd.DataFrame()

        dfs = [pd.read_parquet(f, engine="pyarrow") for f in parquet_files]
        combined = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["time_utc"])
        combined = combined.sort_values("time_utc").reset_index(drop=True)

        if start_dt is not None:
            combined = combined[combined["time_utc"] >= pd.to_datetime(start_dt)]
        if end_dt is not None:
            combined = combined[combined["time_utc"] <= pd.to_datetime(end_dt)]

        return combined
