# Backtest Report: `baseline_m15_ma_cross_real_cost`

Generated at: 2026-10-13 10:28:48 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,782.46` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,202.36` (`-12.02%`) | Sof natija |
| **Jami Savdolar Soni** | `37` | 5 yutuq, 32 zarar |
| **Win Rate** | `13.51%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.26` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-4.23` | Risk-adjusted daromad |
| **Sortino Ratio** | `-59.87` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `12.18%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.99` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-32.50` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$173.92` |
| **Swap Xarajati** | `$-15.18` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `0.4` soat

## Izohlar va Qaydlar
### Stsenariy Tahlili

- **Timeframe:** M15
- **Xarajatlar:** Real (Dynamic Spread + Slippage + Swap)
- **Holdout:** 20% qulfda (Faqat Train/Dev 80% ishlatildi)

### Monte Carlo Tahlili (1,000 iteratsiya bootstrap)

- **Median DD:** 12.26%
- **95% DD (Worst-case konfidensiya):** 13.62%
- **Eng yomon DD:** 14.97%
- **Ruin Ehtimoli (balans 50% ga tushish):** 0.0%
- **1.0x Xarajatdagi Net PnL:** $-1,202.36
- **1.5x Xarajatdagi Net PnL:** $-1,289.32
- **2.0x Xarajatdagi Net PnL:** $-1,376.28
- **Top 10% yutuqlar olib tashlangandagi PnL:** $-1,468.87


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
