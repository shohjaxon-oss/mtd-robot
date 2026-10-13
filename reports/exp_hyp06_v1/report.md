# Backtest Report: `exp_hyp06_v1`

Generated at: 2026-10-13 11:59:52 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$6,579.81` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-3,420.19` (`-34.20%`) | Sof natija |
| **Jami Savdolar Soni** | `1101` | 434 yutuq, 667 zarar |
| **Win Rate** | `39.42%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.89` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.96` | Risk-adjusted daromad |
| **Sortino Ratio** | `-13.95` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `40.36%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.85` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-3.11` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$2,553.79` |
| **Swap Xarajati** | `$-182.11` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `4.8` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-06 (IntradayNoOvernight) [R2 Hisoboti]

- **Parametrlar:** `{'asian_start_hour': 0, 'asian_end_hour': 7, 'entry_window_hours': 3, 'rr_ratio': 1.5, 'atr_sl_mult': 1.5}` (Timeframe: `H1`)
- **Gross PF:** 1.02 | **Net PF:** 0.89 | **Stress 1.5x PF:** 0.84
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $4,070.95 (14.7% gross profitdan)
  - Spread: $2,553.79 | Slippage: $1,335.05
  - Swap: $-182.11 (Long swap: $-182.11, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $3.70 | Cost-to-Edge: 6.26
- **Ambiguous Savdolar (SL & TP bir barda):** 1.09% (12 ta)
- **Long P&L:** $-2,746.24 (595 trades) | **Short P&L:** $-673.95 (506 trades)
- **Yig'ma OOS PF:** 0.00 | **OOS Sharpe:** 0.00 | **Foydali Oynalar:** 0.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
