"""Unit tests for session labeling and spread profiling."""

from datetime import datetime, timezone
import pandas as pd
from python_brain.data.session_profile import compute_spread_profile, tag_sessions


def test_session_tagging():
    """Verify that candles are correctly tagged with UTC sessions."""
    # Test timestamps for Asia (03:00 UTC), London (09:00 UTC), Overlap (14:00 UTC), NY (18:00 UTC), Rollover (21:00 UTC)
    test_rows = [
        {"time_utc": datetime(2026, 9, 2, 3, 0, tzinfo=timezone.utc), "spread": 210},
        {"time_utc": datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc), "spread": 200},
        {"time_utc": datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc), "spread": 190},
        {"time_utc": datetime(2026, 9, 2, 18, 0, tzinfo=timezone.utc), "spread": 205},
        {"time_utc": datetime(2026, 9, 2, 21, 30, tzinfo=timezone.utc), "spread": 350},
    ]
    df = pd.DataFrame(test_rows)
    tagged = tag_sessions(df)

    assert tagged.loc[0, "primary_session"] == "Asia"
    assert tagged.loc[1, "primary_session"] == "London"
    assert tagged.loc[2, "primary_session"] == "London-NY Overlap"
    assert tagged.loc[3, "primary_session"] == "New York"
    assert tagged.loc[4, "primary_session"] == "Off-Hours/Rollover"


def test_spread_profile_computation():
    """Verify aggregation of hourly and session spread statistics."""
    rows = []
    # Create multiple samples
    for h in [9, 14, 21]:
        for s in [200, 220, 240, 260]:
            rows.append({
                "time_utc": datetime(2026, 9, 2, h, 0, tzinfo=timezone.utc),
                "spread": s,
            })
    df = pd.DataFrame(rows)
    hourly_stats, session_stats = compute_spread_profile(df)

    assert not hourly_stats.empty
    assert not session_stats.empty
    assert "mean_spread" in hourly_stats.columns
    assert "p95_spread" in hourly_stats.columns
    assert "median_spread" in session_stats.columns
