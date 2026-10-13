"""Comprehensive validation runner for FU FORMATION Strategy (HYP-09).

Executes:
1. Baseline: "FU_PURE" on M1, M3, M5 (3 runs)
2. Variants: min_trend_candles in {3, 4}, engulf_mode in {body, range}
3. Diagnostics: BUY-only vs SELL-only, zero-cost vs real-cost vs 1.5x/2.0x stress
4. Cost decomposition: gross PnL, net PnL, spread, slippage, swap, commission
5. Detailed setup & leg breakdown: Leg A vs Leg B PnL, exit types (TP_A, TP_B, BE, SL)
6. SL distance distribution (pips), realized R:R, breakeven winrate requirement
7. Ambiguous exit %, bootstrap 95% CI for Profit Factor
8. Monte Carlo analysis (1000 iter) & Walk-Forward Analysis
9. Strict Gate check against TZ section 1 criteria
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_brain.data.downloader import HistoricalDataDownloader
from python_brain.backtest.holdout import HoldoutManager
from python_brain.backtest.engine import BacktestEngine
from python_brain.backtest.risk_gate import DefaultRiskGate
from python_brain.backtest.costs import CostModel
from python_brain.backtest.walkforward import WalkForwardSplitter, WalkForwardAnalyzer
from python_brain.backtest.montecarlo import MonteCarloEngine
from python_brain.signals.fu_formation import FUFormationStrategy


class ZeroCostModel(CostModel):
    """Nol xarajatli test modeli (Gross baseline)."""
    def __init__(self):
        super().__init__(base_spread_points=0.0, commission_per_lot=0.0, swap_long_usd_per_lot=0.0, swap_short_usd_per_lot=0.0)

    def get_effective_spread(self, *args, **kwargs):
        return 0.0, 0.0

    def get_slippage_penalty(self, *args, **kwargs):
        return 0.0

    def calculate_swap(self, *args, **kwargs):
        return 0.0



def compute_metrics(closed_positions, initial_balance=10000.0) -> Dict[str, Any]:
    if not closed_positions:
        return {
            "total_trades": 0, "winrate_pct": 0.0, "gross_pf": 0.0, "net_pf": 0.0,
            "net_pnl": 0.0, "max_dd_pct": 0.0, "sharpe_ratio": 0.0,
            "spread_cost_usd": 0.0, "slippage_cost_usd": 0.0, "swap_cost_usd": 0.0,
            "long_swap_usd": 0.0, "short_swap_usd": 0.0, "commission_usd": 0.0,
            "total_frictions_usd": 0.0, "cost_to_edge_ratio": 999.0,
            "ambiguous_trades_pct": 0.0, "ambiguous_count": 0,
            "leg_a_pnl": 0.0, "leg_b_pnl": 0.0, "leg_a_trades": 0, "leg_b_trades": 0,
            "exit_tp_a": 0, "exit_tp_b": 0, "exit_be": 0, "exit_sl": 0,
            "sl_pips_mean": 0.0, "sl_pips_median": 0.0, "sl_pips_p25": 0.0, "sl_pips_p75": 0.0,
            "realized_rr": 0.0, "required_be_winrate_pct": 0.0, "unique_days": 0,
            "pf_ci_lower": 0.0, "pf_ci_upper": 0.0,
        }

    pnls = [p.realized_pnl for p in closed_positions]
    gross_pnls = [p.gross_pnl for p in closed_positions]

    wins = [x for x in pnls if x > 0]
    losses = [abs(x) for x in pnls if x < 0]
    gross_wins = [x for x in gross_pnls if x > 0]
    gross_losses = [abs(x) for x in gross_pnls if x < 0]

    net_pf = round(sum(wins) / sum(losses), 2) if sum(losses) > 0 else (999.0 if sum(wins) > 0 else 0.0)
    gross_pf = round(sum(gross_wins) / sum(gross_losses), 2) if sum(gross_losses) > 0 else (999.0 if sum(gross_wins) > 0 else 0.0)

    winrate = round((len(wins) / len(pnls)) * 100.0, 2)
    net_pnl = round(sum(pnls), 2)

    # Max Drawdown & Equity Curve
    cum_pnl = np.cumsum(pnls)
    equity_curve = initial_balance + cum_pnl
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = (peaks - equity_curve) / peaks * 100.0
    max_dd = round(float(np.max(drawdowns)), 2)

    # Sharpe ratio (annualized, per trade basis)
    mean_ret = np.mean(pnls)
    std_ret = np.std(pnls)
    sharpe = round(float(mean_ret / std_ret * np.sqrt(252 * 5)), 2) if std_ret > 0 else 0.0

    # Frictions
    spread_cost = round(sum(p.spread_cost for p in closed_positions), 2)
    slippage_cost = round(sum(p.slippage_cost for p in closed_positions), 2)
    swap_cost = round(sum(p.accumulated_swap for p in closed_positions), 2)
    long_swap = round(sum(p.accumulated_swap for p in closed_positions if p.side.value == "BUY"), 2)
    short_swap = round(sum(p.accumulated_swap for p in closed_positions if p.side.value == "SELL"), 2)
    commission = round(sum(p.commission for p in closed_positions), 2)
    total_frictions = round(spread_cost + slippage_cost + abs(swap_cost) + commission, 2)

    gross_profit = sum(gross_wins) - sum(gross_losses)
    cost_to_edge = round(total_frictions / abs(gross_profit), 2) if abs(gross_profit) > 0 else 999.0

    # Ambiguous exits
    ambiguous_count = sum(1 for p in closed_positions if p.is_ambiguous_exit)
    ambiguous_pct = round((ambiguous_count / len(closed_positions)) * 100.0, 2)

    # Leg level breakdown
    legs_a = [p for p in closed_positions if p.leg_id == "A"]
    legs_b = [p for p in closed_positions if p.leg_id == "B"]
    leg_a_pnl = round(sum(p.realized_pnl for p in legs_a), 2)
    leg_b_pnl = round(sum(p.realized_pnl for p in legs_b), 2)

    # Exit types
    exit_tp_a = sum(1 for p in legs_a if p.exit_reason and p.exit_reason.value == "TAKE_PROFIT")
    exit_tp_b = sum(1 for p in legs_b if p.exit_reason and p.exit_reason.value == "TAKE_PROFIT")
    exit_be = sum(1 for p in legs_b if p.exit_reason and p.exit_reason.value == "STOP_LOSS" and p.breakeven_activated)
    exit_sl = sum(1 for p in closed_positions if p.exit_reason and p.exit_reason.value == "STOP_LOSS" and not p.breakeven_activated)

    # SL distance distribution (in pips: 1 pip = 0.10 USD)
    sl_pips_list = []
    for p in closed_positions:
        if p.original_sl:
            dist = abs(p.open_price - p.original_sl) / 0.10
            sl_pips_list.append(dist)
    if sl_pips_list:
        sl_pips_mean = round(float(np.mean(sl_pips_list)), 1)
        sl_pips_median = round(float(np.median(sl_pips_list)), 1)
        sl_pips_p25 = round(float(np.percentile(sl_pips_list, 25)), 1)
        sl_pips_p75 = round(float(np.percentile(sl_pips_list, 75)), 1)
    else:
        sl_pips_mean = sl_pips_median = sl_pips_p25 = sl_pips_p75 = 0.0

    # Realized R:R
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    realized_rr = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0

    # Breakeven winrate: required_wr = 1 / (1 + rr)
    req_wr = round((1.0 / (1.0 + realized_rr)) * 100.0, 2) if realized_rr > 0 else 50.0

    # Unique trading days
    dates = set(p.open_time_utc.strftime("%Y-%m-%d") for p in closed_positions if p.open_time_utc)
    unique_days = len(dates)

    # Bootstrap 95% CI for Profit Factor (1000 resamples)
    boot_pfs = []
    np.random.seed(42)
    n = len(pnls)
    if n >= 20:
        for _ in range(1000):
            sample = np.random.choice(pnls, size=n, replace=True)
            s_w = sum(x for x in sample if x > 0)
            s_l = sum(abs(x) for x in sample if x < 0)
            boot_pfs.append(s_w / s_l if s_l > 0 else 1.0)
        pf_ci_lower = round(float(np.percentile(boot_pfs, 2.5)), 2)
        pf_ci_upper = round(float(np.percentile(boot_pfs, 97.5)), 2)
    else:
        pf_ci_lower = pf_ci_upper = net_pf

    return {
        "total_trades": len(closed_positions),
        "winrate_pct": winrate,
        "gross_pf": gross_pf,
        "net_pf": net_pf,
        "net_pnl": net_pnl,
        "max_dd_pct": max_dd,
        "sharpe_ratio": sharpe,
        "spread_cost_usd": spread_cost,
        "slippage_cost_usd": slippage_cost,
        "swap_cost_usd": swap_cost,
        "long_swap_usd": long_swap,
        "short_swap_usd": short_swap,
        "commission_usd": commission,
        "total_frictions_usd": total_frictions,
        "cost_to_edge_ratio": cost_to_edge,
        "ambiguous_trades_pct": ambiguous_pct,
        "ambiguous_count": ambiguous_count,
        "leg_a_pnl": leg_a_pnl,
        "leg_b_pnl": leg_b_pnl,
        "leg_a_trades": len(legs_a),
        "leg_b_trades": len(legs_b),
        "exit_tp_a": exit_tp_a,
        "exit_tp_b": exit_tp_b,
        "exit_be": exit_be,
        "exit_sl": exit_sl,
        "sl_pips_mean": sl_pips_mean,
        "sl_pips_median": sl_pips_median,
        "sl_pips_p25": sl_pips_p25,
        "sl_pips_p75": sl_pips_p75,
        "realized_rr": realized_rr,
        "required_be_winrate_pct": req_wr,
        "unique_days": unique_days,
        "pf_ci_lower": pf_ci_lower,
        "pf_ci_upper": pf_ci_upper,
    }


def run_experiment(exp_id: str, tf: str, params: dict, df_train: pd.DataFrame) -> Dict[str, Any]:
    print(f"\n---> Running {exp_id} on {tf} with params: {params}...")
    strat = FUFormationStrategy(
        timeframe=tf,
        min_trend_candles=params.get("min_trend_candles", 3),
        engulf_mode=params.get("engulf_mode", "body"),
        sl_buffer_pips=params.get("sl_buffer_pips", 5.0),
        tp1_pips=params.get("tp1_pips", 20.0),
        tp2_pips=params.get("tp2_pips", 30.0),
        lot_per_leg=params.get("lot_per_leg", 0.01),
        pip_size_price=params.get("pip_size_price", 0.10),
    )

    engine = BacktestEngine(initial_balance=10000.0)
    risk_gate = DefaultRiskGate()

    # 1. Real cost (1.0x)
    cost_1_0 = CostModel(point=0.001, contract_size=100.0)
    acc_1_0 = engine.run(df_train, strategy=strat, risk_gate=risk_gate, cost_model=cost_1_0)
    m_1_0 = compute_metrics(acc_1_0.closed_positions)

    # 2. Stress cost (1.5x)
    cost_1_5 = CostModel(point=0.001, contract_size=100.0, stress_multiplier=1.5)
    acc_1_5 = engine.run(df_train, strategy=strat, risk_gate=risk_gate, cost_model=cost_1_5)
    m_1_5 = compute_metrics(acc_1_5.closed_positions)

    # 3. Stress cost (2.0x)
    cost_2_0 = CostModel(point=0.001, contract_size=100.0, stress_multiplier=2.0)
    acc_2_0 = engine.run(df_train, strategy=strat, risk_gate=risk_gate, cost_model=cost_2_0)
    m_2_0 = compute_metrics(acc_2_0.closed_positions)

    # 4. Zero cost (Gross)
    cost_0_0 = ZeroCostModel()
    acc_0_0 = engine.run(df_train, strategy=strat, risk_gate=risk_gate, cost_model=cost_0_0)
    m_0_0 = compute_metrics(acc_0_0.closed_positions)

    # 5. Walk-Forward Analysis (Nested rolling windows)
    combined_oos_pf = 0.0
    combined_oos_sharpe = 0.0
    oos_trades = 0
    prof_win_pct = 0.0

    if len(df_train) >= 5000:
        try:
            if tf == "M5":
                is_days, oos_days, step_days = 90, 30, 30
            else:
                is_days, oos_days, step_days = 30, 10, 10
            splitter = WalkForwardSplitter(
                timeframe=tf,
                is_days=is_days,
                oos_days=oos_days,
                step_days=step_days,
                anchored=False,
            )
            analyzer = WalkForwardAnalyzer(splitter=splitter)
            wf_res = analyzer.run(
                df_train,
                strategy_factory=lambda **kw: FUFormationStrategy(timeframe=tf, **kw),
                engine_factory=lambda: BacktestEngine(initial_balance=10000.0),
                param_grid=[params],
            )
            combined_oos_pf = round(wf_res.combined_oos_pf, 2)
            combined_oos_sharpe = round(wf_res.combined_oos_sharpe, 2)
            oos_trades = wf_res.total_oos_trades
            prof_win_pct = round(wf_res.profitable_windows_pct, 2)
        except Exception as e:
            print(f"    WFO warning: {e}")

    # 6. Monte Carlo Simulation (Bootstrap reshuffle)
    mc_median_dd = 0.0
    mc_p95_dd = 0.0
    mc_ruin_prob = 0.0
    mc_drop10_pf = 0.0

    if len(acc_1_0.closed_positions) >= 20:
        mc = MonteCarloEngine(n_simulations=1000, random_seed=42)
        mc_res = mc.run(acc_1_0.closed_positions, initial_balance=10000.0)
        mc_median_dd = round(mc_res.median_drawdown_pct, 2)
        mc_p95_dd = round(mc_res.p95_drawdown_pct, 2)
        mc_ruin_prob = round(mc_res.risk_of_ruin_pct, 2)
        mc_drop10_pf = round(mc_res.drop_top_10pct_pf, 2)

    # Gate verification (TZ 1-bo'lim)
    passed_gate = (
        m_1_0["net_pf"] >= 1.4
        and m_1_0["max_dd_pct"] <= 12.0
        and m_1_0["sharpe_ratio"] >= 1.2
        and m_1_0["total_trades"] >= 500
        and m_1_5["net_pf"] >= 1.15
        and mc_p95_dd <= 20.0
    )

    res = {
        "experiment_id": exp_id,
        "hypo_id": "HYP-09",
        "strategy_name": "FUFormation",
        "timeframe": tf,
        "params_json": json.dumps(params),
        "total_trades": m_1_0["total_trades"],
        "winrate_pct": m_1_0["winrate_pct"],
        "gross_pf": m_0_0["net_pf"],
        "net_pf": m_1_0["net_pf"],
        "cost_stress_1_5x_pf": m_1_5["net_pf"],
        "cost_stress_2_0x_pf": m_2_0["net_pf"],
        "net_pnl": m_1_0["net_pnl"],
        "total_frictions_usd": m_1_0["total_frictions_usd"],
        "spread_cost_usd": m_1_0["spread_cost_usd"],
        "slippage_cost_usd": m_1_0["slippage_cost_usd"],
        "swap_cost_usd": m_1_0["swap_cost_usd"],
        "long_swap_usd": m_1_0["long_swap_usd"],
        "short_swap_usd": m_1_0["short_swap_usd"],
        "commission_usd": m_1_0["commission_usd"],
        "cost_to_edge_ratio": m_1_0["cost_to_edge_ratio"],
        "ambiguous_trades_pct": m_1_0["ambiguous_trades_pct"],
        "max_dd_pct": m_1_0["max_dd_pct"],
        "sharpe_ratio": m_1_0["sharpe_ratio"],
        "oos_trades": oos_trades,
        "combined_oos_pf": combined_oos_pf,
        "combined_oos_sharpe": combined_oos_sharpe,
        "profitable_windows_pct": prof_win_pct,
        "mc_median_dd": mc_median_dd,
        "mc_p95_dd": mc_p95_dd,
        "mc_ruin_prob": mc_ruin_prob,
        "mc_drop10_pf": mc_drop10_pf,
        "pf_ci_lower": m_1_0["pf_ci_lower"],
        "pf_ci_upper": m_1_0["pf_ci_upper"],
        "leg_a_pnl": m_1_0["leg_a_pnl"],
        "leg_b_pnl": m_1_0["leg_b_pnl"],
        "exit_tp_a": m_1_0["exit_tp_a"],
        "exit_tp_b": m_1_0["exit_tp_b"],
        "exit_be": m_1_0["exit_be"],
        "exit_sl": m_1_0["exit_sl"],
        "sl_pips_mean": m_1_0["sl_pips_mean"],
        "sl_pips_median": m_1_0["sl_pips_median"],
        "realized_rr": m_1_0["realized_rr"],
        "required_be_winrate_pct": m_1_0["required_be_winrate_pct"],
        "unique_days": m_1_0["unique_days"],
        "passed_gate": passed_gate,
    }

    print(f"    Trades: {res['total_trades']} | Gross PF: {res['gross_pf']} | Net PF: {res['net_pf']} | Stress 1.5x: {res['cost_stress_1_5x_pf']}")
    print(f"    Net PnL: ${res['net_pnl']} | Max DD: {res['max_dd_pct']}% | WFO OOS PF: {res['combined_oos_pf']} | Passed: {res['passed_gate']}")
    return res


def main():
    print("==================================================================")
    print("      FU FORMATION STRATEGY (HYP-09) SCIENTIFIC VALIDATION        ")
    print("==================================================================")

    downloader = HistoricalDataDownloader(symbol="XAUUSDm")
    holdout = HoldoutManager()

    # Load datasets
    df_m5_full = downloader.load_timeframe_data("M5")
    df_m3_full = downloader.load_timeframe_data("M3")
    df_m1_full = downloader.load_timeframe_data("M1")

    # Split into 80% Train/Dev (Holdout remains locked!)
    df_m5_train, _ = holdout.split(df_m5_full, timeframe="M5", allow_holdout=False)
    df_m3_train, _ = holdout.split(df_m3_full, timeframe="M3", allow_holdout=False)
    df_m1_train, _ = holdout.split(df_m1_full, timeframe="M1", allow_holdout=False)

    print(f"Train/Dev datasets (80%): M5 ({len(df_m5_train)} bars), M3 ({len(df_m3_train)} bars), M1 ({len(df_m1_train)} bars)")

    experiments = [
        # 1. Baselines ("FU_PURE" on M5, M3, M1)
        ("HYP09_M5_PURE", "M5", {"min_trend_candles": 3, "engulf_mode": "body"}, df_m5_train),
        ("HYP09_M3_PURE", "M3", {"min_trend_candles": 3, "engulf_mode": "body"}, df_m3_train),
        ("HYP09_M1_PURE", "M1", {"min_trend_candles": 3, "engulf_mode": "body"}, df_m1_train),

        # 2. Variants on M5
        ("HYP09_M5_V1", "M5", {"min_trend_candles": 4, "engulf_mode": "body"}, df_m5_train),
        ("HYP09_M5_V2", "M5", {"min_trend_candles": 3, "engulf_mode": "range"}, df_m5_train),
        ("HYP09_M5_V3", "M5", {"min_trend_candles": 4, "engulf_mode": "range"}, df_m5_train),

        # 3. Variants on M3 and M1
        ("HYP09_M3_V1", "M3", {"min_trend_candles": 4, "engulf_mode": "body"}, df_m3_train),
        ("HYP09_M1_V1", "M1", {"min_trend_candles": 4, "engulf_mode": "body"}, df_m1_train),
    ]

    results = []
    for exp_id, tf, params, df_data in experiments:
        res = run_experiment(exp_id, tf, params, df_data)
        results.append(res)

    # Save detailed JSON report
    out_dir = Path("reports/fu_formation")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "fu_formation_validation.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Append to research/experiment_log.csv
    exp_log_path = Path("research/experiment_log.csv")
    csv_rows = []
    for r in results:
        csv_rows.append({
            "experiment_id": r["experiment_id"],
            "hypo_id": r["hypo_id"],
            "strategy_name": r["strategy_name"],
            "timeframe": r["timeframe"],
            "params_json": r["params_json"],
            "total_trades": r["total_trades"],
            "winrate_pct": r["winrate_pct"],
            "gross_pf": r["gross_pf"],
            "net_pf": r["net_pf"],
            "cost_stress_1_5x_pf_corrected": r["cost_stress_1_5x_pf"],
            "cost_stress_1_5x_pf_old_buggy": "N/A (Correct 1.5x)",
            "net_pnl": r["net_pnl"],
            "total_frictions_usd": r["total_frictions_usd"],
            "spread_cost_usd": r["spread_cost_usd"],
            "slippage_cost_usd": r["slippage_cost_usd"],
            "swap_cost_usd": r["swap_cost_usd"],
            "long_swap_usd": r["long_swap_usd"],
            "short_swap_usd": r["short_swap_usd"],
            "commission_usd": r["commission_usd"],
            "cost_to_edge_ratio": r["cost_to_edge_ratio"],
            "ambiguous_trades_pct": r["ambiguous_trades_pct"],
            "max_dd_pct": r["max_dd_pct"],
            "sharpe_ratio": r["sharpe_ratio"],
            "oos_trades": r["oos_trades"],
            "combined_oos_pf": r["combined_oos_pf"],
            "combined_oos_sharpe": r["combined_oos_sharpe"],
            "profitable_windows_pct": r["profitable_windows_pct"],
            "passed_gate": r["passed_gate"],
        })

    df_csv = pd.DataFrame(csv_rows)
    df_csv.to_csv(exp_log_path, mode="a", header=False, index=False)
    print(f"\n[OK] Validation complete. {len(results)} experiments recorded to research/experiment_log.csv.")


if __name__ == "__main__":
    main()
