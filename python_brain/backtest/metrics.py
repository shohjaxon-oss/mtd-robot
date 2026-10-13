"""Comprehensive quantitative performance analytics and metrics computation."""

from typing import Any, Dict, List
import numpy as np
import pandas as pd
from python_brain.backtest.models import AccountState, Position


def calculate_metrics(account: AccountState) -> Dict[str, Any]:
    """Calculate professional quant metrics for backtest performance."""
    trades: List[Position] = account.closed_positions
    total_trades = len(trades)

    if total_trades == 0:
        return {
            "initial_balance": account.initial_balance,
            "final_balance": round(account.balance, 2),
            "final_equity": round(account.equity, 2),
            "net_profit": 0.0,
            "return_pct": 0.0,
            "total_trades": 0,
            "profit_factor": 0.0,
            "winrate_pct": 0.0,
            "max_equity_drawdown_pct": 0.0,
            "max_balance_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "recovery_factor": 0.0,
            "expectancy_usd": 0.0,
            "total_spread_cost": 0.0,
            "total_swap_cost": 0.0,
            "total_commission": 0.0,
        }

    pnls = [t.realized_pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_profit = sum(pnls)

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    winrate_pct = (len(wins) / total_trades * 100.0)

    # Recovery Factor = Net Profit / Max Drawdown Dollar
    max_dd_pct = max(account.max_equity_drawdown_pct, 0.01)
    max_dd_dollar = account.initial_balance * (max_dd_pct / 100.0)
    recovery_factor = (net_profit / max_dd_dollar) if max_dd_dollar > 0 else 0.0

    # Trade duration
    durations = [
        (t.close_time_utc - t.open_time_utc).total_seconds() / 3600.0
        for t in trades
        if t.close_time_utc and t.open_time_utc
    ]
    avg_duration_hours = float(np.mean(durations)) if durations else 0.0

    # Sharpe and Sortino Ratios (per trade or annualized daily)
    returns = np.array(pnls) / account.initial_balance
    mean_ret = np.mean(returns)
    std_ret = np.std(returns) if len(returns) > 1 else 0.0
    downside_returns = returns[returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 1 else 0.0

    # Annualizing assumption (~250 trading days, ~500 trades/yr)
    ann_factor = np.sqrt(total_trades) if total_trades > 0 else 1.0
    sharpe_ratio = float((mean_ret / std_ret) * ann_factor) if std_ret > 0 else 0.0
    sortino_ratio = float((mean_ret / downside_std) * ann_factor) if downside_std > 0 else 0.0

    total_spread = sum(t.spread_cost for t in trades)
    total_swap = sum(t.accumulated_swap for t in trades)
    total_commission = sum(t.commission for t in trades)

    return {
        "initial_balance": account.initial_balance,
        "final_balance": round(account.balance, 2),
        "final_equity": round(account.equity, 2),
        "net_profit": round(net_profit, 2),
        "return_pct": round((net_profit / account.initial_balance) * 100.0, 2),
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "winrate_pct": round(winrate_pct, 2),
        "profit_factor": round(profit_factor, 2),
        "max_equity_drawdown_pct": round(account.max_equity_drawdown_pct, 2),
        "max_balance_drawdown_pct": round(account.max_balance_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "recovery_factor": round(recovery_factor, 2),
        "expectancy_usd": round(float(np.mean(pnls)), 2),
        "avg_duration_hours": round(avg_duration_hours, 2),
        "total_spread_cost": round(total_spread, 2),
        "total_swap_cost": round(total_swap, 2),
        "total_commission": round(total_commission, 2),
    }
