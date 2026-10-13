"""Qayta ko'rib chiqilgan Baseline Backtest va Sanity Check skripti (A10, A11).

Vazifalar:
1. halt_on_kill_switch=False rejimida to'liq Train davrini (Holdout qulfda) o'lchash.
2. MA Crossover: H1 va M15 da Zero-Cost va Real-Cost (bir xil signallarda, savdolar soni taqqoslanadi).
3. Ambiguous-bar tahlili: Har bir timeframe (H1, M15, M5) da bar ichida SL va TP birga tegishi foizi.
4. Random Entry: 30 xil seed bilan (seed=1..30) yurgizish:
   - Zero-cost: o'rtacha expectancy va 95% ishonch intervali (nolni o'z ichiga olishi shart).
   - Real-cost: o'rtacha expectancy manfiy va friksiyaga (spread+slippage) mosligi (±30%).
5. M5 da tekshiruv (mavjud train davrida).
6. Walk-Forward jadvali (har bir oyna bo'yicha IS va OOS metrikalari).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# Loyiha ildizini PYTHONPATH ga qo'shish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from loguru import logger

from python_brain.data.downloader import HistoricalDataDownloader
from python_brain.backtest.costs import CostModel
from python_brain.backtest.engine import BacktestEngine
from python_brain.backtest.holdout import HoldoutManager
from python_brain.backtest.metrics import calculate_metrics
from python_brain.backtest.models import AccountState
from python_brain.backtest.montecarlo import MonteCarloEngine
from python_brain.backtest.reporter import BacktestReporter
from python_brain.backtest.risk_gate import DefaultRiskGate
from python_brain.backtest.strategy_base import MovingAverageCrossStrategy, RandomEntryStrategy
from python_brain.backtest.walkforward import WalkForwardAnalyzer, WalkForwardSplitter


class ZeroCostModel(CostModel):
    def __init__(self):
        super().__init__(base_spread_points=0.0, commission_per_lot=0.0, swap_long_usd_per_lot=0.0, swap_short_usd_per_lot=0.0)

    def get_effective_spread(self, time_utc, bar_spread=None, is_news_blackout=False):
        return 0.0, 0.0

    def get_slippage_penalty(self, order_side, is_stop_order, spread_price, local_atr=1.0):
        return 0.0

    def calculate_swap(self, side, volume, rollover_time):
        return 0.0


def calculate_ambiguous_bars(df: pd.DataFrame, sl_points: float, tp_points: float, point: float = 0.001) -> Dict[str, Any]:
    """Bitta bar ichida ham SL, ham TP diapazoni qamrab olingan (ambiguous) barlar foizini o'lchash."""
    total_bars = len(df)
    if total_bars == 0:
        return {"total_bars": 0, "ambiguous_bars": 0, "ambiguous_pct": 0.0}

    # Range of the bar = High - Low
    # If Bar High - Low >= (sl_points + tp_points) * point, or even just max(sl, tp) * point
    # Conservative threshold: Bar Range >= (SL distance + TP distance)
    required_range = (sl_points + tp_points) * point
    ranges = df["high"] - df["low"]
    ambiguous_count = int((ranges >= required_range).sum())
    ambiguous_pct = (ambiguous_count / total_bars) * 100.0

    return {
        "total_bars": total_bars,
        "ambiguous_bars": ambiguous_count,
        "ambiguous_pct": round(ambiguous_pct, 4),
        "required_range_usd": round(required_range, 2),
    }


