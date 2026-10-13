"""Realistic multi-factor execution cost model for XAUUSDm backtesting.

Integrates:
- Hourly / session spread profiles with multiple selectable regimes (A5):
  * "auto_bar_or_median" (DEFAULT - uses real bar spread if present, else hourly median / p95)
  * "profile_median"
  * "profile_stress_p95"
  * "profile_mean"
  * "profile_empirical_sample" (pseudo-random sampling with reproducible seed)
- Rollover widening (21:00 - 22:00 UTC) and economic news blackout expansion (p95 spread).
- Dynamic slippage model on stop orders (SL execution) based on spread and local ATR.
- Asymmetric overnight swap charges (Points / USD per lot) with explicit weekday config (A7).
- Configurable broker commission per lot.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd


class CostModel:
    """Manages transaction costs, variable spreads, slippage, and overnight swaps."""

    def __init__(
        self,
        base_spread_points: float = 240.0,
        stress_multiplier: float = 1.0,
        commission_per_lot: float = 0.0,
        swap_long_usd_per_lot: float = -52.33,
        swap_short_usd_per_lot: float = 0.0,
        triple_swap_weekday: int = 3,  # Python weekday: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        swap_charge_hour: int = 0,     # UTC hour when swap is rolled over (0 = 00:00 UTC)
        point: float = 0.001,
        contract_size: float = 100.0,
        spread_mode: str = "auto_bar_or_median",
        seed: Optional[int] = 42,
        hourly_profile_path: Optional[str] = "data/processed/hourly_spread_profile.parquet",
    ):
        self.base_spread_points = base_spread_points
        self.stress_multiplier = stress_multiplier
        self.commission_per_lot = commission_per_lot
        self.swap_long_usd_per_lot = swap_long_usd_per_lot
        self.swap_short_usd_per_lot = swap_short_usd_per_lot
        self.triple_swap_weekday = triple_swap_weekday
        self.swap_charge_hour = swap_charge_hour
        self.point = point
        self.contract_size = contract_size
        self.spread_mode = spread_mode
        self.rng = np.random.default_rng(seed)

        # Load hourly spread profile table if available
        self.hourly_profile: Dict[int, Dict[str, float]] = {}
        if hourly_profile_path and Path(hourly_profile_path).exists():
            df_prof = pd.read_parquet(hourly_profile_path)
            for _, row in df_prof.iterrows():
                h = int(row["utc_hour"])
                self.hourly_profile[h] = {
                    "median": float(row["median_spread"]),
                    "p95": float(row["p95_spread"]),
                    "mean": float(row["mean_spread"]),
                }

    def get_effective_spread(
        self,
        time_utc: datetime,
        bar_spread: Optional[float] = None,
        is_news_blackout: bool = False,
    ) -> Tuple[float, float]:
        """Returns (spread_points, spread_price_usd) for the given timestamp according to spread_mode."""
        hour = time_utc.hour
        is_rollover = hour in [21, 22]

        has_profile = hour in self.hourly_profile
        stats = self.hourly_profile.get(hour, {})

        if is_rollover or is_news_blackout:
            # Under extreme liquidity drought or high-impact news, unconditionally expand to p95
            raw_spread_pts = stats.get("p95", self.base_spread_points * 2.0)
        elif self.spread_mode == "auto_bar_or_median":
            # Priority: real broker spread captured on bar -> profile median -> baseline
            if bar_spread is not None and bar_spread > 0:
                raw_spread_pts = bar_spread
            elif has_profile:
                raw_spread_pts = stats["median"]
            else:
                raw_spread_pts = self.base_spread_points
        elif self.spread_mode == "profile_stress_p95":
            raw_spread_pts = stats.get("p95", self.base_spread_points * 2.0)
        elif self.spread_mode == "profile_mean":
            raw_spread_pts = stats.get("mean", self.base_spread_points)
        elif self.spread_mode == "profile_median":
            raw_spread_pts = stats.get("median", self.base_spread_points)
        elif self.spread_mode == "profile_empirical_sample":
            # Sample between median and p95 with lognormal / uniform shape
            med = stats.get("median", self.base_spread_points)
            p95 = stats.get("p95", self.base_spread_points * 1.5)
            # Uniform draw between median and p95 with occasional outlier
            raw_spread_pts = float(self.rng.uniform(med, p95))
        else:
            raw_spread_pts = bar_spread if (bar_spread and bar_spread > 0) else self.base_spread_points

        effective_pts = raw_spread_pts * self.stress_multiplier
        effective_price = effective_pts * self.point
        return effective_pts, effective_price

    def get_slippage_penalty(
        self,
        order_side: str,
        is_stop_order: bool,
        spread_price: float,
        local_atr: float = 1.0,
    ) -> float:
        """Calculate slippage penalty (in price points).
        
        Limit/TP orders execute conservatively at 0 adverse slippage.
        Stop orders (SL, Stop entries) suffer spread + ATR-dependent adverse slippage.
        """
        if not is_stop_order:
            return 0.0

        slippage_price = (0.20 * spread_price) + (0.05 * max(local_atr, 0.5))
        return slippage_price

    def calculate_commission(self, volume: float) -> float:
        """Calculate total roundturn commission in USD."""
        return self.commission_per_lot * volume

    def calculate_swap(
        self,
        side: str,
        volume: float,
        rollover_time: datetime,
    ) -> float:
        """Calculate overnight holding charge in USD for rolling past midnight UTC."""
        rate = self.swap_long_usd_per_lot if side == "BUY" else self.swap_short_usd_per_lot
        # Triple swap weekday check in Python datetime (0=Monday...3=Thursday)
        multiplier = 3.0 if rollover_time.weekday() == self.triple_swap_weekday else 1.0
        return rate * volume * multiplier
