"""3/10 Bosqich: Baseline Strategiyalarni H1 va M15 da sinash va hisobot generatsiya qilish.

Sinov stsenariylari:
1. MA Crossover (H1) - Zero Cost vs Real Cost
2. MA Crossover (M15) - Zero Cost vs Real Cost
3. Random Entry (H1) - Zero Cost vs Real Cost
4. Random Entry (M15) - Zero Cost vs Real Cost

Har biri bo'yicha:
- Faqat 80% Train/Dev ma'lumotlarida (Holdout qulflangan)
- Monte Carlo tahlili (1000 iteratsiya bootstrap, DD percentillar, ruin prob, cost stress)
- Walk-forward tahlili
- To'liq hisobotlar: reports/<run_id>/
"""

from __future__ import annotations

import sys
from pathlib import Path

# Loyiha ildizini PYTHONPATH ga qo'shish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
import pandas as pd

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
    """Solishtirish uchun nol friksiyali model."""
    def __init__(self):
        super().__init__(base_spread_points=0.0, commission_per_lot=0.0, swap_long_usd_per_lot=0.0, swap_short_usd_per_lot=0.0)

    def get_effective_spread(self, time_utc, bar_spread=None, is_news_blackout=False):
        return 0.0, 0.0

    def get_slippage_penalty(self, order_side, is_stop_order, spread_price, local_atr=1.0):
        return 0.0

    def calculate_swap(self, side, volume, rollover_time):
        return 0.0


def run_experiment(
    run_id: str,
    df: pd.DataFrame,
    strategy,
    use_costs: bool,
    timeframe: str,
    reporter: BacktestReporter,
    mc_engine: MonteCarloEngine,
) -> AccountState:
    logger.info(f"\n=======================================================")
    logger.info(f"Yugurish boshlandi: {run_id} (TF: {timeframe}, Xarajatlar: {use_costs})")
    logger.info(f"=======================================================")

    cost_model = CostModel() if use_costs else ZeroCostModel()
    risk_gate = DefaultRiskGate(risk_per_trade_pct=0.5, require_stop_loss=True)
    engine = BacktestEngine(initial_balance=10000.0)

    # Backtestni yurgizish
    account = engine.run(
        df=df,
        strategy=strategy,
        risk_gate=risk_gate,
        cost_model=cost_model,
        stress_multiplier=1.0,
    )

    metrics = calculate_metrics(account)
    logger.info(
        f"Natijalar: Net PnL=${metrics['net_profit']:,.2f} ({metrics['return_pct']:+.2f}%) | "
        f"Trades={metrics['total_trades']} | WR={metrics['winrate_pct']:.1f}% | "
        f"PF={metrics['profit_factor']:.2f} | Max DD={metrics['max_equity_drawdown_pct']:.2f}% | "
        f"Sharpe={metrics['sharpe_ratio']:.2f}"
    )

    # Monte Carlo tahlili
    mc_res = mc_engine.analyze(account.closed_positions, iterations=1000, random_seed=42)

    notes = (
        f"### Stsenariy Tahlili\n\n"
        f"- **Timeframe:** {timeframe}\n"
        f"- **Xarajatlar:** {'Real (Dynamic Spread + Slippage + Swap)' if use_costs else 'Zero Friction (Nazariy Ideal)'}\n"
        f"- **Holdout:** 20% qulfda (Faqat Train/Dev 80% ishlatildi)\n\n"
        f"### Monte Carlo Tahlili (1,000 iteratsiya bootstrap)\n\n"
        f"- **Median DD:** {mc_res.dd_p50:.2f}%\n"
        f"- **95% DD (Worst-case konfidensiya):** {mc_res.dd_p95:.2f}%\n"
        f"- **Eng yomon DD:** {mc_res.dd_worst:.2f}%\n"
        f"- **Ruin Ehtimoli (balans 50% ga tushish):** {mc_res.ruin_probability:.1f}%\n"
        f"- **1.0x Xarajatdagi Net PnL:** ${mc_res.cost_stress_1_0x:,.2f}\n"
        f"- **1.5x Xarajatdagi Net PnL:** ${mc_res.cost_stress_1_5x:,.2f}\n"
        f"- **2.0x Xarajatdagi Net PnL:** ${mc_res.cost_stress_2_0x:,.2f}\n"
        f"- **Top 10% yutuqlar olib tashlangandagi PnL:** ${mc_res.drop_10pct_wins_pnl:,.2f}\n"
    )

    reporter.generate_report(
        run_id=run_id,
        account=account,
        config={"run_id": run_id, "timeframe": timeframe, "use_costs": use_costs, "bars_count": len(df)},
        notes=notes,
    )

    return account


