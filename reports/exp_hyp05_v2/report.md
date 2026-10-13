# Backtest Report: `exp_hyp05_v2`

Generated at: 2026-10-13 11:58:49 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$9,430.60` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-603.64` (`-6.04%`) | Sof natija |
| **Jami Savdolar Soni** | `353` | 98 yutuq, 255 zarar |
| **Win Rate** | `27.76%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.95` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-0.45` | Risk-adjusted daromad |
| **Sortino Ratio** | `-2.51` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `14.35%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.42` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-1.71` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$215.71` |
| **Swap Xarajati** | `$-1,851.44` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `188.6` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-05 (DonchianTrendH4) [R2 Hisoboti]

- **Parametrlar:** `{'entry_period': 20, 'exit_period': 10, 'atr_sl_mult': 2.0, 'rr_ratio': 3.0}` (Timeframe: `H4`)
- **Gross PF:** 1.17 | **Net PF:** 0.95 | **Stress 1.5x PF:** 0.94
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $2,361.26 (19.9% gross profitdan)
  - Spread: $215.71 | Slippage: $294.12
  - Swap: $-1,851.44 (Long swap: $-1,851.44, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $6.69 | Cost-to-Edge: 1.34
- **Ambiguous Savdolar (SL & TP bir barda):** 0.0% (0 ta)
- **Long P&L:** $99.42 (195 trades) | **Short P&L:** $-703.06 (158 trades)
- **Yig'ma OOS PF:** 0.97 | **OOS Sharpe:** -0.19 | **Foydali Oynalar:** 25.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
