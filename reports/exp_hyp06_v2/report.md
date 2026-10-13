# Backtest Report: `exp_hyp06_v2`

Generated at: 2026-10-13 12:01:03 UTC

## Asosiy Ko'rsatkichlar

| Ko'rsatkich | Qiymat | Izoh |
| :--- | :--- | :--- |
| **Boshlang'ich Balans** | `$10,000.00` | Boshlang'ich kapital |
| **Yakuniy Equity** | `$7,417.12` | Test tugashidagi kapital |
| **Net Foyda / Zarar** | `$-2,582.88` (`-25.83%`) | Sof natija |
| **Jami Savdolar Soni** | `951` | 317 yutuq, 634 zarar |
| **Win Rate** | `33.33%` | Yutuqli savdolar ulushi |
| **Profit Factor** | `0.91` | Yalpi foyda / Yalpi zarar |
| **Sharpe Ratio** | `-1.40` | Risk-adjusted daromad |
| **Sortino Ratio** | `-10.95` | Downside risk-adjusted daromad |
| **Max Drawdown (%)** | `34.09%` | Eng katta nisbiy pasayish |
| **Recovery Factor** | `-0.76` | Net Profit / Max Drawdown |
| **Expectancy ($ / trade)**| `$-2.72` | Har bir savdodan kutilma |

## Xarajatlar Tahlili

| Xarajat Turi | Jami USD |
| :--- | :--- |
| **Spread Xarajati** | `$1,627.94` |
| **Swap Xarajati** | `$-756.17` |
| **Komissiya** | `$0.00` |

## Savdo Xarakteristikalari

- **O'rtacha davomiylik:** `14.2` soat

## Izohlar va Qaydlar
### Gipoteza: HYP-06 (IntradayNoOvernight) [R2 Hisoboti]

- **Parametrlar:** `{'asian_start_hour': 0, 'asian_end_hour': 7, 'entry_window_hours': 3, 'rr_ratio': 2.0, 'atr_sl_mult': 2.0}` (Timeframe: `H1`)
- **Gross PF:** 1.03 | **Net PF:** 0.91 | **Stress 1.5x PF:** 0.86
- **Xarajatlar Dekompozitsiyasi:**
  - Jami xarajatlar: $3,369.85 (12.8% gross profitdan)
  - Spread: $1,627.94 | Slippage: $985.75
  - Swap: $-756.17 (Long swap: $-756.17, Short swap: $0.00)
  - Komissiya: $0.00
  - Savdo boshiga o'rtacha xarajat: $3.54 | Cost-to-Edge: 4.28
- **Ambiguous Savdolar (SL & TP bir barda):** 0.53% (5 ta)
- **Long P&L:** $-3,276.39 (516 trades) | **Short P&L:** $693.51 (435 trades)
- **Yig'ma OOS PF:** 0.00 | **OOS Sharpe:** 0.00 | **Foydali Oynalar:** 0.0%
- **Gate Xulosasi:** GATE REJECTED


---
*Grafik: `equity_curve.png`*  
*Batafsil ma'lumotlar: `trades.csv`, `metrics.json`*
