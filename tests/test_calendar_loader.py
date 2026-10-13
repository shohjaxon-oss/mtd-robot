"""Unit tests for economic calendar loading and news blackout calculation."""

from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pytest
from python_brain.news.calendar_loader import CalendarLoader


def test_calendar_loader_sample_generation_and_loading(tmp_path):
    """Test creating and ingesting sample economic calendar CSV."""
    sample_csv = tmp_path / "test_calendar.csv"
    CalendarLoader.generate_sample_calendar_csv(str(sample_csv))

    loader = CalendarLoader(broker_utc_offset_hours=0.0)
    df = loader.load_from_csv(str(sample_csv))

    assert not df.empty
    assert len(df) == 3
    assert "is_high_impact" in df.columns
    assert df["is_high_impact"].all()  # All sample items are NFP, CPI, FOMC


def test_blackout_windows_calculation(tmp_path):
    """Verify blackout time windows generation around high impact news."""
    sample_csv = tmp_path / "test_calendar.csv"
    CalendarLoader.generate_sample_calendar_csv(str(sample_csv))

    loader = CalendarLoader(broker_utc_offset_hours=0.0)
    df = loader.load_from_csv(str(sample_csv))

    windows = loader.get_blackout_windows(df, before_minutes=30, after_minutes=30)
    assert len(windows) == 3

    # Check NFP window
    start_utc, end_utc, event_name = windows[0]
    assert "Non-Farm" in event_name
    duration_mins = (end_utc - start_utc).total_seconds() / 60.0
    assert duration_mins == 60.0  # 30 mins before + 30 mins after
