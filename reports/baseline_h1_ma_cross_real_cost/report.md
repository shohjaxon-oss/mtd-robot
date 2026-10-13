# Backtest Report: `baseline_h1_ma_cross_real_cost`

Generated at: 2026-10-13 10:27:54 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,908.62` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,065.74` (`-10.66%`) | Sof natija |
| **Jami Savdolar Soni** | `49` | 12 yutuq, 37 zarar |
| **Win Rate** | `24.49%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.48` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-2.55` | Risk-adjusted daromad |
| **Sortino Ratio** | `-24.62` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `12.09%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.88` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-21.75` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$124.48` |
| **Swap Xarajati** | `$-25.64` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `7.6` soat

## Izohlar va Qaydlar
### Stsenariy Tahlili

- **Timeframe:** H1
- **Xarajatlar:** Real (Dynamic Spread + Slippage + Swap)
- **Holdout:** 20% qulfda (Faqat Train/Dev 80% ishlatildi)

### Monte Carlo Tahlili (1,000 iteratsiya bootstrap)

- **Median DD:** 11.51%
- **95% DD (Worst-case konfidensiya):** 13.27%
- **Eng yomon DD:** 15.11%
- **Ruin Ehtimoli (balans 50% ga tushish):** 0.0%
- **1.0x Xarajatdagi Net PnL:** $-1,065.74
- **1.5x Xarajatdagi Net PnL:** $-1,127.98
- **2.0x Xarajatdagi Net PnL:** $-1,190.22
- **Top 10% yutuqlar olib tashlangandagi PnL:** $-1,436.85


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
