"""Data quality assurance and validation module for OHLC historical candles.

Strictly checks for:
- Duplicate timestamps
- Non-monotonic / unordered timestamps
- Unexpected intra-week gaps (excluding standard weekend closes)
- Zero or negative prices
- Broken OHLC logic (high < low, high < open/close, low > open/close)
- Price spikes exceeding N x ATR
- Zero tick volume bars
- Negative or extreme spread anomalies

Zero-illusion rule: Never silently mutate or discard data. All anomalies are logged and reported.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


@dataclass
class QualityReport:
    timeframe: str
    total_bars: int
    start_time: str
    end_time: str
    duplicate_count: int
    unordered_count: int
    unexpected_gap_count: int
    invalid_price_count: int
    invalid_ohlc_count: int
    spike_count: int
    zero_volume_count: int
    spread_anomaly_count: int
    is_clean: bool
    summary_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataQualityAuditor:
    """Performs comprehensive quantitative integrity audits on price bar DataFrames."""

    EXPECTED_DELTA_MINUTES = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
    }

    def __init__(self, spike_atr_multiplier: float = 6.0, max_spread_points: float = 800.0):
        self.spike_atr_multiplier = spike_atr_multiplier
        self.max_spread_points = max_spread_points

    def audit(self, df: pd.DataFrame, timeframe: str = "M5") -> QualityReport:
        """Run full battery of quality checks on candle DataFrame."""
        if df.empty:
            return QualityReport(
                timeframe=timeframe,
                total_bars=0,
                start_time="N/A",
                end_time="N/A",
                duplicate_count=0,
                unordered_count=0,
                unexpected_gap_count=0,
                invalid_price_count=0,
                invalid_ohlc_count=0,
                spike_count=0,
                zero_volume_count=0,
                spread_anomaly_count=0,
                is_clean=True,
                summary_notes=["DataFrame is empty."],
            )

        data = df.copy()
        data["time_utc"] = pd.to_datetime(data["time_utc"])
        total_bars = len(data)
        notes = []

        # 1. Duplicates
        duplicate_mask = data.duplicated(subset=["time_utc"])
        duplicate_count = int(duplicate_mask.sum())
        if duplicate_count > 0:
            notes.append(f"Found {duplicate_count} duplicate timestamps.")

        # 2. Monotonicity (Unordered)
        diff_seconds = data["time_utc"].diff().dt.total_seconds()
        unordered_count = int((diff_seconds < 0).sum())
        if unordered_count > 0:
            notes.append(f"Found {unordered_count} non-chronological bar sequences.")

        # 3. Invalid Price Checks (Zero or Negative)
        price_cols = ["open", "high", "low", "close"]
        invalid_prices = (data[price_cols] <= 0).any(axis=1)
        invalid_price_count = int(invalid_prices.sum())
        if invalid_price_count > 0:
            notes.append(f"Found {invalid_price_count} bars with non-positive price values.")

        # 4. OHLC Logical Integrity
        # High must be >= Open, Close, Low
        # Low must be <= Open, Close, High
        broken_high = (data["high"] < data["low"]) | (data["high"] < data["open"]) | (data["high"] < data["close"])
        broken_low = (data["low"] > data["open"]) | (data["low"] > data["close"])
        invalid_ohlc_mask = broken_high | broken_low
        invalid_ohlc_count = int(invalid_ohlc_mask.sum())
        if invalid_ohlc_count > 0:
            notes.append(f"Found {invalid_ohlc_count} bars violating basic OHLC geometric logic.")

        # 5. Unexpected Intra-week Gaps
        expected_step_m = self.EXPECTED_DELTA_MINUTES.get(timeframe, 5)
        diff_minutes = diff_seconds / 60.0

        # Weekend gap definition: gap spans between Friday 20:00+ and Sunday 21:00+ UTC
        # If gap is larger than 2x expected step, check if it's weekend
        gap_mask = diff_minutes > (expected_step_m * 1.5)
        unexpected_gaps = 0

        if gap_mask.any():
            gap_indices = np.where(gap_mask)[0]
            for idx in gap_indices:
                prev_time = data["time_utc"].iloc[idx - 1]
                curr_time = data["time_utc"].iloc[idx]

                # If prev_time is Friday and curr_time is Sunday/Monday, it's legitimate market close
                is_weekend = (prev_time.weekday() == 4 and curr_time.weekday() in [6, 0]) or (
                    prev_time.weekday() == 6 and curr_time.weekday() == 0
                )
                # Daily maintenance break (around 21:00 - 22:00 or 23:00 - 00:00 UTC) ~ 60 mins
                is_daily_break = (
                    (curr_time - prev_time).total_seconds() <= 7200
                    and (prev_time.hour in [20, 21, 22, 23])
                )

                if not (is_weekend or is_daily_break):
                    unexpected_gaps += 1

        if unexpected_gaps > 0:
            notes.append(f"Found {unexpected_gaps} unexpected intra-week data gaps.")

        # 6. Anomalous Price Spikes (> N x ATR)
        tr = np.maximum(
            data["high"] - data["low"],
            np.maximum(
                np.abs(data["high"] - data["close"].shift(1).fillna(data["open"])),
                np.abs(data["low"] - data["close"].shift(1).fillna(data["open"])),
            ),
        )
        atr_14 = tr.rolling(14, min_periods=1).mean()
        bar_range = data["high"] - data["low"]
        spike_mask = bar_range > (self.spike_atr_multiplier * atr_14)
        spike_count = int(spike_mask.sum())
        if spike_count > 0:
            notes.append(f"Found {spike_count} extreme price spikes exceeding {self.spike_atr_multiplier}x ATR.")

        # 7. Zero Volume Bars
        zero_vol_mask = data["tick_volume"] <= 0
        zero_volume_count = int(zero_vol_mask.sum())
        if zero_volume_count > 0:
            notes.append(f"Found {zero_volume_count} bars with zero tick volume.")

        # 8. Spread Anomalies (Negative or Extreme)
        if "spread" in data.columns:
            spread_mask = (data["spread"] < 0) | (data["spread"] > self.max_spread_points)
            spread_anomaly_count = int(spread_mask.sum())
            if spread_anomaly_count > 0:
                notes.append(f"Found {spread_anomaly_count} bars with spread anomalies (< 0 or > {self.max_spread_points} pts).")
        else:
            spread_anomaly_count = 0

        is_clean = (
            duplicate_count == 0
            and unordered_count == 0
            and invalid_price_count == 0
            and invalid_ohlc_count == 0
            and unexpected_gaps == 0
        )

        if is_clean:
            notes.append("Passed all structural and logical integrity checks cleanly.")

        return QualityReport(
            timeframe=timeframe,
            total_bars=total_bars,
            start_time=data["time_utc"].min().strftime("%Y-%m-%d %H:%M:%S UTC"),
            end_time=data["time_utc"].max().strftime("%Y-%m-%d %H:%M:%S UTC"),
            duplicate_count=duplicate_count,
            unordered_count=unordered_count,
            unexpected_gap_count=unexpected_gaps,
            invalid_price_count=invalid_price_count,
            invalid_ohlc_count=invalid_ohlc_count,
            spike_count=spike_count,
            zero_volume_count=zero_volume_count,
            spread_anomaly_count=spread_anomaly_count,
            is_clean=is_clean,
            summary_notes=notes,
        )
