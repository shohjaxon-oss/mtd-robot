"""4/10 Bosqich: Strategiya Tadqiqoti va Validatsiya Protokoli (B3 - B4).

Barcha sinovlar QAT'IY ravishda faqat Train/Dev (80%) ma'lumotlarida o'tkaziladi.
Holdout (oxirgi 20%) qulflangan.

Baholash mezonlari:
1. Tajriba jurnali: research/experiment_log.csv ga har bir sinov qayd etiladi.
2. Xarajat stressi: 1.0x va 1.5x xarajatlar ostida sinov.
3. Long va Short alohida ajratiladi.
4. Walk-forward efficiency (WFO): OOS PF >= IS PF * 0.70.
5. Gate mezonlari: PF >= 1.4, Max DD <= 12%, Sharpe >= 1.2, Recovery >= 3, Savdolar >= 500.
"""

from __future__ import annotations

import json
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
from python_brain.backtest.montecarlo import MonteCarloEngine
from python_brain.backtest.reporter import BacktestReporter
from python_brain.backtest.risk_gate import DefaultRiskGate
from python_brain.backtest.strategy_base import Strategy
from python_brain.backtest.walkforward import WalkForwardAnalyzer, WalkForwardSplitter
from python_brain.signals.mean_reversion import MeanReversionStrategy
from python_brain.signals.session_breakout import SessionBreakoutStrategy
from python_brain.signals.trend_pullback import TrendPullbackStrategy
from python_brain.signals.volatility_squeeze import VolatilitySqueezeStrategy


LOG_CSV_PATH = Path("research/experiment_log.csv")


