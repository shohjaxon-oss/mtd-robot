# Backtest Report: `exp_hyp07_v2`

Generated at: 2026-10-13 12:05:07 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$8,434.29` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-1,565.71` (`-15.66%`) | Sof natija |
| **Jami Savdolar Soni** | `563` | 156 yutuq, 407 zarar |
| **Win Rate** | `27.71%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.91` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-0.98` | Risk-adjusted daromad |
| **Sortino Ratio** | `-9.13` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `22.89%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.68` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-2.78` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$793.54` |
| **Swap Xarajati** | `$0.00` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `47.1` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-07 (ShortOnlyTrendPullback) [R2 Hisoboti]

- **Parametrlar:** `{'fast_ema': 20, 'slow_ema': 50, 'trend_ema': 200, 'rsi_overbought': 50.0, 'rr_ratio': 2.5, 'atr_sl_mult': 2.0}` (Timeframe: `H1`)
- **Gross PF:** 0.99 | **Net PF:** 0.91 | **Stress 1.5x PF:** 0.89
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $1,355.68 (8.2% gross profitdan)
  - Spread: $793.54 | Slippage: $562.14
  - Swap: $0.00 (Long swap: $0.00, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $2.41 | Cost-to-Edge: 999.00
- **Ambiguous Savdolar (SL & TP bir barda):** 0.18% (1 ta)
- **Long P&L:** $0.00 (0 trades) | **Short P&L:** $-1,565.71 (563 trades)
- **Yig'ma OOS PF:** 0.00 | **OOS Sharpe:** 0.00 | **Foydali Oynalar:** 0.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
