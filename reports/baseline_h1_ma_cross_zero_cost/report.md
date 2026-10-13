# Backtest Report: `baseline_h1_ma_cross_zero_cost`

Generated at: 2026-10-13 10:27:37 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,888.01` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,111.99` (`-11.12%`) | Sof natija |
| **Jami Savdolar Soni** | `119` | 32 yutuq, 87 zarar |
| **Win Rate** | `26.89%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.72` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.69` | Risk-adjusted daromad |
| **Sortino Ratio** | `-66.84` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `12.37%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.90` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-9.34` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$0.00` |
| **Swap Xarajati** | `$0.00` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `10.3` soat

## Izohlar va Qaydlar
### Stsenariy Tahlili

- **Timeframe:** H1
- **Xarajatlar:** Zero Friction (Nazariy Ideal)
- **Holdout:** 20% qulfda (Faqat Train/Dev 80% ishlatildi)

### Monte Carlo Tahlili (1,000 iteratsiya bootstrap)

- **Median DD:** 13.46%
- **95% DD (Worst-case konfidensiya):** 16.44%
- **Eng yomon DD:** 20.21%
- **Ruin Ehtimoli (balans 50% ga tushish):** 0.0%
- **1.0x Xarajatdagi Net PnL:** $-1,111.99
- **1.5x Xarajatdagi Net PnL:** $-1,111.99
- **2.0x Xarajatdagi Net PnL:** $-1,111.99
- **Top 10% yutuqlar olib tashlangandagi PnL:** $-2,139.20


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
