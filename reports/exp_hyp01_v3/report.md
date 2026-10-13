# Backtest Report: `exp_hyp01_v3`

Generated at: 2026-10-13 11:44:53 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$7,507.97` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-2,492.03` (`-24.92%`) | Sof natija |
| **Jami Savdolar Soni** | `938` | 313 yutuq, 625 zarar |
| **Win Rate** | `33.37%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.91` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.36` | Risk-adjusted daromad |
| **Sortino Ratio** | `-10.71` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `33.80%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.74` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-2.66` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$1,614.43` |
| **Swap Xarajati** | `$-725.82` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `14.2` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-01 (SessionBreakout) [R2 Hisoboti]

- **Parametrlar:** `{'entry_window_hours': 3, 'rr_ratio': 2.0, 'atr_sl_mult': 2.0}` (Timeframe: `H1`)
- **Gross PF:** 1.03 | **Net PF:** 0.91 | **Stress 1.5x PF:** 0.86
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $3,313.13 (12.7% gross profitdan)
  - Spread: $1,614.43 | Slippage: $972.88
  - Swap: $-725.82 (Long swap: $-725.82, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $3.53 | Cost-to-Edge: 4.04
- **Ambiguous Savdolar (SL & TP bir barda):** 0.53% (5 ta)
- **Long P&L:** $-3,158.12 (511 trades) | **Short P&L:** $666.09 (427 trades)
- **Yig'ma OOS PF:** 0.00 | **OOS Sharpe:** 0.00 | **Foydali Oynalar:** 0.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
