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
    best_params: Dict[str, Any] | None = None


@dataclass
class WalkForwardAnalysisResult:
    window_results: List[WindowResult]
    combined_oos_metrics: Dict[str, Any]
    profitable_windows_pct: float
    total_oos_trades: int
    combined_oos_pf: float
    combined_oos_sharpe: float
    combined_oos_max_dd: float


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
        strategy_factory: Callable[..., Strategy],
        engine_factory: Callable[[], BacktestEngine],
        param_grid: List[Dict[str, Any]] | None = None,
    ) -> WalkForwardAnalysisResult:
        windows = self.splitter.generate_windows(df)
        results: List[WindowResult] = []

        time_series = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df["time_utc"])
        all_oos_positions = []

        for w in windows:
            mask_is = (time_series >= w.is_start) & (time_series <= w.is_end)
            mask_oos = (time_series > w.oos_start) & (time_series <= w.oos_end)

            is_df = df[mask_is].copy()
            oos_df = df[mask_oos].copy()

            # Nested In-Sample Parameter Selection (R2-4)
            best_p = None
            best_is_metric = -999999.0
            best_is_acc = None
            best_is_metrics = {}

            if param_grid and len(param_grid) > 0:
                for p in param_grid:
                    eng = engine_factory()
                    strat = strategy_factory(**p)
                    acc = eng.run(is_df, strat)
                    m = calculate_metrics(acc)
                    # IS saralash mezoni: Profit Factor (agar trades >= 10 bo'lsa)
                    score = m.get("profit_factor", 0.0) if m.get("total_trades", 0) >= 10 else 0.0
                    if score > best_is_metric:
                        best_is_metric = score
                        best_p = p
                        best_is_acc = acc
                        best_is_metrics = m
            else:
                best_p = {}
                eng = engine_factory()
                strat = strategy_factory()
                best_is_acc = eng.run(is_df, strat)
                best_is_metrics = calculate_metrics(best_is_acc)

            # Out-of-Sample evaluation using best parameter from IS
            eng_oos = engine_factory()
            strat_oos = strategy_factory(**best_p) if best_p else strategy_factory()
            res_oos = eng_oos.run(oos_df, strat_oos)
            metrics_oos = calculate_metrics(res_oos)

            # Accumulate OOS closed trades
            all_oos_positions.extend(res_oos.closed_positions)

            is_sharpe = best_is_metrics.get("sharpe_ratio", 0.0)
            oos_sharpe = metrics_oos.get("sharpe_ratio", 0.0)
            if abs(is_sharpe) > 1e-4:
                wfo_eff = oos_sharpe / is_sharpe
            else:
                wfo_eff = 1.0 if oos_sharpe >= 0 else 0.0

            results.append(
                WindowResult(
                    window=w,
                    is_metrics=best_is_metrics,
                    oos_metrics=metrics_oos,
                    wfo_efficiency=wfo_eff,
                    best_params=best_p,
                )
            )

        # R2-4: Concatenate ALL OOS trades into single master account for holistic metrics
        init_bal = 10000.0
        combined_acc = BacktestEngine(initial_balance=init_bal).run(
            df.iloc[:2], strategy_factory(**(param_grid[0] if param_grid else {}))
        )
        combined_acc.closed_positions = all_oos_positions
        combined_acc.balance = init_bal + sum(p.realized_pnl for p in all_oos_positions)
        combined_acc.equity = combined_acc.balance

        # Calculate peak-to-trough on merged OOS curve
        running_bal = init_bal
        peak_bal = init_bal
        max_dd = 0.0
        for p in all_oos_positions:
            running_bal += p.realized_pnl
            if running_bal > peak_bal:
                peak_bal = running_bal
            dd = (peak_bal - running_bal) / peak_bal * 100.0
            if dd > max_dd:
                max_dd = dd
        combined_acc.max_equity_drawdown_pct = max_dd
        combined_acc.max_balance_drawdown_pct = max_dd

        combined_metrics = calculate_metrics(combined_acc)

        # Profitable windows ratio
        profitable_count = sum(1 for r in results if r.oos_metrics.get("net_profit", 0.0) > 0)
        prof_pct = (profitable_count / len(results) * 100.0) if results else 0.0

        return WalkForwardAnalysisResult(
            window_results=results,
            combined_oos_metrics=combined_metrics,
            profitable_windows_pct=round(prof_pct, 2),
            total_oos_trades=len(all_oos_positions),
            combined_oos_pf=combined_metrics.get("profit_factor", 0.0),
            combined_oos_sharpe=combined_metrics.get("sharpe_ratio", 0.0),
            combined_oos_max_dd=round(max_dd, 2),
        )
