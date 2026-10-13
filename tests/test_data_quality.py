"""Unit tests for DataQualityAuditor with synthetic corrupted datasets."""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest
from python_brain.data.quality import DataQualityAuditor


def create_synthetic_bars(count: int = 50, base_price: float = 2700.0) -> pd.DataFrame:
    """Generate a synthetically clean baseline DataFrame."""
    times = [
        datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=5 * i)
        for i in range(count)
    ]
    data = []
    for t in times:
        o = base_price
        h = base_price + 1.5
        l = base_price - 1.2
        c = base_price + 0.3
        data.append({
            "time_utc": t,
            "broker_time": t,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "tick_volume": 120,
            "spread": 240,
            "real_volume": 0,
        })
    return pd.DataFrame(data)


def test_clean_data_passes_audit():
    """Clean data should pass all checks without errors."""
    df = create_synthetic_bars(30)
    auditor = DataQualityAuditor()
    report = auditor.audit(df, timeframe="M5")

    assert report.is_clean is True
    assert report.duplicate_count == 0
    assert report.unordered_count == 0
    assert report.invalid_ohlc_count == 0
    assert report.unexpected_gap_count == 0


def test_detect_duplicate_timestamps():
    """Duplicates must be flagged accurately."""
    df = create_synthetic_bars(30)
    # Duplicate first row timestamp
    df.loc[1, "time_utc"] = df.loc[0, "time_utc"]

    auditor = DataQualityAuditor()
    report = auditor.audit(df, timeframe="M5")

    assert report.is_clean is False
    assert report.duplicate_count == 1


def test_detect_unordered_timestamps():
    """Non-chronological order must be flagged."""
    df = create_synthetic_bars(30)
    # Swap row 5 and row 6
    temp = df.loc[5, "time_utc"]
    df.loc[5, "time_utc"] = df.loc[6, "time_utc"]
    df.loc[6, "time_utc"] = temp

    auditor = DataQualityAuditor()
    report = auditor.audit(df, timeframe="M5")

    assert report.is_clean is False
    assert report.unordered_count > 0


def test_detect_broken_ohlc():
    """High < Low or High < Open/Close must be caught."""
    df = create_synthetic_bars(30)
    # Make high smaller than low
    df.loc[3, "high"] = 2650.0
    df.loc[3, "low"] = 2700.0

    auditor = DataQualityAuditor()
    report = auditor.audit(df, timeframe="M5")

    assert report.is_clean is False
    assert report.invalid_ohlc_count >= 1


def test_detect_zero_or_negative_prices():
    """Negative or zero price values must fail the audit."""
    df = create_synthetic_bars(30)
    df.loc[2, "close"] = -10.0

    auditor = DataQualityAuditor()
    report = auditor.audit(df, timeframe="M5")

    assert report.is_clean is False
    assert report.invalid_price_count >= 1


def test_detect_unexpected_intraweek_gaps():
    """Intra-week gaps (e.g. 2 hours missing on a Tuesday) must be flagged."""
    df = create_synthetic_bars(30)
    # Add an artificial gap of 4 hours on a Tuesday
    df.loc[15:, "time_utc"] = df.loc[15:, "time_utc"] + timedelta(hours=4)

    auditor = DataQualityAuditor()
    report = auditor.audit(df, timeframe="M5")

    assert report.is_clean is False
    assert report.unexpected_gap_count >= 1


def test_detect_extreme_atr_spikes():
    """Spikes exceeding 6x ATR must be caught."""
    df = create_synthetic_bars(40)
    # Artificial spike: normal range is 2.7, add range of 50.0
    df.loc[25, "high"] = df.loc[25, "low"] + 50.0

    auditor = DataQualityAuditor(spike_atr_multiplier=6.0)
    report = auditor.audit(df, timeframe="M5")

    assert report.spike_count >= 1


def test_detect_zero_volume_and_spread_anomaly():
    """Zero volume and spread anomalies must be captured."""
    df = create_synthetic_bars(30)
    df.loc[5, "tick_volume"] = 0
    df.loc[7, "spread"] = -5
    df.loc[8, "spread"] = 2500

    auditor = DataQualityAuditor(max_spread_points=800.0)
    report = auditor.audit(df, timeframe="M5")

    assert report.zero_volume_count == 1
    assert report.spread_anomaly_count == 2
