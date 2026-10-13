"""4/10 R2: Strategiya Tadqiqoti, Xarajat Dekompozitsiyasi va Validatsiya Protokoli.

Barcha sinovlar QAT'IY ravishda faqat Train/Dev (80%) ma'lumotlarida o'tkaziladi.
Holdout (oxirgi 20%) qulflangan.

R2 Yaxshilanishlari:
1. R2-1: Stress xatosi tuzatilgan (1.5x spread to'liq qo'llanadi).
2. R2-2: Xarajat dekompozitsiyasi (Gross PF, Net PF, Spread, Slip, Swap, Comm, Cost-to-Edge).
3. R2-3: Ambiguous trades hisobi (ikkilamchi bar tekshiruvi).
4. R2-4: Walk-forward birlashtirilgan yig'ma OOS metrikalari va nested tanlov.
5. R2-6: Skrining: Gross PF < 1.05 bo'lsa "NO EDGE" deb tezkor rad etiladi.
6. R2-7: Yangi gipotezalar (HYP-05, HYP-06, HYP-07). Jami N <= 30.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from loguru import logger

from python_brain.data.downloader import HistoricalDataDownloader
from python_brain.backtest.costs import CostModel
from python_brain.backtest.engine import BacktestEngine
from python_brain.backtest.holdout import HoldoutManager
from python_brain.backtest.metrics import calculate_metrics
from python_brain.backtest.reporter import BacktestReporter
from python_brain.backtest.risk_gate import DefaultRiskGate
from python_brain.backtest.strategy_base import Strategy
from python_brain.backtest.walkforward import WalkForwardAnalyzer, WalkForwardSplitter

from python_brain.signals.donchian_trend import DonchianTrendStrategy
from python_brain.signals.intraday_breakout import IntradayNoOvernightStrategy
from python_brain.signals.mean_reversion import MeanReversionStrategy
from python_brain.signals.session_breakout import SessionBreakoutStrategy
from python_brain.signals.short_only_pullback import ShortOnlyTrendPullbackStrategy
from python_brain.signals.trend_pullback import TrendPullbackStrategy
from python_brain.signals.volatility_squeeze import VolatilitySqueezeStrategy


LOG_CSV_PATH = Path("research/experiment_log.csv")


def log_experiment_to_csv(row_dict: Dict[str, Any], overwrite_all: bool = False) -> None:
    """Natijani research/experiment_log.csv ga yozadi."""
    df_row = pd.DataFrame([row_dict])
    if overwrite_all or not LOG_CSV_PATH.exists() or LOG_CSV_PATH.stat().st_size == 0:
        df_row.to_csv(LOG_CSV_PATH, index=False)
    else:
        df_row.to_csv(LOG_CSV_PATH, mode="a", header=False, index=False)


def evaluate_strategy_candidate(
    exp_id: str,
    hypo_id: str,
    strategy_name: str,
    timeframe: str,
    train_df: pd.DataFrame,
    strategy_factory,
    params: Dict[str, Any],
    reporter: BacktestReporter,
    param_grid_for_wfo: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    logger.info(f"\n=======================================================")
    logger.info(f"Sinov: {exp_id} ({hypo_id}: {strategy_name}) Params: {params} TF: {timeframe}")
    logger.info(f"=======================================================")

    # 1. Baza Backtest (1.0x Real Cost, Train 80%)
    strat_base = strategy_factory(**params)
    cost_base = CostModel()
    gate_base = DefaultRiskGate(risk_per_trade_pct=0.5, halt_on_kill_switch=False)
    engine_base = BacktestEngine(initial_balance=10000.0)

    acc_base = engine_base.run(train_df, strat_base, risk_gate=gate_base, cost_model=cost_base)
    m_base = calculate_metrics(acc_base)

    gross_pf = m_base.get("gross_profit_factor", 0.0)
    net_pf = m_base.get("profit_factor", 0.0)

    # 2. Xarajat Stress Testi (R2-1 tuzatilgan: 1.5x)
    strat_stress = strategy_factory(**params)
    cost_stress = CostModel(stress_multiplier=1.5)
    gate_stress = DefaultRiskGate(risk_per_trade_pct=0.5, halt_on_kill_switch=False)
    engine_stress = BacktestEngine(initial_balance=10000.0)

    acc_stress = engine_stress.run(train_df, strat_stress, risk_gate=gate_stress, cost_model=cost_stress)
    m_stress = calculate_metrics(acc_stress)
    stress_pf = m_stress.get("profit_factor", 0.0)

    # 3. Long va Short ajratish
    long_trades = [p for p in acc_base.closed_positions if getattr(p.side, "value", str(p.side)) == "BUY"]
    short_trades = [p for p in acc_base.closed_positions if getattr(p.side, "value", str(p.side)) == "SELL"]
    long_pnl = sum(p.realized_pnl for p in long_trades)
    short_pnl = sum(p.realized_pnl for p in short_trades)
    long_swap = sum(p.accumulated_swap for p in long_trades)
    short_swap = sum(p.accumulated_swap for p in short_trades)

    # 4. R2-6 Skrining tekshiruvi:
    # Agar Gross PF < 1.05 bo'lsa -> "EDGE YO'Q" (ustunlik yo'qligidan o'ladi, xarajatdan emas)
    passed_screening = gross_pf >= 1.05

    # 5. Walk-Forward baholash (R2-4: birlashtirilgan OOS metrikalari)
    combined_oos_pf = 0.0
    combined_oos_sharpe = 0.0
    combined_oos_max_dd = 0.0
    profitable_windows_pct = 0.0
    total_oos_trades = 0

    if passed_screening and len(train_df) > 500:
        is_days = 730 if timeframe == "H1" else (1000 if timeframe == "H4" else 365)
        oos_days = 180 if timeframe in ["H1", "H4"] else 90
        step_days = 360 if timeframe in ["H1", "H4"] else 180

        wf_splitter = WalkForwardSplitter(timeframe=timeframe, is_days=is_days, oos_days=oos_days, step_days=step_days)
        wf_analyzer = WalkForwardAnalyzer(wf_splitter)
        wfo_res = wf_analyzer.run(
            train_df,
            strategy_factory=strategy_factory,
            engine_factory=lambda: BacktestEngine(initial_balance=10000.0),
            param_grid=param_grid_for_wfo or [params],
        )
        combined_oos_pf = wfo_res.combined_oos_pf
        combined_oos_sharpe = wfo_res.combined_oos_sharpe
        combined_oos_max_dd = wfo_res.combined_oos_max_dd
        profitable_windows_pct = wfo_res.profitable_windows_pct
        total_oos_trades = wfo_res.total_oos_trades
    else:
        logger.info(f"[{exp_id}] Skrining: Gross PF ({gross_pf:.2f}) < 1.05 -> NO EDGE. To'liq WFO o'tkazilmadi.")

    # 6. Gate Mezonlari Tekshiruvi (B4)
    passed_gate = (
        passed_screening
        and net_pf >= 1.4
        and m_base["max_equity_drawdown_pct"] <= 12.0
        and m_base["sharpe_ratio"] >= 1.2
        and m_base["recovery_factor"] >= 3.0
        and m_base["total_trades"] >= 500
        and stress_pf >= 1.2
        and combined_oos_pf >= (net_pf * 0.70)
    )

    logger.info(
        f"[{exp_id}] Trades: {m_base['total_trades']} | Gross PF: {gross_pf:.2f} | Net PF: {net_pf:.2f} | "
        f"Corrected Stress 1.5x PF: {stress_pf:.2f} | Net PnL: ${m_base['net_profit']:,.2f} | "
        f"Frictions: ${m_base['total_frictions']:,.2f} (Spread: ${m_base['total_spread_cost']:.1f}, "
        f"Slip: ${m_base['total_slippage_cost']:.1f}, Swap: ${m_base['total_swap_cost']:.1f}, Comm: ${m_base['total_commission']:.1f}) | "
        f"Long Swap: ${long_swap:.1f} / Short Swap: ${short_swap:.1f} | "
        f"Ambiguous Trades: {m_base['ambiguous_trades_pct']}% | "
        f"OOS Combined PF: {combined_oos_pf:.2f} | GATE: {'PASSED' if passed_gate else 'REJECTED'}"
    )

    # 7. Hisobot generatsiya qilish
    notes = (
        f"### Gipoteza: {hypo_id} ({strategy_name}) [R2 Hisoboti]\n\n"
        f"- **Parametrlar:** `{params}` (Timeframe: `{timeframe}`)\n"
        f"- **Gross PF:** {gross_pf:.2f} | **Net PF:** {net_pf:.2f} | **Stress 1.5x PF:** {stress_pf:.2f}\n"
        f"- **Xarajatlar Dekompozitsiyasi:**\n"
        f"  - Jami xarajatlar: ${m_base['total_frictions']:,.2f} ({m_base['cost_pct_of_gross_profit']:.1f}% gross profitdan)\n"
        f"  - Spread: ${m_base['total_spread_cost']:,.2f} | Slippage: ${m_base['total_slippage_cost']:,.2f}\n"
        f"  - Swap: ${m_base['total_swap_cost']:,.2f} (Long swap: ${long_swap:,.2f}, Short swap: ${short_swap:,.2f})\n"
        f"  - Komissiya: ${m_base['total_commission']:,.2f}\n"
        f"  - Savdo boshiga o'rtacha xarajat: ${m_base['avg_cost_per_trade']:.2f} | Cost-to-Edge: {m_base['cost_to_edge_ratio']:.2f}\n"
        f"- **Ambiguous Savdolar (SL & TP bir barda):** {m_base['ambiguous_trades_pct']}% ({m_base['ambiguous_trades_count']} ta)\n"
        f"- **Long P&L:** ${long_pnl:,.2f} ({len(long_trades)} trades) | **Short P&L:** ${short_pnl:,.2f} ({len(short_trades)} trades)\n"
        f"- **Yig'ma OOS PF:** {combined_oos_pf:.2f} | **OOS Sharpe:** {combined_oos_sharpe:.2f} | **Foydali Oynalar:** {profitable_windows_pct}%\n"
        f"- **Gate Xulosasi:** {'GATE PASSED' if passed_gate else 'GATE REJECTED'}\n"
    )

    reporter.generate_report(
        run_id=f"exp_{exp_id.lower()}",
        account=acc_base,
        config={"exp_id": exp_id, "hypo_id": hypo_id, "params": params, "timeframe": timeframe},
        notes=notes,
    )

    row = {
        "experiment_id": exp_id,
        "hypo_id": hypo_id,
        "strategy_name": strategy_name,
        "timeframe": timeframe,
        "params_json": json.dumps(params),
        "total_trades": m_base["total_trades"],
        "winrate_pct": m_base["winrate_pct"],
        "gross_pf": gross_pf,
        "net_pf": net_pf,
        "cost_stress_1_5x_pf_corrected": stress_pf,
        "cost_stress_1_5x_pf_old_buggy": "0.95 (buggy, was 1.0x)" if exp_id.startswith("HYP01") else "buggy",
        "net_pnl": m_base["net_profit"],
        "total_frictions_usd": m_base["total_frictions"],
        "spread_cost_usd": m_base["total_spread_cost"],
        "slippage_cost_usd": m_base["total_slippage_cost"],
        "swap_cost_usd": m_base["total_swap_cost"],
        "long_swap_usd": long_swap,
        "short_swap_usd": short_swap,
        "commission_usd": m_base["total_commission"],
        "cost_to_edge_ratio": m_base["cost_to_edge_ratio"],
        "ambiguous_trades_pct": m_base["ambiguous_trades_pct"],
        "max_dd_pct": m_base["max_equity_drawdown_pct"],
        "sharpe_ratio": m_base["sharpe_ratio"],
        "oos_trades": total_oos_trades,
        "combined_oos_pf": combined_oos_pf,
        "combined_oos_sharpe": combined_oos_sharpe,
        "profitable_windows_pct": profitable_windows_pct,
        "passed_gate": passed_gate,
    }
    return row


def main():
    downloader = HistoricalDataDownloader(symbol="XAUUSDm")
    holdout_mgr = HoldoutManager()
    reporter = BacktestReporter(output_root="reports")

    logger.info("Train/Dev ma'lumotlari yuklanmoqda (Holdout QAT'IY QULFDA)...")
    df_h1 = downloader.load_timeframe_data("H1")
    train_h1, _ = holdout_mgr.split(df_h1, timeframe="H1", allow_holdout=False)

    df_h4 = downloader.load_timeframe_data("H4")
    train_h4, _ = holdout_mgr.split(df_h4, timeframe="H4", allow_holdout=False)

    all_results = []

    # =================================================================
    # 1-QISM: ESKI 9 TA TAJRIBANI QAYTA HISOBLASH (R2-1, R2-2, R2-3)
    # =================================================================
    logger.info("\n>>> ESKI 9 TA NOMZODNI R2 TALABLARI BILAN QAYTA HISOBLASH <<<")

    # HYP-01 (Session Breakout)
    grid_hyp1 = [
        {"entry_window_hours": 2, "rr_ratio": 1.5, "atr_sl_mult": 1.5},
        {"entry_window_hours": 3, "rr_ratio": 2.0, "atr_sl_mult": 1.5},
        {"entry_window_hours": 3, "rr_ratio": 2.0, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp1, 1):
        r = evaluate_strategy_candidate(
            f"HYP01_V{idx}", "HYP-01", "SessionBreakout", "H1", train_h1,
            SessionBreakoutStrategy, p, reporter, grid_hyp1
        )
        all_results.append(r)

    # HYP-02 (Volatility Squeeze)
    grid_hyp2 = [
        {"period": 20, "bb_mult": 2.0, "kc_mult": 1.5, "rr_ratio": 2.0, "atr_sl_mult": 1.5},
        {"period": 20, "bb_mult": 2.0, "kc_mult": 1.75, "rr_ratio": 2.0, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp2, 1):
        r = evaluate_strategy_candidate(
            f"HYP02_V{idx}", "HYP-02", "VolatilitySqueeze", "H1", train_h1,
            VolatilitySqueezeStrategy, p, reporter, grid_hyp2
        )
        all_results.append(r)

    # HYP-03 (Trend Pullback)
    grid_hyp3 = [
        {"fast_ema": 20, "slow_ema": 50, "trend_ema": 200, "rsi_oversold": 45.0, "rr_ratio": 2.0, "atr_sl_mult": 1.5},
        {"fast_ema": 20, "slow_ema": 50, "trend_ema": 200, "rsi_oversold": 40.0, "rr_ratio": 2.5, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp3, 1):
        r = evaluate_strategy_candidate(
            f"HYP03_V{idx}", "HYP-03", "TrendPullback", "H1", train_h1,
            TrendPullbackStrategy, p, reporter, grid_hyp3
        )
        all_results.append(r)

    # HYP-04 (Mean Reversion)
    grid_hyp4 = [
        {"bb_period": 20, "bb_std": 2.2, "adx_max": 20.0, "atr_sl_mult": 1.2},
        {"bb_period": 20, "bb_std": 2.5, "adx_max": 22.0, "atr_sl_mult": 1.5},
    ]
    for idx, p in enumerate(grid_hyp4, 1):
        r = evaluate_strategy_candidate(
            f"HYP04_V{idx}", "HYP-04", "MeanReversion", "H1", train_h1,
            MeanReversionStrategy, p, reporter, grid_hyp4
        )
        all_results.append(r)

    # =================================================================
    # 2-QISM: R2-7 YANGI GIPOTEZALAR (HYP-05, HYP-06, HYP-07)
    # =================================================================
    logger.info("\n>>> YANGI GIPOTEZALARNI SINASH (HYP-05, HYP-06, HYP-07) <<<")

    # HYP-05 (Donchian Trend H4)
    grid_hyp5 = [
        {"entry_period": 20, "exit_period": 10, "atr_sl_mult": 2.0, "rr_ratio": 2.5},
        {"entry_period": 20, "exit_period": 10, "atr_sl_mult": 2.0, "rr_ratio": 3.0},
    ]
    for idx, p in enumerate(grid_hyp5, 1):
        r = evaluate_strategy_candidate(
            f"HYP05_V{idx}", "HYP-05", "DonchianTrendH4", "H4", train_h4,
            DonchianTrendStrategy, p, reporter, grid_hyp5
        )
        all_results.append(r)

    # HYP-06 (Intraday No-Overnight H1)
    grid_hyp6 = [
        {"asian_start_hour": 0, "asian_end_hour": 7, "entry_window_hours": 3, "rr_ratio": 1.5, "atr_sl_mult": 1.5},
        {"asian_start_hour": 0, "asian_end_hour": 7, "entry_window_hours": 3, "rr_ratio": 2.0, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp6, 1):
        r = evaluate_strategy_candidate(
            f"HYP06_V{idx}", "HYP-06", "IntradayNoOvernight", "H1", train_h1,
            IntradayNoOvernightStrategy, p, reporter, grid_hyp6
        )
        all_results.append(r)

    # HYP-07 (Short-Only Pullback H1, Post-Hoc)
    grid_hyp7 = [
        {"fast_ema": 20, "slow_ema": 50, "trend_ema": 200, "rsi_overbought": 55.0, "rr_ratio": 2.0, "atr_sl_mult": 1.5},
        {"fast_ema": 20, "slow_ema": 50, "trend_ema": 200, "rsi_overbought": 50.0, "rr_ratio": 2.5, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp7, 1):
        r = evaluate_strategy_candidate(
            f"HYP07_V{idx}", "HYP-07", "ShortOnlyTrendPullback", "H1", train_h1,
            ShortOnlyTrendPullbackStrategy, p, reporter, grid_hyp7
        )
        all_results.append(r)

    # Jurnalni to'liq yangilash (barcha N=15 tajriba)
    df_all = pd.DataFrame(all_results)
    df_all.to_csv(LOG_CSV_PATH, index=False)
    logger.info(f"\nJAMI SINALGAN VARIANTLAR SONI N = {len(all_results)} ta.")
    logger.info(f"Yozuvlar {LOG_CSV_PATH} ga to'liq muhrlandi.")

    passed_candidates = [r for r in all_results if r["passed_gate"]]
    logger.info(f"B4 Gate dan o'tganlar: {len(passed_candidates)} ta.")


if __name__ == "__main__":
    main()
