# Backtest Report: `exp_hyp01_v1`

Generated at: 2026-10-13 11:43:22 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,716.71` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,283.29` (`-12.83%`) | Sof natija |
| **Jami Savdolar Soni** | `843` | 347 yutuq, 496 zarar |
| **Win Rate** | `41.16%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.95` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-0.75` | Risk-adjusted daromad |
| **Sortino Ratio** | `-8.00` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `29.07%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.44` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-1.52` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$2,190.96` |
| **Swap Xarajati** | `$-150.19` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `4.7` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-01 (SessionBreakout) [R2 Hisoboti]

- **Parametrlar:** `{'entry_window_hours': 2, 'rr_ratio': 1.5, 'atr_sl_mult': 1.5}` (Timeframe: `H1`)
- **Gross PF:** 1.10 | **Net PF:** 0.95 | **Stress 1.5x PF:** 0.90
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $3,445.79 (14.0% gross profitdan)
  - Spread: $2,190.96 | Slippage: $1,104.64
  - Swap: $-150.19 (Long swap: $-150.19, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $4.09 | Cost-to-Edge: 1.59
- **Ambiguous Savdolar (SL & TP bir barda):** 0.71% (6 ta)
- **Long P&L:** $-1,676.85 (457 trades) | **Short P&L:** $393.56 (386 trades)
- **Yig'ma OOS PF:** 0.88 | **OOS Sharpe:** -1.27 | **Foydali Oynalar:** 22.22%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
