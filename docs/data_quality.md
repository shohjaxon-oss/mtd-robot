# XAUUSDm Ma'lumotlar Sifati Tekshiruvi (Data Quality Audit Report)

> **Broker:** Exness (`Exness-MT5Trial15`)  
> **Tekshiruv Sanasi:** 2026-10-12 13:53:49 UTC  
> **Qoida:** Nol-taxmin va to'liq oshkoralik (hech qanday ma'lumot jimgina tuzatilmadi).  

---

## 1. Sifat Tekshiruvi Xulosasi

| TF | Jami Barlar | Oraliq (UTC) | Dublikatlar | Tartibsiz | Bo'shliqlar | OHLC Xatolari | ATR Sakrashlar | Nol Hajm | Holat |
|---|---|---|---|---|---|---|---|---|---|
| **D1** | 3,922 | 2014-01-14 - 2026-10-12 | 0 | 0 | 23 | 0 | 0 | 0 | ⚠️ OGOHLANTIRISH |
| **H4** | 16,298 | 2014-01-14 - 2026-10-12 | 0 | 0 | 675 | 0 | 0 | 0 | ⚠️ OGOHLANTIRISH |
| **H1** | 57,657 | 2014-01-14 - 2026-10-12 | 0 | 0 | 740 | 0 | 9 | 0 | ⚠️ OGOHLANTIRISH |
| **M15** | 100,001 | 2022-07-18 - 2026-10-12 | 0 | 0 | 37 | 0 | 37 | 0 | ⚠️ OGOHLANTIRISH |
| **M5** | 100,002 | 2025-05-13 - 2026-10-12 | 0 | 0 | 13 | 0 | 14 | 0 | ⚠️ OGOHLANTIRISH |
| **M1** | 100,000 | 2026-07-01 - 2026-10-12 | 0 | 0 | 1 | 0 | 16 | 0 | ⚠️ OGOHLANTIRISH |

---

## 2. Tafsilotlar va Izohlar

### Timeframe: D1
- Found 23 unexpected intra-week data gaps.
- Found 7 bars with spread anomalies (< 0 or > 800.0 pts).

### Timeframe: H4
- Found 675 unexpected intra-week data gaps.
- Found 38 bars with spread anomalies (< 0 or > 800.0 pts).

### Timeframe: H1
- Found 740 unexpected intra-week data gaps.
- Found 9 extreme price spikes exceeding 6.0x ATR.
- Found 171 bars with spread anomalies (< 0 or > 800.0 pts).

### Timeframe: M15
- Found 37 unexpected intra-week data gaps.
- Found 37 extreme price spikes exceeding 6.0x ATR.
- Found 29 bars with spread anomalies (< 0 or > 800.0 pts).

### Timeframe: M5
- Found 13 unexpected intra-week data gaps.
- Found 14 extreme price spikes exceeding 6.0x ATR.
- Found 3 bars with spread anomalies (< 0 or > 800.0 pts).

### Timeframe: M1
- Found 1 unexpected intra-week data gaps.
- Found 16 extreme price spikes exceeding 6.0x ATR.

### Timeframe: M3 (Resampled from M1 & Native Broker M3)
- **M3 Resampled (`data/raw/XAUUSDm/M3/`):** 33,388 bars, 2026-07-01 dan 2026-10-12 gacha. M1 barlaridan UTC ga tekislangan (:00, :03, :06, ...) resample qilingan.
  - Open = first M1 open, High = max M1 high, Low = min M1 low, Close = last M1 close, Volume = sum(tick_volume), Spread = last M1 spread.
  - OHLC xatolari: 0, Dublikatlar: 0.
- **M3 Native Broker (`data/raw/XAUUSDm/M3_broker/`):** 100,000 bars, 2025-12-08 dan 2026-10-13 gacha. Exness MT5 serveri tomonidan `TIMEFRAME_M3` sifatida to'g'ridan-to'g'ri taqdim etilgan.