def run_random_entry_battery(
    df: pd.DataFrame,
    num_seeds: int = 30,
    sl_points: float = 3000.0,
    tp_points: float = 3000.0,
    entry_prob: float = 0.02,
) -> Dict[str, Any]:
    """Random entry strategiyasini kamida 30 xil seed bilan yurgizish (Zero vs Real cost)."""
    logger.info(f"Random Entry Battery boshlandi ({num_seeds} seeds)...")

    zero_expectancies = []
    real_expectancies = []
    spread_slippage_costs = []

    for seed in range(1, num_seeds + 1):
        strat_zero = RandomEntryStrategy(entry_probability=entry_prob, sl_points=sl_points, tp_points=tp_points, seed=seed)
        gate_zero = DefaultRiskGate(risk_per_trade_pct=0.5, halt_on_kill_switch=False)
        engine_zero = BacktestEngine()
        acc_zero = engine_zero.run(df, strat_zero, risk_gate=gate_zero, cost_model=ZeroCostModel())
        m_zero = calculate_metrics(acc_zero)
        zero_expectancies.append(m_zero["expectancy_usd"])

        strat_real = RandomEntryStrategy(entry_probability=entry_prob, sl_points=sl_points, tp_points=tp_points, seed=seed)
        gate_real = DefaultRiskGate(risk_per_trade_pct=0.5, halt_on_kill_switch=False)
        engine_real = BacktestEngine()
        acc_real = engine_real.run(df, strat_real, risk_gate=gate_real, cost_model=CostModel())
        m_real = calculate_metrics(acc_real)
        real_expectancies.append(m_real["expectancy_usd"])

        # Har bir savdoga to'g'ri kelgan o'rtacha spread + slippage xarajati
        trades_count = max(1, m_real["total_trades"])
        per_trade_friction = (m_real["total_spread_cost"] + m_real.get("total_commission", 0.0)) / trades_count
        spread_slippage_costs.append(per_trade_friction)

    zero_arr = np.array(zero_expectancies)
    real_arr = np.array(real_expectancies)

    zero_mean = float(np.mean(zero_arr))
    zero_sem = float(np.std(zero_arr, ddof=1) / np.sqrt(num_seeds))
    zero_ci_95 = (zero_mean - 1.96 * zero_sem, zero_mean + 1.96 * zero_sem)

    real_mean = float(np.mean(real_arr))
    real_sem = float(np.std(real_arr, ddof=1) / np.sqrt(num_seeds))
    real_ci_95 = (real_mean - 1.96 * real_sem, real_mean + 1.96 * real_sem)

    avg_expected_friction = float(np.mean(spread_slippage_costs))

    return {
        "num_seeds": num_seeds,
        "zero_cost_mean_expectancy": round(zero_mean, 2),
        "zero_cost_ci_95": (round(zero_ci_95[0], 2), round(zero_ci_95[1], 2)),
        "zero_includes_zero": (zero_ci_95[0] <= 0.0 <= zero_ci_95[1]),
        "real_cost_mean_expectancy": round(real_mean, 2),
        "real_cost_ci_95": (round(real_ci_95[0], 2), round(real_ci_95[1], 2)),
        "avg_friction_per_trade": round(avg_expected_friction, 2),
    }


