"""Monte Carlo Tahlil Moduli.

Strategiya barqarorligini va xatarlarni tekshirish:
1. Trade Reshuffle (Permutation Bootstrap): Savdolar ketma-ketligini aralashtirib Max DD taqsimotini hisoblash (5%, 50%, 95%).
2. Friksiya Stress Testi: Xarajatlarni 1.0x, 1.5x, 2.0x ga oshirib ko'rish.
3. Tasodifiy savdolarni tashlash: 10% eng yaxshi yutuqlarni olib tashlaganda omon qolish qobiliyati.
4. Risk of Ruin ehtimoli (balans 50% ga tushish ehtimoli).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List
import numpy as np
from loguru import logger

from python_brain.backtest.models import Position


@dataclass
class MonteCarloResult:
    iterations: int
    dd_p5: float          # 5-percentil DD
    dd_p50: float         # Median DD
    dd_p95: float         # 95-percentil DD
    dd_worst: float       # Eng yomon DD
    ruin_probability: float  # Balans 50% tushish ehtimoli
    cost_stress_1_0x: float # 1.0x xarajatdagi Net PnL
    cost_stress_1_5x: float # 1.5x xarajatdagi Net PnL
    cost_stress_2_0x: float # 2.0x xarajatdagi Net PnL
    drop_10pct_wins_pnl: float # 10% eng yaxshi yutuqlar olib tashlangandagi PnL


class MonteCarloEngine:
    def __init__(self, initial_balance: float = 10000.0) -> None:
        self.initial_balance = initial_balance

    def analyze(
        self,
        trades: List[Position],
        iterations: int = 1000,
        random_seed: int = 42,
    ) -> MonteCarloResult:
        if not trades:
            return MonteCarloResult(
                iterations=0,
                dd_p5=0.0,
                dd_p50=0.0,
                dd_p95=0.0,
                dd_worst=0.0,
                ruin_probability=0.0,
                cost_stress_1_0x=0.0,
                cost_stress_1_5x=0.0,
                cost_stress_2_0x=0.0,
                drop_10pct_wins_pnl=0.0,
            )

        rng = np.random.default_rng(random_seed)
        net_pnls = np.array([p.realized_pnl for p in trades], dtype=np.float64)
        total_trades = len(net_pnls)

        # 1. Trade Reshuffle (Bootstrap / Permutation)
        max_drawdowns_pct = []
        ruin_count = 0
        ruin_threshold = self.initial_balance * 0.5

        for _ in range(iterations):
            shuffled_pnl = rng.permutation(net_pnls)
            equity_curve = self.initial_balance + np.cumsum(shuffled_pnl)
            equity_with_start = np.insert(equity_curve, 0, self.initial_balance)

            running_max = np.maximum.accumulate(equity_with_start)
            drawdowns = (running_max - equity_with_start) / running_max * 100.0
            max_dd = np.max(drawdowns)
            max_drawdowns_pct.append(max_dd)

            if np.min(equity_with_start) <= ruin_threshold:
                ruin_count += 1

        dd_p5 = float(np.percentile(max_drawdowns_pct, 5))
        dd_p50 = float(np.percentile(max_drawdowns_pct, 50))
        dd_p95 = float(np.percentile(max_drawdowns_pct, 95))
        dd_worst = float(np.max(max_drawdowns_pct))
        ruin_prob = float(ruin_count / iterations * 100.0)

        # 2. Xarajat Stress Testi (1.0x, 1.5x, 2.0x)
        # realized_pnl = gross_pnl + accumulated_swap - commission
        # Friction = spread_cost + slippage_cost + commission
        spread_costs = np.array([p.spread_cost for p in trades], dtype=np.float64)
        slippage_costs = np.array([p.slippage_cost for p in trades], dtype=np.float64)
        commissions = np.array([p.commission for p in trades], dtype=np.float64)
        swaps = np.array([p.accumulated_swap for p in trades], dtype=np.float64)

        base_friction = spread_costs + slippage_costs + commissions
        # gross_pnl = net_pnl + base_friction - swaps
        gross_pnls = net_pnls + base_friction - swaps

        cost_1_0x = float(np.sum(gross_pnls - (base_friction * 1.0) + swaps))
        cost_1_5x = float(np.sum(gross_pnls - (base_friction * 1.5) + swaps))
        cost_2_0x = float(np.sum(gross_pnls - (base_friction * 2.0) + swaps))

        # 3. Yutuqli savdolarning eng yaxshi 10% ini olib tashlash stress testi
        sorted_pnls = np.sort(net_pnls)
        drop_count = max(1, int(total_trades * 0.10))
        pnls_without_top_10 = sorted_pnls[:-drop_count]
        drop_10pct_pnl = float(np.sum(pnls_without_top_10))

        logger.info(
            f"Monte Carlo ({iterations} iters): Median DD={dd_p50:.2f}%, "
            f"95% DD={dd_p95:.2f}%, Ruin Prob={ruin_prob:.1f}%, "
            f"Cost Stress (1x/1.5x/2x)=${cost_1_0x:.1f}/${cost_1_5x:.1f}/${cost_2_0x:.1f}"
        )

        return MonteCarloResult(
            iterations=iterations,
            dd_p5=dd_p5,
            dd_p50=dd_p50,
            dd_p95=dd_p95,
            dd_worst=dd_worst,
            ruin_probability=ruin_prob,
            cost_stress_1_0x=cost_1_0x,
            cost_stress_1_5x=cost_1_5x,
            cost_stress_2_0x=cost_2_0x,
            drop_10pct_wins_pnl=drop_10pct_pnl,
        )
