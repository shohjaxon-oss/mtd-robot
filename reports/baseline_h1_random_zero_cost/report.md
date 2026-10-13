# Backtest Report: `baseline_h1_random_zero_cost`

Generated at: 2026-10-13 10:29:02 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,787.43` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,212.57` (`-12.13%`) | Sof natija |
| **Jami Savdolar Soni** | `90` | 32 yutuq, 58 zarar |
| **Win Rate** | `35.56%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.54` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-2.98` | Risk-adjusted daromad |
| **Sortino Ratio** | `-39.51` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `12.13%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-1.00` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-13.47` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$0.00` |
| **Swap Xarajati** | `$0.00` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `5.4` soat

## Izohlar va Qaydlar
### Stsenariy Tahlili

- **Timeframe:** H1
- **Xarajatlar:** Zero Friction (Nazariy Ideal)
- **Holdout:** 20% qulfda (Faqat Train/Dev 80% ishlatildi)

### Monte Carlo Tahlili (1,000 iteratsiya bootstrap)

- **Median DD:** 12.94%
- **95% DD (Worst-case konfidensiya):** 14.40%
- **Eng yomon DD:** 15.96%
- **Ruin Ehtimoli (balans 50% ga tushish):** 0.0%
- **1.0x Xarajatdagi Net PnL:** $-1,212.57
- **1.5x Xarajatdagi Net PnL:** $-1,212.57
- **2.0x Xarajatdagi Net PnL:** $-1,212.57
- **Top 10% yutuqlar olib tashlangandagi PnL:** $-1,637.24


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