def main():
    downloader = HistoricalDataDownloader(symbol="XAUUSDm")
    holdout_mgr = HoldoutManager()
    reporter = BacktestReporter(output_root="reports")
    mc_engine = MonteCarloEngine(initial_balance=10000.0)

    # 1. H1 ma'lumotlarini yuklash
    logger.info("H1 ma'lumotlari yuklanmoqda...")
    df_h1 = downloader.load_timeframe_data("H1")
    train_h1, _ = holdout_mgr.split(df_h1, timeframe="H1", allow_holdout=False)

    # 2. M15 ma'lumotlarini yuklash
    logger.info("M15 ma'lumotlari yuklanmoqda...")
    df_m15 = downloader.load_timeframe_data("M15")
    train_m15, _ = holdout_mgr.split(df_m15, timeframe="M15", allow_holdout=False)

    # -------------------------------------------------------------
    # 1. MA CROSSOVER - H1 (Zero vs Real)
    # -------------------------------------------------------------
    strat_ma_h1_zero = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=3000.0, tp_points=6000.0)
    run_experiment("baseline_h1_ma_cross_zero_cost", train_h1, strat_ma_h1_zero, False, "H1", reporter, mc_engine)

    strat_ma_h1_real = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=3000.0, tp_points=6000.0)
    run_experiment("baseline_h1_ma_cross_real_cost", train_h1, strat_ma_h1_real, True, "H1", reporter, mc_engine)

    # -------------------------------------------------------------
    # 2. MA CROSSOVER - M15 (Zero vs Real)
    # -------------------------------------------------------------
    strat_ma_m15_zero = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=1500.0, tp_points=3000.0)
    run_experiment("baseline_m15_ma_cross_zero_cost", train_m15, strat_ma_m15_zero, False, "M15", reporter, mc_engine)

    strat_ma_m15_real = MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=1500.0, tp_points=3000.0)
    run_experiment("baseline_m15_ma_cross_real_cost", train_m15, strat_ma_m15_real, True, "M15", reporter, mc_engine)

    # -------------------------------------------------------------
    # 3. RANDOM ENTRY - H1 (Expectancy Drag Check)
    # -------------------------------------------------------------
    strat_rnd_h1_zero = RandomEntryStrategy(entry_probability=0.03, sl_points=3000.0, tp_points=3000.0, seed=42)
    run_experiment("baseline_h1_random_zero_cost", train_h1, strat_rnd_h1_zero, False, "H1", reporter, mc_engine)

    strat_rnd_h1_real = RandomEntryStrategy(entry_probability=0.03, sl_points=3000.0, tp_points=3000.0, seed=42)
    run_experiment("baseline_h1_random_real_cost", train_h1, strat_rnd_h1_real, True, "H1", reporter, mc_engine)

    # -------------------------------------------------------------
    # 4. WALK-FORWARD TAHLILI (H1 va M15)
    # -------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("WALK-FORWARD TAHLILI BOSHLANMOQDA...")
    logger.info("=======================================================")

    # H1 WFO
    wf_h1_splitter = WalkForwardSplitter(timeframe="H1", is_days=730, oos_days=180, step_days=180)
    wf_h1_analyzer = WalkForwardAnalyzer(wf_h1_splitter)

    wfo_h1_results = wf_h1_analyzer.run(
        train_h1,
        strategy_factory=lambda: MovingAverageCrossStrategy(fast_period=10, slow_period=30, sl_points=3000.0, tp_points=6000.0),
        engine_factory=lambda: BacktestEngine(initial_balance=10000.0),
    )

    logger.info(f"H1 WFO Yakunlandi: {len(wfo_h1_results)} ta oyna tekshirildi.")
    for res in wfo_h1_results[:5]:
        logger.info(
            f"  Oyna {res.window.window_id}: IS Sharpe={res.is_metrics['sharpe_ratio']:.2f} | "
            f"OOS Sharpe={res.oos_metrics['sharpe_ratio']:.2f} | WFO Eff={res.wfo_efficiency:.2f}"
        )

    logger.info("\nBarcha baseline sinovlar muvaffaqiyatli yakunlandi!")


if __name__ == "__main__":
    main()
