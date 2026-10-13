# Backtest Report: `exp_hyp02_v1`

Generated at: 2026-10-13 11:14:27 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$7,546.07` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-2,453.93` (`-24.54%`) | Sof natija |
| **Jami Savdolar Soni** | `906` | 309 yutuq, 597 zarar |
| **Win Rate** | `34.11%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.90` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.45` | Risk-adjusted daromad |
| **Sortino Ratio** | `-9.04` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `36.74%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.67` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-2.71` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$1,571.28` |
| **Swap Xarajati** | `$-1,261.68` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `19.8` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-02 (VolatilitySqueeze)

- **Parametrlar:** `{'period': 20, 'bb_mult': 2.0, 'kc_mult': 1.5, 'rr_ratio': 2.0, 'atr_sl_mult': 1.5}`
- **Baza PF (1.0x):** 0.90 | **Stress PF (1.5x):** 0.90
- **Long P&L:** $-2,091.79 (482 trades)
- **Short P&L:** $-362.14 (424 trades)
- **Ambiguous Barlar:** 8.77%
- **OOS Average PF:** 0.92 | **OOS Sharpe:** -1.86
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
