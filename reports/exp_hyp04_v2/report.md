# Backtest Report: `exp_hyp04_v2`

Generated at: 2026-10-13 11:24:45 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$9,582.26` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-417.74` (`-4.18%`) | Sof natija |
| **Jami Savdolar Soni** | `51` | 30 yutuq, 21 zarar |
| **Win Rate** | `58.82%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.64` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.37` | Risk-adjusted daromad |
| **Sortino Ratio** | `-2.71` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `5.69%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.73` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-8.19` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$84.59` |
| **Swap Xarajati** | `$-32.97` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `11.6` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-04 (MeanReversion)

- **Parametrlar:** `{'bb_period': 20, 'bb_std': 2.5, 'adx_max': 22.0, 'atr_sl_mult': 1.5}`
- **Baza PF (1.0x):** 0.64 | **Stress PF (1.5x):** 0.64
- **Long P&L:** $-60.01 (21 trades)
- **Short P&L:** $-357.73 (30 trades)
- **Ambiguous Barlar:** 8.77%
- **OOS Average PF:** 333.28 | **OOS Sharpe:** -7.14
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