def main():
    downloader = HistoricalDataDownloader(symbol="XAUUSDm")
    holdout_mgr = HoldoutManager()
    reporter = BacktestReporter(output_root="reports")
    mc_engine = MonteCarloEngine(initial_balance=10000.0)

    # 1. H1 ma'lumotlari
    logger.info("H1 ma'lumotlari yuklanmoqda...")
    df_h1 = downloader.load_timeframe_data("H1")
    train_h1, _ = holdout_mgr.split(df_h1, timeframe="H1", allow_holdout=False)

    # 2. M15 ma'lumotlari
    logger.info("M15 ma'lumotlari yuklanmoqda...")
    df_m15 = downloader.load_timeframe_data("M15")
    train_m15, _ = holdout_mgr.split(df_m15, timeframe="M15", allow_holdout=False)

    # 3. M5 ma'lumotlari
    logger.info("M5 ma'lumotlari yuklanmoqda...")
    df_m5 = downloader.load_timeframe_data("M5")
    train_m5, _ = holdout_mgr.split(df_m5, timeframe="M5", allow_holdout=False)

    # -------------------------------------------------------------
    # Ambiguous Bars tekshiruvi (H1, M15, M5)
    # -------------------------------------------------------------
    amb_h1 = calculate_ambiguous_bars(train_h1, sl_points=3000.0, tp_points=6000.0) # $3 SL, $6 TP
    amb_m15 = calculate_ambiguous_bars(train_m15, sl_points=1500.0, tp_points=3000.0) # $1.5 SL, $3 TP
    amb_m5 = calculate_ambiguous_bars(train_m5, sl_points=1000.0, tp_points=2000.0) # $1.0 SL, $2 TP

    logger.info(f"Ambiguous Bars H1: {amb_h1['ambiguous_bars']} / {amb_h1['total_bars']} ({amb_h1['ambiguous_pct']}%)")
    logger.info(f"Ambiguous Bars M15: {amb_m15['ambiguous_bars']} / {amb_m15['total_bars']} ({amb_m15['ambiguous_pct']}%)")
    logger.info(f"Ambiguous Bars M5: {amb_m5['ambiguous_bars']} / {amb_m5['total_bars']} ({amb_m5['ambiguous_pct']}%)")

    # -------------------------------------------------------------
    # MA Crossover Backtest (halt_on_kill_switch=False)
    # -------------------------------------------------------------
    def run_clean_backtest(run_id: str, df: pd.DataFrame, strat, use_cost: bool, tf: str):
        cost_m = CostModel() if use_cost else ZeroCostModel()
        gate = DefaultRiskGate(risk_per_trade_pct=0.5, halt_on_kill_switch=False)
        engine = BacktestEngine(initial_balance=10000.0)
        acc = engine.run(df, strat, risk_gate=gate, cost_model=cost_m)
        m = calculate_metrics(acc)
        mc_res = mc_engine.analyze(acc.closed_positions, iterations=1000)

        ks_trigger_str = acc.kill_switch_triggered_at.strftime("%Y-%m-%d %H:%M") if acc.kill_switch_triggered_at else "Triggered emas"

        notes = (
            f"- **Timeframe:** {tf}\n"
            f"- **Friksiya:** {'Real Cost Model' if use_cost else 'Zero Cost Model'}\n"
            f"- **Kill-Switch Holati:** {ks_trigger_str}\n"
            f"- **Monte Carlo Median DD:** {mc_res.dd_p50:.2f}%, 95% DD: {mc_res.dd_p95:.2f}%\n"
        )
        reporter.generate_report(run_id, acc, config={"timeframe": tf, "use_cost": use_cost}, notes=notes)
        return m, acc

    logger.info("H1 MA Cross (Zero vs Real) o'tkazilmoqda...")
    strat_h1_zero = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=3000.0, tp_points=6000.0)
    m_h1_zero, acc_h1_zero = run_clean_backtest("baseline_h1_ma_cross_zero_cost", train_h1, strat_h1_zero, False, "H1")

    strat_h1_real = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=3000.0, tp_points=6000.0)
    m_h1_real, acc_h1_real = run_clean_backtest("baseline_h1_ma_cross_real_cost", train_h1, strat_h1_real, True, "H1")

    logger.info(f"H1 Zero: Trades={m_h1_zero['total_trades']}, Net=${m_h1_zero['net_profit']:,.2f}, MaxDD={m_h1_zero['max_equity_drawdown_pct']:.2f}%")
    logger.info(f"H1 Real: Trades={m_h1_real['total_trades']}, Net=${m_h1_real['net_profit']:,.2f}, MaxDD={m_h1_real['max_equity_drawdown_pct']:.2f}%, KS Trigger={acc_h1_real.kill_switch_triggered_at}")

    logger.info("M15 MA Cross (Zero vs Real) o'tkazilmoqda...")
    strat_m15_zero = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=1500.0, tp_points=3000.0)
    m_m15_zero, acc_m15_zero = run_clean_backtest("baseline_m15_ma_cross_zero_cost", train_m15, strat_m15_zero, False, "M15")

    strat_m15_real = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=1500.0, tp_points=3000.0)
    m_m15_real, acc_m15_real = run_clean_backtest("baseline_m15_ma_cross_real_cost", train_m15, strat_m15_real, True, "M15")

    logger.info(f"M15 Zero: Trades={m_m15_zero['total_trades']}, Net=${m_m15_zero['net_profit']:,.2f}, MaxDD={m_m15_zero['max_equity_drawdown_pct']:.2f}%")
    logger.info(f"M15 Real: Trades={m_m15_real['total_trades']}, Net=${m_m15_real['net_profit']:,.2f}, MaxDD={m_m15_real['max_equity_drawdown_pct']:.2f}%, KS Trigger={acc_m15_real.kill_switch_triggered_at}")

    # M5 tekshiruv
    logger.info("M5 MA Cross tekshiruv...")
    strat_m5_real = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=1000.0, tp_points=2000.0)
    m_m5_real, acc_m5_real = run_clean_backtest("baseline_m5_ma_cross_real_cost", train_m5, strat_m5_real, True, "M5")
    logger.info(f"M5 Real: Trades={m_m5_real['total_trades']}, Net=${m_m5_real['net_profit']:,.2f}, MaxDD={m_m5_real['max_equity_drawdown_pct']:.2f}%")

    # -------------------------------------------------------------
    # Random Entry Battery (30 Seeds)
    # Ambiguous-bar intrabar asimmetriyasidan holi bo'lishi uchun SL/TP = 12,000 pts ($12.00)
    # -------------------------------------------------------------
    rnd_res = run_random_entry_battery(
        train_h1.iloc[-4000:],
        num_seeds=30,
        sl_points=12000.0,
        tp_points=12000.0,
        entry_prob=0.03,
    )
    logger.info(f"Random Entry Battery (30 Seeds) Natijalari:\n{rnd_res}")

    # -------------------------------------------------------------
    # Walk-Forward Tahlili Jadvali (A11)
    # -------------------------------------------------------------
    logger.info("Walk-Forward tahlili boshlanmoqda...")
    wf_splitter = WalkForwardSplitter(timeframe="H1", is_days=730, oos_days=180, step_days=180)
    wf_analyzer = WalkForwardAnalyzer(wf_splitter)
    wfo_results = wf_analyzer.run(
        train_h1,
        strategy_factory=lambda: MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=3000.0, tp_points=6000.0),
        engine_factory=lambda: BacktestEngine(initial_balance=10000.0),
    )

    wfo_table_rows = []
    for r in wfo_results:
        wfo_table_rows.append({
            "window_id": r.window.window_id,
            "is_start": r.window.is_start.strftime("%Y-%m-%d"),
            "is_end": r.window.is_end.strftime("%Y-%m-%d"),
            "oos_start": r.window.oos_start.strftime("%Y-%m-%d"),
            "oos_end": r.window.oos_end.strftime("%Y-%m-%d"),
            "is_trades": r.is_metrics["total_trades"],
            "is_sharpe": r.is_metrics["sharpe_ratio"],
            "is_net_pnl": r.is_metrics["net_profit"],
            "oos_trades": r.oos_metrics["total_trades"],
            "oos_sharpe": r.oos_metrics["sharpe_ratio"],
            "oos_net_pnl": r.oos_metrics["net_profit"],
            "wfo_efficiency": round(r.wfo_efficiency, 2),
        })

    wfo_df = pd.DataFrame(wfo_table_rows)
    wfo_csv_path = Path("reports/wfo_h1_table.csv")
    wfo_df.to_csv(wfo_csv_path, index=False)
    logger.info(f"Walk-Forward jadvali saqlandi: {wfo_csv_path} ({len(wfo_df)} oynalar)")

    # Xulosa faylini shakllantirish
    summary_path = Path("reports/baseline_sanity_summary.json")
    import json
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "ambiguous_bars": {
                "H1": amb_h1,
                "M15": amb_m15,
                "M5": amb_m5,
            },
            "random_entry_battery": rnd_res,
            "ma_crossover_h1": {
                "zero_cost": m_h1_zero,
                "real_cost": m_h1_real,
                "kill_switch_triggered_at": str(acc_h1_real.kill_switch_triggered_at),
            },
            "ma_crossover_m15": {
                "zero_cost": m_m15_zero,
                "real_cost": m_m15_real,
                "kill_switch_triggered_at": str(acc_m15_real.kill_switch_triggered_at),
            },
            "ma_crossover_m5": {
                "real_cost": m_m5_real,
                "kill_switch_triggered_at": str(acc_m5_real.kill_switch_triggered_at),
            },
        }, f, indent=2, default=str)

    logger.info(f"Barcha baseline va sanity hisobotlari saqlandi: {summary_path}")


if __name__ == "__main__":
    main()
