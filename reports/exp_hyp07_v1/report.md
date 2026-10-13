# Backtest Report: `exp_hyp07_v1`

Generated at: 2026-10-13 12:03:12 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$6,610.02` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-3,389.98` (`-33.90%`) | Sof natija |
| **Jami Savdolar Soni** | `845` | 262 yutuq, 583 zarar |
| **Win Rate** | `31.01%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.86` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-2.07` | Risk-adjusted daromad |
| **Sortino Ratio** | `-17.82` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `38.05%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.89` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-4.01` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$1,510.93` |
| **Swap Xarajati** | `$0.00` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `22.7` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-07 (ShortOnlyTrendPullback) [R2 Hisoboti]

- **Parametrlar:** `{'fast_ema': 20, 'slow_ema': 50, 'trend_ema': 200, 'rsi_overbought': 55.0, 'rr_ratio': 2.0, 'atr_sl_mult': 1.5}` (Timeframe: `H1`)
- **Gross PF:** 0.96 | **Net PF:** 0.86 | **Stress 1.5x PF:** 0.83
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $2,501.57 (11.8% gross profitdan)
  - Spread: $1,510.93 | Slippage: $990.64
  - Swap: $0.00 (Long swap: $0.00, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $2.96 | Cost-to-Edge: 999.00
- **Ambiguous Savdolar (SL & TP bir barda):** 0.83% (7 ta)
- **Long P&L:** $0.00 (0 trades) | **Short P&L:** $-3,389.98 (845 trades)
- **Yig'ma OOS PF:** 0.00 | **OOS Sharpe:** 0.00 | **Foydali Oynalar:** 0.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
