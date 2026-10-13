# Backtest Report: `exp_hyp04_v1`

Generated at: 2026-10-13 11:23:01 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$9,318.47` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-681.53` (`-6.82%`) | Sof natija |
| **Jami Savdolar Soni** | `120` | 66 yutuq, 54 zarar |
| **Win Rate** | `55.00%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.76` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.36` | Risk-adjusted daromad |
| **Sortino Ratio** | `-3.50` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `8.76%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.78` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-5.68` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$276.72` |
| **Swap Xarajati** | `$-97.86` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `7.9` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-04 (MeanReversion)

- **Parametrlar:** `{'bb_period': 20, 'bb_std': 2.2, 'adx_max': 20.0, 'atr_sl_mult': 1.2}`
- **Baza PF (1.0x):** 0.76 | **Stress PF (1.5x):** 0.76
- **Long P&L:** $-312.61 (46 trades)
- **Short P&L:** $-368.92 (74 trades)
- **Ambiguous Barlar:** 13.85%
- **OOS Average PF:** 111.53 | **OOS Sharpe:** -0.08
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
