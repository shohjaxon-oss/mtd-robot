# Backtest Report: `exp_hyp02_v2`

Generated at: 2026-10-13 11:16:11 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$5,552.28` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-4,447.72` (`-44.48%`) | Sof natija |
| **Jami Savdolar Soni** | `977` | 313 yutuq, 664 zarar |
| **Win Rate** | `32.04%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.81` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-3.12` | Risk-adjusted daromad |
| **Sortino Ratio** | `-14.25` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `49.12%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.91` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-4.55` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$1,072.26` |
| **Swap Xarajati** | `$-1,485.13` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `32.9` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-02 (VolatilitySqueeze)

- **Parametrlar:** `{'period': 20, 'bb_mult': 2.0, 'kc_mult': 1.75, 'rr_ratio': 2.0, 'atr_sl_mult': 2.0}`
- **Baza PF (1.0x):** 0.81 | **Stress PF (1.5x):** 0.81
- **Long P&L:** $-2,755.83 (519 trades)
- **Short P&L:** $-1,691.89 (458 trades)
- **Ambiguous Barlar:** 4.71%
- **OOS Average PF:** 0.80 | **OOS Sharpe:** -2.33
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
