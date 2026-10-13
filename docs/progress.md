# MTD-ROBOT Loyiha Taraqqiyoti (Progress Tracker)

> **Joriy Bosqich:** 2/10 — Data Layer (Yakunlandi)  
> **Oxirgi yangilanish:** 2026-10-12  
> **Broker / Server:** Exness (`Exness-MT5Trial15`), Demo Standard  
> **Faol Instrument:** `XAUUSDm` (Digits: 3, Point: 0.001)

---

## 10 Bosqichli Reja Holati

| # | Bosqich Nomi | Holat | Gate Holati | Izoh |
|---|---|---|---|---|
| 1 | **Poydevor va spetsifikatsiyani qulflash** | ✅ Yopildi | ✅ O'tdi | Muhit, tuzilma, config, logging, MT5 ulanish, testlar |
| 2 | **Data layer (Tarixiy ma'lumot, sifat, profil)** | ✅ Yopildi | ✅ O'tdi | M1-D1 ma'lumot Parquet'da, sifat hisoboti, spread modeli |
| 3 | Backtest engine va xarajat modeli | 🔄 Keyingi | Kutilmoqda | Event-driven, slippage, spread profili, Monte Carlo |
| 4 | Strategiya tadqiqoti va validatsiya | ⏳ Kutilmoqda | - | 3-5 g'oya, out-of-sample edge tekshiruvi |
| 5 | Signal engine, rejim aniqlash, yangilik filtri | ⏳ Kutilmoqda | - | Real-vaqt signallari, yangilik filtri |
| 6 | Risk engine (eng muhim modul) | ⏳ Kutilmoqda | - | 0.5% risk, kill-switch, lot hisoblash |
| 7 | MQL5 EA ijro qatlami va ko'prik | ⏳ Kutilmoqda | - | Terminal ichidagi himoya qalqoni |
| 8 | Monitoring, logging, ogohlantirish, testlar | ⏳ Kutilmoqda | - | Telegram bot, 48h uzluksiz demo test |
| 9 | Demo forward-test (8-12 hafta) | ⏳ Kutilmoqda | - | Qat'iy parametrlarda real bozor tekshiruvi |
| 10 | Mikro-live, VPS, masshtablash va operatsiya | ⏳ Kutilmoqda | - | Kichik real kapital, runbook, monitoring |

---

## 2/10 Bosqich Bajarilgan Vazifalar

- [x] **1/10 Tuzatishlari:**
  - `mt5_connect.py`: Live tick `ask - bid` asosida real spread hisoblash (pts va USD).
  - Swap rejimi va narxi: 1 lot uchun bir kechalik USD xarajati aniqlandi (Long: -$52.33 / kecha, Short: $0.00 swap-free).
  - Broker `order_calc_margin` va `order_calc_profit` yordamida 1 lot ($208.63) va 0.01 lot ($2.09) margin hamda $1 harakatda $100.00 foyda tekshirildi.
  - `config/symbols.yaml` broker jonli parametrlari bilan to'liq yangilandi.
- [x] **Tarixiy Ma'lumot Chuqurligi Tekshiruvi (`scripts/probe_history.py`):**
  - Exness MT5 server vaqti **aniq UTC+0** ekanligi o'lchandi.
  - Har bir timeframe bo'yicha eng chuqur sanalar o'lchandi va `docs/data_availability.md` hisobotiga yozildi.
- [x] **Tarixiy Ma'lumot Yuklash (`python_brain/data/downloader.py`):**
  - Barcha barlar (D1, H4, H1, M15, M5, M1) Parquet formatida `data/raw/XAUUSDm/<tf>/` ga saqlandi.
  - Jami: D1 (3,922 bar), H4 (16,298 bar), H1 (57,657 bar), M15 (100,001 bar), M5 (100,002 bar), M1 (100,000 bar).
- [x] **Sifat Tekshiruvi (`python_brain/data/quality.py`):**
  - Dublikatlar: 0, tartibsiz: 0, OHLC xatolari: 0.
  - `docs/data_quality.md` hisoboti shakllantirildi.
- [x] **Sessiya va Spread Profili (`python_brain/data/session_profile.py`):**
  - Asia, London, NY, Overlap va Rollover sessiyalari belgilandi.
  - Soatlik va sessiyaviy spread jadvali `docs/spread_profile.md` va `data/processed/*.parquet` ga saqlandi.
- [x] **Iqtisodiy Kalendar:**
  - `mql5_ea/scripts/ExportCalendar.mq5` skripti yozildi.
  - `python_brain/news/calendar_loader.py` yaratildi.
  - MetaEditor uchun qadamma-qadam qo'llanma `docs/runbook.md` ga kiritildi.
- [x] **Testlar:**
  - 28 ta pytest testlari yozildi va 100% yashil o'tdi.

---

## 2/10 Gate Mezonlari

1. **`pytest` hammasi yashil:** ✅ **28/28 test yashil** (`0.38s`).
2. **Haqiqiy raqamlar bilan hujjatlar:** ✅
   - `docs/data_availability.md`
   - `docs/data_quality.md`
   - `docs/spread_profile.md`
   - `docs/decisions.md` (ADR-0005, ADR-0006, ADR-0007)
   - `docs/runbook.md`
3. **M1 va M5 brokerdagi maksimal tarix:** ✅ M1 (100,000 bar), M5 (100,002 bar) to'liq yuklangan va UTC ga o'tkazilgan.
4. **Kalendar CSV va yuklovchi:** ✅ Tayyor.
