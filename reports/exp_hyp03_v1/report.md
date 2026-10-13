# Backtest Report: `exp_hyp03_v1`

Generated at: 2026-10-13 11:51:22 UTC

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
### Gipoteza: HYP-03 (TrendPullback) [R2 Hisoboti]

- **Parametrlar:** `{'fast_ema': 20, 'slow_ema': 50, 'trend_ema': 200, 'rsi_oversold': 45.0, 'rr_ratio': 2.0, 'atr_sl_mult': 1.5}` (Timeframe: `H1`)
- **Gross PF:** 1.06 | **Net PF:** 0.90 | **Stress 1.5x PF:** 0.87
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $2,058.96 (16.2% gross profitdan)
  - Spread: $797.66 | Slippage: $492.57
  - Swap: $-768.73 (Long swap: $-768.73, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $4.70 | Cost-to-Edge: 2.68
- **Ambiguous Savdolar (SL & TP bir barda):** 0.23% (1 ta)
- **Long P&L:** $-1,681.74 (244 trades) | **Short P&L:** $392.43 (194 trades)
- **Yig'ma OOS PF:** 0.80 | **OOS Sharpe:** -1.36 | **Foydali Oynalar:** 22.22%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
