# Backtest Report: `exp_hyp03_v1`

Generated at: 2026-10-13 11:18:40 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,710.69` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,289.31` (`-12.89%`) | Sof natija |
| **Jami Savdolar Soni** | `438` | 149 yutuq, 289 zarar |
| **Win Rate** | `34.02%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.90` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.01` | Risk-adjusted daromad |
| **Sortino Ratio** | `-9.09` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `18.97%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.68` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-2.94` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$797.66` |
| **Swap Xarajati** | `$-768.73` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `25.2` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-03 (TrendPullback)

- **Parametrlar:** `{'fast_ema': 20, 'slow_ema': 50, 'trend_ema': 200, 'rsi_oversold': 45.0, 'rr_ratio': 2.0, 'atr_sl_mult': 1.5}`
- **Baza PF (1.0x):** 0.90 | **Stress PF (1.5x):** 0.90
- **Long P&L:** $-1,681.74 (244 trades)
- **Short P&L:** $392.43 (194 trades)
- **Ambiguous Barlar:** 8.77%
- **OOS Average PF:** 0.82 | **OOS Sharpe:** -0.34
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
