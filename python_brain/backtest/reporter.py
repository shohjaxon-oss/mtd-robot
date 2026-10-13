"""Backtest natijalarini saqlash, vizuallashtirish va hisobot yaratish moduli.

reports/<run_id>/ katalogida:
- trades.csv
- metrics.json
- report.md
- equity_curve.png
- config_snapshot.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # Headless muhit
import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger

from python_brain.backtest.metrics import calculate_metrics
from python_brain.backtest.models import AccountState, Position


class BacktestReporter:
    def __init__(self, output_root: str = "reports") -> None:
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        run_id: str,
        account: AccountState,
        equity_curve: Optional[List[float]] = None,
        config: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Path:
        """Backtest yugurishi uchun to'liq hisobot katalogini shakllantiradi."""
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating backtest report in {run_dir}...")

        metrics = calculate_metrics(account)

        # 1. trades.csv
        trades_df = self._save_trades(run_dir, account.closed_positions)

        # 2. metrics.json
        self._save_metrics(run_dir, metrics)

        # 3. equity_curve.png
        self._save_equity_chart(run_dir, equity_curve, account)

        # 4. config_snapshot.json
        self._save_config(run_dir, config)

        # 5. report.md
        self._save_markdown_summary(run_dir, run_id, metrics, notes)

        logger.info(f"Report successfully saved to {run_dir}")
        return run_dir

    def _save_trades(self, run_dir: Path, positions: List[Position]) -> pd.DataFrame:
        records = []
        for p in positions:
            records.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "side": p.side.value if hasattr(p.side, "value") else str(p.side),
                "volume": p.volume,
                "open_time": p.open_time_utc.isoformat() if p.open_time_utc else None,
                "open_price": p.open_price,
                "close_time": p.close_time_utc.isoformat() if p.close_time_utc else None,
                "close_price": p.close_price,
                "sl": p.sl,
                "tp": p.tp,
                "exit_reason": p.exit_reason.value if hasattr(p.exit_reason, "value") and p.exit_reason else str(p.exit_reason),
                "realized_pnl": p.realized_pnl,
                "spread_cost": p.spread_cost,
                "slippage_cost": p.slippage_cost,
                "accumulated_swap": p.accumulated_swap,
                "commission": p.commission,
            })
        df = pd.DataFrame(records)
        df.to_csv(run_dir / "trades.csv", index=False)
        return df

    def _save_metrics(self, run_dir: Path, metrics: Dict[str, Any]) -> None:
        with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)

    def _save_config(self, run_dir: Path, config: Optional[Dict[str, Any]]) -> None:
        if config is None:
            config = {}
        snapshot = {
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            "config": config,
        }
        with open(run_dir / "config_snapshot.json", "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, default=str)

    def _save_equity_chart(
        self,
        run_dir: Path,
        equity_curve: Optional[List[float]],
        account: AccountState,
    ) -> None:
        if not equity_curve:
            # Closed trades bo'yicha cumsum equity yasaymiz
            pnls = [p.realized_pnl for p in account.closed_positions]
            equity_curve = [account.initial_balance]
            curr = account.initial_balance
            for p in pnls:
                curr += p
                equity_curve.append(curr)

        eq_series = pd.Series(equity_curve)

        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
        )

        ax1.plot(eq_series.index, eq_series.values, label="Equity ($)", color="#1f77b4", linewidth=1.5)
        ax1.set_title("Equity Curve & Drawdown", fontsize=14, fontweight="bold")
        ax1.set_ylabel("Account Equity (USD)", fontsize=11)
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend(loc="upper left")

        running_max = eq_series.cummax()
        drawdown_pct = (eq_series - running_max) / running_max * 100.0

        ax2.fill_between(drawdown_pct.index, drawdown_pct.values, 0, color="#d62728", alpha=0.4, label="Drawdown %")
        ax2.plot(drawdown_pct.index, drawdown_pct.values, color="#d62728", linewidth=1.0)
        ax2.set_ylabel("Drawdown (%)", fontsize=11)
        ax2.set_xlabel("Trade / Step Index", fontsize=11)
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend(loc="lower left")

        plt.tight_layout()
        plt.savefig(run_dir / "equity_curve.png", dpi=150)
        plt.close(fig)

    def _save_markdown_summary(
        self,
        run_dir: Path,
        run_id: str,
        m: Dict[str, Any],
        notes: str,
    ) -> None:
        content = f"""# Backtest Report: `{run_id}`

Generated at: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `${m.get('initial_balance', 0):,.2f}` | Boshlang'ich kapital |
| **Yakuniy Equity** | `${m.get('final_equity', 0):,.2f}` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `${m.get('net_profit', 0):,.2f}` (`{m.get('return_pct', 0):+.2f}%`) | Sof natija |
| **Jami Savdolar Soni** | `{m.get('total_trades', 0)}` | {m.get('winning_trades', 0)} yutuq, {m.get('losing_trades', 0)} zarar |
| **Win Rate** | `{m.get('winrate_pct', 0):.2f}%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `{m.get('profit_factor', 0):.2f}` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `{m.get('sharpe_ratio', 0):.2f}` | Risk-adjusted daromad |
| **Sortino Ratio** | `{m.get('sortino_ratio', 0):.2f}` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `{m.get('max_equity_drawdown_pct', 0):.2f}%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `{m.get('recovery_factor', 0):.2f}` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `${m.get('expectancy_usd', 0):,.2f}` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `${m.get('total_spread_cost', 0):,.2f}` |
| **Swap Xarajati** | `${m.get('total_swap_cost', 0):,.2f}` |
| **Komissiya** | `${m.get('total_commission', 0):,.2f}` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `{m.get('avg_duration_hours', 0):.1f}` soat

## Izohlar va Qaydlar
{notes if notes else "_Hech qanday qo'shimcha izoh kiritilmadi._"}

---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
"""
        with open(run_dir / "report.md", "w", encoding="utf-8") as f:
            f.write(content)
