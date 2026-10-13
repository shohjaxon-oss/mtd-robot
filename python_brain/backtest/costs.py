"""Realistic multi-factor execution cost model for XAUUSDm backtesting.

Integrates:
- Hourly / session spread profiles with stress multipliers (1.0x, 1.5x, 2.0x).
- Rollover widening (21:00 - 22:00 UTC) and economic news blackout expansion (p95 spread).
- Dynamic slippage model on stop orders (SL execution) based on spread and local ATR.
- Asymmetric overnight swap charges (Points / USD per lot) with 3x rollover day logic.
- Configurable broker commission per lot.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
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
        triple_swap_weekday: int = 3,  # 3 = Thursday (0=Mon...3=Thu)
        point: float = 0.001,
        contract_size: float = 100.0,
        hourly_profile_path: Optional[str] = "data/processed/hourly_spread_profile.parquet",
    ):
        self.base_spread_points = base_spread_points
        self.stress_multiplier = stress_multiplier
        self.commission_per_lot = commission_per_lot
        self.swap_long_usd_per_lot = swap_long_usd_per_lot
        self.swap_short_usd_per_lot = swap_short_usd_per_lot
        self.triple_swap_weekday = triple_swap_weekday
        self.point = point
        self.contract_size = contract_size

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
        """Returns (spread_points, spread_price_usd) for the given timestamp."""
        hour = time_utc.hour
        is_rollover = hour in [21, 22]

        # Use profile if available, else bar spread or baseline
        if hour in self.hourly_profile:
            stats = self.hourly_profile[hour]
            if is_rollover or is_news_blackout:
                raw_spread_pts = stats["p95"]
            else:
                raw_spread_pts = stats["median"]
        elif bar_spread is not None and bar_spread > 0:
            raw_spread_pts = bar_spread
        else:
            raw_spread_pts = self.base_spread_points

        # Apply stress multiplier
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
        
        Limit/TP orders typically experience 0 or favorable slippage (modeled conservatively as 0).
        Stop orders (Stop Loss / Stop Entry) experience adverse slippage proportional to spread & ATR.
        """
        if not is_stop_order:
            return 0.0

        # Conservative quantitative slippage model:
        # Base penalty: 20% of spread + 5% of local bar ATR
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
        multiplier = 3.0 if rollover_time.weekday() == self.triple_swap_weekday else 1.0
        return rate * volume * multiplier
