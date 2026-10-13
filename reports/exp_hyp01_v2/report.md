# Backtest Report: `exp_hyp01_v2`

Generated at: 2026-10-13 11:44:08 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$6,658.66` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-3,341.34` (`-33.41%`) | Sof natija |
| **Jami Savdolar Soni** | `1034` | 341 yutuq, 693 zarar |
| **Win Rate** | `32.98%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.89` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.78` | Risk-adjusted daromad |
| **Sortino Ratio** | `-13.39` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `39.82%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.84` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-3.23` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$2,325.90` |
| **Swap Xarajati** | `$-391.95` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `6.7` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-01 (SessionBreakout) [R2 Hisoboti]

- **Parametrlar:** `{'entry_window_hours': 3, 'rr_ratio': 2.0, 'atr_sl_mult': 1.5}` (Timeframe: `H1`)
- **Gross PF:** 1.03 | **Net PF:** 0.89 | **Stress 1.5x PF:** 0.85
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $4,070.34 (14.7% gross profitdan)
  - Spread: $2,325.90 | Slippage: $1,352.48
  - Swap: $-391.95 (Long swap: $-391.95, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $3.94 | Cost-to-Edge: 5.58
- **Ambiguous Savdolar (SL & TP bir barda):** 0.68% (7 ta)
- **Long P&L:** $-2,454.54 (563 trades) | **Short P&L:** $-886.80 (471 trades)
- **Yig'ma OOS PF:** 0.00 | **OOS Sharpe:** 0.00 | **Foydali Oynalar:** 0.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
