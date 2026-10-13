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

    # R2-2: Theoretical Gross P&L and Gross Profit Factor
    gross_pnls = [getattr(t, "gross_pnl", t.realized_pnl) for t in trades]
    gross_wins = [gp for gp in gross_pnls if gp > 0]
    gross_losses = [gp for gp in gross_pnls if gp < 0]
    sum_gross_wins = sum(gross_wins)
    sum_gross_losses = abs(sum(gross_losses))
    gross_profit_factor = (
        (sum_gross_wins / sum_gross_losses)
        if sum_gross_losses > 0
        else (999.0 if sum_gross_wins > 0 else 0.0)
    )

    # Frictions breakdown
    total_spread = sum(t.spread_cost for t in trades)
    total_slippage = sum(getattr(t, "slippage_cost", 0.0) for t in trades)
    total_commission = sum(t.commission for t in trades)
    total_swap = sum(t.accumulated_swap for t in trades)
    long_swap = sum(t.accumulated_swap for t in trades if getattr(t.side, "value", str(t.side)) == "BUY")
    short_swap = sum(t.accumulated_swap for t in trades if getattr(t.side, "value", str(t.side)) == "SELL")

    # Total friction cost (note: negative swap is a cost)
    total_frictions = total_spread + total_slippage + total_commission - total_swap
    cost_pct_of_gross_profit = (
        (total_frictions / sum_gross_wins * 100.0) if sum_gross_wins > 0 else 0.0
    )
    avg_gross_per_trade = float(np.mean(gross_pnls)) if gross_pnls else 0.0
    avg_cost_per_trade = (total_frictions / total_trades) if total_trades > 0 else 0.0
    cost_to_edge_ratio = (
        (avg_cost_per_trade / avg_gross_per_trade)
        if avg_gross_per_trade > 0
        else (999.0 if avg_cost_per_trade > 0 else 0.0)
    )

    # R2-3: Ambiguous trades (both SL and TP touched on same bar)
    ambiguous_count = sum(1 for t in trades if getattr(t, "is_ambiguous_exit", False))
    ambiguous_pct = (ambiguous_count / total_trades * 100.0) if total_trades > 0 else 0.0

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

    return {
        "initial_balance": account.initial_balance,
        "final_balance": round(account.balance, 2),
        "final_equity": round(account.equity, 2),
        "net_profit": round(net_profit, 2),
        "gross_profit_raw": round(sum(gross_pnls), 2),
        "return_pct": round((net_profit / account.initial_balance) * 100.0, 2),
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "winrate_pct": round(winrate_pct, 2),
        "profit_factor": round(profit_factor, 2),
        "gross_profit_factor": round(gross_profit_factor, 2),
        "max_equity_drawdown_pct": round(account.max_equity_drawdown_pct, 2),
        "max_balance_drawdown_pct": round(account.max_balance_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "recovery_factor": round(recovery_factor, 2),
        "expectancy_usd": round(float(np.mean(pnls)), 2),
        "avg_duration_hours": round(avg_duration_hours, 2),
        "total_spread_cost": round(total_spread, 2),
        "total_slippage_cost": round(total_slippage, 2),
        "total_commission": round(total_commission, 2),
        "total_swap_cost": round(total_swap, 2),
        "long_swap_cost": round(long_swap, 2),
        "short_swap_cost": round(short_swap, 2),
        "total_frictions": round(total_frictions, 2),
        "cost_pct_of_gross_profit": round(cost_pct_of_gross_profit, 2),
        "avg_gross_per_trade": round(avg_gross_per_trade, 2),
        "avg_cost_per_trade": round(avg_cost_per_trade, 2),
        "cost_to_edge_ratio": round(cost_to_edge_ratio, 2),
        "ambiguous_trades_count": ambiguous_count,
        "ambiguous_trades_pct": round(ambiguous_pct, 2),
    }