def log_experiment_to_csv(row_dict: Dict[str, Any]) -> None:
    """Natijani research/experiment_log.csv ga yozadi."""
    df_row = pd.DataFrame([row_dict])
    if not LOG_CSV_PATH.exists() or LOG_CSV_PATH.stat().st_size == 0:
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
    mc_engine: MonteCarloEngine,
) -> Dict[str, Any]:
    logger.info(f"\n=======================================================")
    logger.info(f"Sinov: {exp_id} ({hypo_id}: {strategy_name}) Params: {params}")
    logger.info(f"=======================================================")

    # 1. Baza Backtest (1.0x Real Cost, Train 80%)
    strat_base = strategy_factory(**params)
    cost_base = CostModel()
    gate_base = DefaultRiskGate(risk_per_trade_pct=0.5, halt_on_kill_switch=False)
    engine_base = BacktestEngine(initial_balance=10000.0)

    acc_base = engine_base.run(train_df, strat_base, risk_gate=gate_base, cost_model=cost_base)
    m_base = calculate_metrics(acc_base)

    # 2. Xarajat Stress Testi (1.5x)
    strat_stress = strategy_factory(**params)
    cost_stress = CostModel(stress_multiplier=1.5)
    gate_stress = DefaultRiskGate(risk_per_trade_pct=0.5, halt_on_kill_switch=False)
    engine_stress = BacktestEngine(initial_balance=10000.0)

    acc_stress = engine_stress.run(train_df, strat_stress, risk_gate=gate_stress, cost_model=cost_stress)
    m_stress = calculate_metrics(acc_stress)

    # 3. Long va Short ajratish
    long_trades = [p for p in acc_base.closed_positions if p.side.value == "BUY"]
    short_trades = [p for p in acc_base.closed_positions if p.side.value == "SELL"]
    long_pnl = sum(p.realized_pnl for p in long_trades)
    short_pnl = sum(p.realized_pnl for p in short_trades)

    # 4. Ambiguous barlar foizi
    sl_points = params.get("atr_sl_mult", 1.5) * 2000.0
    tp_points = sl_points * params.get("rr_ratio", 2.0)
    req_range = (sl_points + tp_points) * 0.001
    amb_count = int(((train_df["high"] - train_df["low"]) >= req_range).sum())
    amb_pct = round((amb_count / max(1, len(train_df))) * 100.0, 2)

    # 5. Walk-Forward baholash (3 ta vakillik oynasi tezkor test)
    wf_splitter = WalkForwardSplitter(timeframe=timeframe, is_days=730, oos_days=180, step_days=360)
    wf_analyzer = WalkForwardAnalyzer(wf_splitter)
    wfo_results = wf_analyzer.run(
        train_df,
        strategy_factory=lambda: strategy_factory(**params),
        engine_factory=lambda: BacktestEngine(initial_balance=10000.0),
    )

    oos_pfs = [r.oos_metrics.get("profit_factor", 0.0) for r in wfo_results]
    oos_sharpes = [r.oos_metrics.get("sharpe_ratio", 0.0) for r in wfo_results]
    avg_oos_pf = float(np.mean(oos_pfs)) if oos_pfs else 0.0
    avg_oos_sharpe = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
    total_oos_trades = sum(r.oos_metrics.get("total_trades", 0) for r in wfo_results)

    # 6. Gate Mezonlari Tekshiruvi (B4)
    # Shartlar: PF >= 1.4, Max DD <= 12%, Sharpe >= 1.2, Recovery >= 3, Savdolar >= 500
    passed_gate = (
        m_base["profit_factor"] >= 1.4
        and m_base["max_equity_drawdown_pct"] <= 12.0
        and m_base["sharpe_ratio"] >= 1.2
        and m_base["recovery_factor"] >= 3.0
        and m_base["total_trades"] >= 500
        and m_stress["profit_factor"] >= 1.2
    )

    logger.info(
        f"[{exp_id}] Trades: {m_base['total_trades']} | PF: {m_base['profit_factor']:.2f} (Stress 1.5x: {m_stress['profit_factor']:.2f}) | "
        f"Net PnL: ${m_base['net_profit']:,.2f} | Max DD: {m_base['max_equity_drawdown_pct']:.2f}% | "
        f"Sharpe: {m_base['sharpe_ratio']:.2f} | Long/Short PnL: ${long_pnl:.1f} / ${short_pnl:.1f} | "
        f"OOS PF: {avg_oos_pf:.2f} | GATE: {'PASSED' if passed_gate else 'REJECTED'}"
    )

    # 7. Hisobot generatsiya qilish
    notes = (
        f"### Gipoteza: {hypo_id} ({strategy_name})\n\n"
        f"- **Parametrlar:** `{params}`\n"
        f"- **Baza PF (1.0x):** {m_base['profit_factor']:.2f} | **Stress PF (1.5x):** {m_stress['profit_factor']:.2f}\n"
        f"- **Long P&L:** ${long_pnl:,.2f} ({len(long_trades)} trades)\n"
        f"- **Short P&L:** ${short_pnl:,.2f} ({len(short_trades)} trades)\n"
        f"- **Ambiguous Barlar:** {amb_pct}%\n"
        f"- **OOS Average PF:** {avg_oos_pf:.2f} | **OOS Sharpe:** {avg_oos_sharpe:.2f}\n"
        f"- **Gate Xulosasi:** {'GATE PASSED' if passed_gate else 'GATE REJECTED'}\n"
    )

    reporter.generate_report(
        run_id=f"exp_{exp_id.lower()}",
        account=acc_base,
        config={"exp_id": exp_id, "hypo_id": hypo_id, "params": params, "timeframe": timeframe},
        notes=notes,
    )

    # 8. experiment_log.csv ga yozish
    row = {
        "experiment_id": exp_id,
        "hypo_id": hypo_id,
        "strategy_name": strategy_name,
        "timeframe": timeframe,
        "params_json": json.dumps(params),
        "total_trades": m_base["total_trades"],
        "winrate_pct": m_base["winrate_pct"],
        "profit_factor": m_base["profit_factor"],
        "net_pnl": m_base["net_profit"],
        "max_dd_pct": m_base["max_equity_drawdown_pct"],
        "sharpe_ratio": m_base["sharpe_ratio"],
        "sortino_ratio": m_base["sortino_ratio"],
        "expectancy_usd": m_base["expectancy_usd"],
        "oos_trades": total_oos_trades,
        "oos_pf": round(avg_oos_pf, 2),
        "oos_sharpe": round(avg_oos_sharpe, 2),
        "cost_stress_1_5x_pf": m_stress["profit_factor"],
        "ambiguous_bar_pct": amb_pct,
        "passed_gate": passed_gate,
    }
    log_experiment_to_csv(row)

    return row


