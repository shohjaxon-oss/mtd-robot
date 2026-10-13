# Backtest Report: `exp_hyp01_v2`

Generated at: 2026-10-13 11:11:06 UTC

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
### Gipoteza: HYP-01 (SessionBreakout)

- **Parametrlar:** `{'entry_window_hours': 3, 'rr_ratio': 2.0, 'atr_sl_mult': 1.5}`
- **Baza PF (1.0x):** 0.89 | **Stress PF (1.5x):** 0.89
- **Long P&L:** $-2,454.54 (563 trades)
- **Short P&L:** $-886.80 (471 trades)
- **Ambiguous Barlar:** 8.77%
- **OOS Average PF:** 0.83 | **OOS Sharpe:** -0.34
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
