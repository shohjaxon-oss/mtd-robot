# Backtest Report: `baseline_h1_random_real_cost`

Generated at: 2026-10-13 10:29:15 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,779.87` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,175.13` (`-11.75%`) | Sof natija |
| **Jami Savdolar Soni** | `59` | 21 yutuq, 38 zarar |
| **Win Rate** | `35.59%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.41` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-3.40` | Risk-adjusted daromad |
| **Sortino Ratio** | `-19.54` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `12.20%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.96` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-19.92` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$133.44` |
| **Swap Xarajati** | `$-45.00` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `4.2` soat

## Izohlar va Qaydlar
### Stsenariy Tahlili

- **Timeframe:** H1
- **Xarajatlar:** Real (Dynamic Spread + Slippage + Swap)
- **Holdout:** 20% qulfda (Faqat Train/Dev 80% ishlatildi)

### Monte Carlo Tahlili (1,000 iteratsiya bootstrap)

- **Median DD:** 12.17%
- **95% DD (Worst-case konfidensiya):** 13.40%
- **Eng yomon DD:** 15.15%
- **Ruin Ehtimoli (balans 50% ga tushish):** 0.0%
- **1.0x Xarajatdagi Net PnL:** $-1,175.13
- **1.5x Xarajatdagi Net PnL:** $-1,241.85
- **2.0x Xarajatdagi Net PnL:** $-1,308.57
- **Top 10% yutuqlar olib tashlangandagi PnL:** $-1,402.14


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