def main():
    downloader = HistoricalDataDownloader(symbol="XAUUSDm")
    holdout_mgr = HoldoutManager()
    reporter = BacktestReporter(output_root="reports")
    mc_engine = MonteCarloEngine(initial_balance=10000.0)

    # Ma'lumotlarni yuklash (Faqat 80% Train, Holdout QULFDA!)
    logger.info("Train/Dev ma'lumotlari yuklanmoqda (Holdout muhrlangan)...")
    df_h1 = downloader.load_timeframe_data("H1")
    train_h1, _ = holdout_mgr.split(df_h1, timeframe="H1", allow_holdout=False)

    df_m15 = downloader.load_timeframe_data("M15")
    train_m15, _ = holdout_mgr.split(df_m15, timeframe="M15", allow_holdout=False)

    results = []

    # -----------------------------------------------------------------
    # GIPOTEZA 1: HYP-01 (Session Breakout)
    # -----------------------------------------------------------------
    grid_hyp1 = [
        {"entry_window_hours": 2, "rr_ratio": 1.5, "atr_sl_mult": 1.5},
        {"entry_window_hours": 3, "rr_ratio": 2.0, "atr_sl_mult": 1.5},
        {"entry_window_hours": 3, "rr_ratio": 2.0, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp1, 1):
        res = evaluate_strategy_candidate(
            exp_id=f"HYP01_V{idx}",
            hypo_id="HYP-01",
            strategy_name="SessionBreakout",
            timeframe="H1",
            train_df=train_h1,
            strategy_factory=SessionBreakoutStrategy,
            params=p,
            reporter=reporter,
            mc_engine=mc_engine,
        )
        results.append(res)

    # -----------------------------------------------------------------
    # GIPOTEZA 2: HYP-02 (Volatility Squeeze)
    # -----------------------------------------------------------------
    grid_hyp2 = [
        {"period": 20, "bb_mult": 2.0, "kc_mult": 1.5, "rr_ratio": 2.0, "atr_sl_mult": 1.5},
        {"period": 20, "bb_mult": 2.0, "kc_mult": 1.75, "rr_ratio": 2.0, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp2, 1):
        res = evaluate_strategy_candidate(
            exp_id=f"HYP02_V{idx}",
            hypo_id="HYP-02",
            strategy_name="VolatilitySqueeze",
            timeframe="H1",
            train_df=train_h1,
            strategy_factory=VolatilitySqueezeStrategy,
            params=p,
            reporter=reporter,
            mc_engine=mc_engine,
        )
        results.append(res)

    # -----------------------------------------------------------------
    # GIPOTEZA 3: HYP-03 (Trend Pullback)
    # -----------------------------------------------------------------
    grid_hyp3 = [
        {"fast_ema": 20, "slow_ema": 50, "trend_ema": 200, "rsi_oversold": 45.0, "rr_ratio": 2.0, "atr_sl_mult": 1.5},
        {"fast_ema": 20, "slow_ema": 50, "trend_ema": 200, "rsi_oversold": 40.0, "rr_ratio": 2.5, "atr_sl_mult": 2.0},
    ]
    for idx, p in enumerate(grid_hyp3, 1):
        res = evaluate_strategy_candidate(
            exp_id=f"HYP03_V{idx}",
            hypo_id="HYP-03",
            strategy_name="TrendPullback",
            timeframe="H1",
            train_df=train_h1,
            strategy_factory=TrendPullbackStrategy,
            params=p,
            reporter=reporter,
            mc_engine=mc_engine,
        )
        results.append(res)

    # -----------------------------------------------------------------
    # GIPOTEZA 4: HYP-04 (Mean Reversion)
    # -----------------------------------------------------------------
    grid_hyp4 = [
        {"bb_period": 20, "bb_std": 2.2, "adx_max": 20.0, "atr_sl_mult": 1.2},
        {"bb_period": 20, "bb_std": 2.5, "adx_max": 22.0, "atr_sl_mult": 1.5},
    ]
    for idx, p in enumerate(grid_hyp4, 1):
        res = evaluate_strategy_candidate(
            exp_id=f"HYP04_V{idx}",
            hypo_id="HYP-04",
            strategy_name="MeanReversion",
            timeframe="H1",
            train_df=train_h1,
            strategy_factory=MeanReversionStrategy,
            params=p,
            reporter=reporter,
            mc_engine=mc_engine,
        )
        results.append(res)

    logger.info("\n=======================================================")
    logger.info("BARCHA 4 TA GIPOTEZA SINAVLARI YAKUNLANDI!")
    logger.info("=======================================================")

    passed = [r for r in results if r["passed_gate"]]
    logger.info(f"Jami sinovlar soni: {len(results)} ta. Gate dan o'tganlar: {len(passed)} ta.")


if __name__ == "__main__":
    main()
