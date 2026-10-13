"""Unit tests for HistoricalDataDownloader including UTC conversion and Parquet I/O."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest
from python_brain.data.downloader import HistoricalDataDownloader


@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary storage path fixture."""
    return tmp_path / "raw"


def test_utc_timezone_conversion():
    """Verify that broker time is accurately offset to UTC and preserved in broker_time."""
    # Test with broker at UTC+2 (e.g. Cyprus EET)
    downloader = HistoricalDataDownloader(
        symbol="XAUUSDm",
        broker_utc_offset_hours=2.0,
    )

    # Simulated MT5 structured array
    broker_ts = int(datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc).timestamp())
    fake_rates = pd.DataFrame([{
        "time": broker_ts,
        "open": 2700.0,
        "high": 2702.0,
        "low": 2699.0,
        "close": 2701.0,
        "tick_volume": 100,
        "spread": 240,
        "real_volume": 0,
    }])

    df = downloader._convert_rates_to_df(fake_rates)
    assert not df.empty
    assert "time_utc" in df.columns
    assert "broker_time" in df.columns

    # Broker time is 14:00, adjusted UTC must be 12:00 (14 - 2)
    assert df["broker_time"].iloc[0].hour == 14
    assert df["time_utc"].iloc[0].hour == 12


def test_downloader_mocked_download_and_parquet_io(temp_data_dir):
    """Test chunked download and Parquet read/write roundtrip."""
    downloader = HistoricalDataDownloader(
        symbol="XAUUSDm",
        base_dir=str(temp_data_dir),
        broker_utc_offset_hours=0.0,
    )

    fake_rates = [
        (1770000000, 2700.0, 2705.0, 2695.0, 2702.0, 150, 240, 0),
        (1770000300, 2702.0, 2706.0, 2701.0, 2704.0, 160, 240, 0),
    ]
    rates_array = np.array(
        fake_rates,
        dtype=[
            ("time", "i8"),
            ("open", "f8"),
            ("high", "f8"),
            ("low", "f8"),
            ("close", "f8"),
            ("tick_volume", "i8"),
            ("spread", "i4"),
            ("real_volume", "i8"),
        ],
    )

    mock_mt5 = MagicMock()
    mock_mt5.copy_rates_range.return_value = rates_array

    with patch("python_brain.data.downloader.mt5", mock_mt5):
        result = downloader.download_and_save_timeframe("D1", start_year=2026, end_year=2026)
        assert result["total_bars"] == 2
        assert len(result["saved_files"]) == 1

        # Read back
        loaded_df = downloader.load_timeframe_data("D1")
        assert len(loaded_df) == 2
        assert loaded_df["close"].iloc[1] == 2704.0
