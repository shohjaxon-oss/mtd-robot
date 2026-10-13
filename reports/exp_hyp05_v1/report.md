# Backtest Report: `exp_hyp05_v1`

Generated at: 2026-10-13 11:57:44 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$9,127.84` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-906.40` (`-9.06%`) | Sof natija |
| **Jami Savdolar Soni** | `398` | 122 yutuq, 276 zarar |
| **Win Rate** | `30.65%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.92` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-0.74` | Risk-adjusted daromad |
| **Sortino Ratio** | `-4.44` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `20.42%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.44` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-2.28` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$233.31` |
| **Swap Xarajati** | `$-1,506.58` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `164.2` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-05 (DonchianTrendH4) [R2 Hisoboti]

- **Parametrlar:** `{'entry_period': 20, 'exit_period': 10, 'atr_sl_mult': 2.0, 'rr_ratio': 2.5}` (Timeframe: `H4`)
- **Gross PF:** 1.11 | **Net PF:** 0.92 | **Stress 1.5x PF:** 0.89
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $2,039.95 (17.8% gross profitdan)
  - Spread: $233.31 | Slippage: $300.06
  - Swap: $-1,506.58 (Long swap: $-1,506.58, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $5.13 | Cost-to-Edge: 1.80
- **Ambiguous Savdolar (SL & TP bir barda):** 0.0% (0 ta)
- **Long P&L:** $-472.64 (229 trades) | **Short P&L:** $-433.76 (169 trades)
- **Yig'ma OOS PF:** 0.97 | **OOS Sharpe:** -0.19 | **Foydali Oynalar:** 25.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
