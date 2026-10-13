"""Walk-Forward Tahlil Moduli.

Vaqt qatorlarini In-Sample (IS) va Out-of-Sample (OOS) oynalariga bo'lish va tahlil qilish.
Timeframe bo'yicha moslashtirilgan:
- H1 (~12.7 yil): Rolling/Anchored oynalar (IS: 2.0 yil, OOS: 0.5 yil).
- M15 (~4.2 yil): Rolling oynalar (IS: 1.0 yil, OOS: 3 oy).
- M5 (~1.4 yil): Tekshiruv oynalari (IS: 6 oy, OOS: 1 oy).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Dict, List
import pandas as pd
from loguru import logger

from python_brain.backtest.engine import BacktestEngine
from python_brain.backtest.metrics import calculate_metrics
from python_brain.backtest.strategy_base import Strategy


@dataclass
class WalkForwardWindow:
    window_id: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp
    is_bars: int
    oos_bars: int


@dataclass
class WindowResult:
    window: WalkForwardWindow
    is_metrics: Dict[str, Any]
    oos_metrics: Dict[str, Any]
    wfo_efficiency: float  # OOS Sharpe / IS Sharpe


class WalkForwardSplitter:
    """Datasetni rolling yoki anchored oynalarga bo'luvchi yordamchi sinf."""

    DEFAULT_CONFIGS = {
        "H1": {"is_days": 730, "oos_days": 180, "step_days": 180},
        "M15": {"is_days": 365, "oos_days": 90, "step_days": 90},
        "M5": {"is_days": 180, "oos_days": 30, "step_days": 30},
    }

    def __init__(
        self,
        timeframe: str = "H1",
        is_days: int | None = None,
        oos_days: int | None = None,
        step_days: int | None = None,
        anchored: bool = False,
    ) -> None:
        cfg = self.DEFAULT_CONFIGS.get(timeframe, self.DEFAULT_CONFIGS["H1"])
        self.timeframe = timeframe
        self.is_days = is_days or cfg["is_days"]
        self.oos_days = oos_days or cfg["oos_days"]
        self.step_days = step_days or cfg["step_days"]
        self.anchored = anchored

    def generate_windows(self, df: pd.DataFrame) -> List[WalkForwardWindow]:
        if df.empty:
            return []

        # Vaqt ustuni indeks yoki time_utc bo'lishi mumkin
        time_series = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df["time_utc"])
        start_time = time_series.iloc[0] if hasattr(time_series, "iloc") else time_series[0]
        end_time = time_series.iloc[-1] if hasattr(time_series, "iloc") else time_series[-1]
        windows: List[WalkForwardWindow] = []

        window_idx = 1
        current_is_start = start_time

        while True:
            current_is_end = current_is_start + timedelta(days=self.is_days)
            current_oos_start = current_is_end
            current_oos_end = current_oos_start + timedelta(days=self.oos_days)

            if current_oos_end > end_time:
                if (end_time - current_oos_start).days >= (self.oos_days // 2):
                    current_oos_end = end_time
                else:
                    break

            # Filterlash
            mask_is = (time_series >= current_is_start) & (time_series <= current_is_end)
            mask_oos = (time_series > current_oos_start) & (time_series <= current_oos_end)

            is_count = int(mask_is.sum())
            oos_count = int(mask_oos.sum())

            if is_count > 50 and oos_count > 20:
                windows.append(
                    WalkForwardWindow(
                        window_id=window_idx,
                        is_start=current_is_start,
                        is_end=current_is_end,
                        oos_start=current_oos_start,
                        oos_end=current_oos_end,
                        is_bars=is_count,
                        oos_bars=oos_count,
                    )
                )
                window_idx += 1

            if current_oos_end >= end_time:
                break

            if self.anchored:
                self.is_days += self.step_days
            else:
                current_is_start = current_is_start + timedelta(days=self.step_days)

        logger.info(
            f"WalkForwardSplitter ({self.timeframe}): {len(windows)} ta oyna yaratildi "
            f"(IS={self.is_days}d, OOS={self.oos_days}d, Anchored={self.anchored})"
        )
        return windows


class WalkForwardAnalyzer:
    def __init__(self, splitter: WalkForwardSplitter) -> None:
        self.splitter = splitter

    def run(
        self,
        df: pd.DataFrame,
        strategy_factory: Callable[[], Strategy],
        engine_factory: Callable[[], BacktestEngine],
    ) -> List[WindowResult]:
        windows = self.splitter.generate_windows(df)
        results: List[WindowResult] = []

        time_series = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df["time_utc"])

        for w in windows:
            mask_is = (time_series >= w.is_start) & (time_series <= w.is_end)
            mask_oos = (time_series > w.oos_start) & (time_series <= w.oos_end)

            is_df = df[mask_is].copy()
            oos_df = df[mask_oos].copy()

            # In-Sample
            strat_is = strategy_factory()
            engine_is = engine_factory()
            res_is = engine_is.run(is_df, strat_is)
            metrics_is = calculate_metrics(res_is)

            # Out-of-Sample
            strat_oos = strategy_factory()
            engine_oos = engine_factory()
            res_oos = engine_oos.run(oos_df, strat_oos)
            metrics_oos = calculate_metrics(res_oos)

            is_sharpe = metrics_is.get("sharpe_ratio", 0.0)
            oos_sharpe = metrics_oos.get("sharpe_ratio", 0.0)
            if abs(is_sharpe) > 1e-4:
                wfo_eff = oos_sharpe / is_sharpe
            else:
                wfo_eff = 1.0 if oos_sharpe >= 0 else 0.0

            results.append(
                WindowResult(
                    window=w,
                    is_metrics=metrics_is,
                    oos_metrics=metrics_oos,
                    wfo_efficiency=wfo_eff,
                )
            )

        return results
