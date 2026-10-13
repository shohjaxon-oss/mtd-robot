# Backtest Report: `exp_hyp03_v2`

Generated at: 2026-10-13 11:21:09 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$9,230.01` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-769.99` (`-7.70%`) | Sof natija |
| **Jami Savdolar Soni** | `340` | 101 yutuq, 239 zarar |
| **Win Rate** | `29.71%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.93` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-0.59` | Risk-adjusted daromad |
| **Sortino Ratio** | `-5.50` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `12.99%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.59` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-2.26` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$483.07` |
| **Swap Xarajati** | `$-692.33` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `44.6` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-03 (TrendPullback)

- **Parametrlar:** `{'fast_ema': 20, 'slow_ema': 50, 'trend_ema': 200, 'rsi_oversold': 40.0, 'rr_ratio': 2.5, 'atr_sl_mult': 2.0}`
- **Baza PF (1.0x):** 0.93 | **Stress PF (1.5x):** 0.93
- **Long P&L:** $-1,446.21 (166 trades)
- **Short P&L:** $676.22 (174 trades)
- **Ambiguous Barlar:** 3.08%
- **OOS Average PF:** 0.83 | **OOS Sharpe:** -0.30
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
