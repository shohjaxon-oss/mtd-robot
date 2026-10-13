# Backtest Report: `exp_hyp02_v2`

Generated at: 2026-10-13 11:47:56 UTC

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
### Gipoteza: HYP-02 (VolatilitySqueeze) [R2 Hisoboti]

- **Parametrlar:** `{'period': 20, 'bb_mult': 2.0, 'kc_mult': 1.75, 'rr_ratio': 2.0, 'atr_sl_mult': 2.0}` (Timeframe: `H1`)
- **Gross PF:** 0.94 | **Net PF:** 0.81 | **Stress 1.5x PF:** 0.78
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $3,252.70 (16.6% gross profitdan)
  - Spread: $1,072.26 | Slippage: $695.32
  - Swap: $-1,485.13 (Long swap: $-1,485.13, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $3.33 | Cost-to-Edge: 999.00
- **Ambiguous Savdolar (SL & TP bir barda):** 0.2% (2 ta)
- **Long P&L:** $-2,755.83 (519 trades) | **Short P&L:** $-1,691.89 (458 trades)
- **Yig'ma OOS PF:** 0.00 | **OOS Sharpe:** 0.00 | **Foydali Oynalar:** 0.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
