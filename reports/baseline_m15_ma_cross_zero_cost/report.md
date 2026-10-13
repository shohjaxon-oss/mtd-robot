# Backtest Report: `baseline_m15_ma_cross_zero_cost`

Generated at: 2026-10-13 10:28:21 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,787.66` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,212.34` (`-12.12%`) | Sof natija |
| **Jami Savdolar Soni** | `119` | 31 yutuq, 88 zarar |
| **Win Rate** | `26.05%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.70` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.84` | Risk-adjusted daromad |
| **Sortino Ratio** | `-80.65` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `12.12%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-1.00` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-10.19` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$0.00` |
| **Swap Xarajati** | `$0.00` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `1.3` soat

## Izohlar va Qaydlar
### Stsenariy Tahlili

- **Timeframe:** M15
- **Xarajatlar:** Zero Friction (Nazariy Ideal)
- **Holdout:** 20% qulfda (Faqat Train/Dev 80% ishlatildi)

### Monte Carlo Tahlili (1,000 iteratsiya bootstrap)

- **Median DD:** 14.17%
- **95% DD (Worst-case konfidensiya):** 17.22%
- **Eng yomon DD:** 21.50%
- **Ruin Ehtimoli (balans 50% ga tushish):** 0.0%
- **1.0x Xarajatdagi Net PnL:** $-1,212.34
- **1.5x Xarajatdagi Net PnL:** $-1,212.34
- **2.0x Xarajatdagi Net PnL:** $-1,212.34
- **Top 10% yutuqlar olib tashlangandagi PnL:** $-2,251.53


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
