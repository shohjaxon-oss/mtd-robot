# XAUUSDm Tarixiy Ma'lumot Chuqurligi Hisoboti (Data Availability Report)

> **Broker:** Exness (Exness-MT5Trial15)  
> **Hisob turi:** Standard Demo (`XAUUSDm`)  
> **O'lchov Sanasi:** 2026-10-13 10:05:57 UTC  
> **Server Vaqti / UTC Siljishi:** **0.0 soat (UTC+0)**. Exness MT5 serveri to'g'ridan-to'g'ri haqiqiy UTC vaqtida ishlaydi.  

---

## 1. Timeframe'lar Bo'yicha Haqiqiy Bar Chuqurligi

| Timeframe | Eng Eski Bar (UTC) | Eng Yangi Bar (UTC) | Davr (Kun) | Davr (Yil) | 5+ Yillik Talab |
|---|---|---|---|---|---|
| **D1** | 2014-01-14 00:00:00 UTC | 2026-10-13 00:00:00 UTC | 4655 kun | 12.74 yil | **YES (>= 5y)** |
| **H4** | 2014-01-14 00:00:00 UTC | 2026-10-13 08:00:00 UTC | 4655 kun | 12.74 yil | **YES (>= 5y)** |
| **H1** | 2014-01-14 00:00:00 UTC | 2026-10-13 10:00:00 UTC | 4655 kun | 12.74 yil | **YES (>= 5y)** |
| **M15** | 2022-07-19 00:15:00 UTC | 2026-10-13 10:00:00 UTC | 1547 kun | 4.24 yil | **NO (4.24y < 5y)** |
| **M5** | 2025-05-14 19:05:00 UTC | 2026-10-13 10:05:00 UTC | 516 kun | 1.41 yil | **NO (1.41y < 5y)** |
| **M1** | 2026-07-01 17:00:00 UTC | 2026-10-13 10:05:00 UTC | 103 kun | 0.28 yil | **NO (0.28y < 5y)** |

---

## 2. Tick Ma'lumotlari Chuqurligi (`copy_ticks_range`)

| Gorizont | Sinov Sanasi | Topilgan Ticklar (1 soatlik oyna) | Holat |
|---|---|---|---|
| **1_day** | 2026-10-12 | 6182 tick | Available |
| **7_days** | 2026-10-06 | 7331 tick | Available |
| **30_days** | 2026-09-13 | 0 tick | Not available |
| **90_days** | 2026-07-15 | 8936 tick | Available |
| **180_days** | 2026-04-16 | 7173 tick | Available |
| **365_days** | 2025-10-13 | 0 tick | Not available |
| **730_days** | 2024-10-13 | 0 tick | Not available |

---

## 3. Halol Quant Tahlili va Xulosalar

1. **Makro va Rejim (D1, H4, H1):** Brokerda 12.74 yillik (D1) va 12.74 yillik (H1) boy tarix mavjud. Bu bozor rejimi (regime detection), uzoq muddatli trend va volatillikni o'rganish uchun yetarli.
2. **Intraday va Bajarish (M1, M5):**
   - **M5:** Broker serverida 1.41 yillik tarix mavjud (2025-05-14 19:05:00 UTC dan boshlab).
   - **M1:** Broker serverida 0.28 yillik tarix mavjud (2026-07-01 17:00:00 UTC dan boshlab).
3. **MUAMMO VA SABAB:** Exness serveri M1 daqiqalik barlarni 0.28 yildan ortiq saqlamaydi (bu barcha retail MT5 brokerlarida saqlash hajmi cheklovi tufayli odatiy holat). 5 yillik M1 talabi brokerning o'zida jismonan mavjud emas.
4. **Kvant Strategiya Yechimi:**
   - 1-bosqich: M5 bo'yicha brokerning to'liq mavjud tarixidan (1.41 yil) foydalanish.
   - 2-bosqich: M1 bo'yicha mavjud 0.28 yillik to'liq barlarni yuklash.
   - 3-bosqich (Qo'shimcha): Agar 5 yillik M1 shart bo'lsa, Dukascopy XAUUSD M1 tarixini alohida `data/raw/dukascopy/` ga yuklash moduli qo'shiladi va broker ma'lumotiga aralashtirmasdan taqqoslanadi.
