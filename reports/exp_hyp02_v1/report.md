# Backtest Report: `exp_hyp02_v1`

Generated at: 2026-10-13 11:47:09 UTC

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
### Gipoteza: HYP-02 (VolatilitySqueeze) [R2 Hisoboti]

- **Parametrlar:** `{'period': 20, 'bb_mult': 2.0, 'kc_mult': 1.5, 'rr_ratio': 2.0, 'atr_sl_mult': 1.5}` (Timeframe: `H1`)
- **Gross PF:** 1.06 | **Net PF:** 0.90 | **Stress 1.5x PF:** 0.87
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $3,818.91 (15.9% gross profitdan)
  - Spread: $1,571.28 | Slippage: $985.96
  - Swap: $-1,261.68 (Long swap: $-1,261.68, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $4.22 | Cost-to-Edge: 2.80
- **Ambiguous Savdolar (SL & TP bir barda):** 0.66% (6 ta)
- **Long P&L:** $-2,091.79 (482 trades) | **Short P&L:** $-362.14 (424 trades)
- **Yig'ma OOS PF:** 0.94 | **OOS Sharpe:** -0.65 | **Foydali Oynalar:** 33.33%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
