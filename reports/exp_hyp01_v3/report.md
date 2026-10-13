# Backtest Report: `exp_hyp01_v3`

Generated at: 2026-10-13 11:12:50 UTC

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
### Gipoteza: HYP-01 (SessionBreakout)

- **Parametrlar:** `{'entry_window_hours': 3, 'rr_ratio': 2.0, 'atr_sl_mult': 2.0}`
- **Baza PF (1.0x):** 0.91 | **Stress PF (1.5x):** 0.91
- **Long P&L:** $-3,158.12 (511 trades)
- **Short P&L:** $666.09 (427 trades)
- **Ambiguous Barlar:** 4.71%
- **OOS Average PF:** 0.92 | **OOS Sharpe:** -0.03
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
