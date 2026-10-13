# MTD-ROBOT Loyiha Taraqqiyoti (Progress Tracker)

> **Joriy Bosqich:** 3/10 — Backtest Engine va Xarajat Modeli (Yakunlandi)  
> **Oxirgi yangilanish:** 2026-10-13  
> **Broker / Server:** Exness (`Exness-MT5Trial15`), Demo Standard  
> **Faol Instrument:** `XAUUSDm` (Digits: 3, Point: 0.001)

---

## 10 Bosqichli Reja Holati

| # | Bosqich Nomi | Holat | Gate Holati | Izoh |
|---|---|---|---|---|
| 1 | **Poydevor va spetsifikatsiyani qulflash** | ✅ Yopildi | ✅ O'tdi | Muhit, tuzilma, config, logging, MT5 ulanish, testlar |
| 2 | **Data layer (Tarixiy ma'lumot, sifat, profil)** | ✅ Yopildi | ✅ O'tdi | M1-D1 ma'lumot Parquet'da, sifat hisoboti, spread modeli |
| 3 | **Backtest engine va xarajat modeli** | ✅ Yopildi | ✅ O'tdi | Event-driven, Bid/Ask, SL-first, Monte Carlo, Holdout qulfi, WFO |
| 4 | Strategiya tadqiqoti va validatsiya | 🔄 Keyingi | Kutilmoqda | 3-5 g'oya, out-of-sample edge tekshiruvi |
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

## 3/10 Bosqich Bajarilgan Vazifalar
- [x] **A Bandi: Tarix chegarasi va arxivator:**
  - `downloader.py` da hech qanday qattiq chegara (`count=100000`) yo'qligi tekshirildi va tasdiqlandi.
  - To'g'ridan-to'g'ri `copy_rates_range` so'rovi bilan broker serverida eski M1/M5 tarixi yo'qligi isbotlandi (0 bar qaytdi).
  - ADR-0007 yangilandi.
  - `scripts/archive_recent.py` yozildi va sinovdan o'tkazildi (+50k M1 bar, +1.15M tick arxivlandi).
  - `docs/runbook.md` ga Windows Task Scheduler orqali haftalik avto-arxivlash yo'riqnomasi kiritildi.
- [x] **B Bandi: Backtest Engine arxitekturasi:**
  - Event-driven arxitektura (`engine.py`, `models.py`): Zero-Lookahead (Signal bar t close -> Execution bar t+1 open).
  - Bid/Ask narxlar modeli: Buy ochilishi Ask da, yopilishi Bid da; Sell ochilishi Bid da, yopilishi Ask da.
  - Konservativ intrabar to'qnashuv: bitta bar ichida ham SL, ham TP tegsa, har doim SL birinchi ijro etiladi.
  - Stop-Out mexanikasi: 20% margin levelda barcha ochiq pozitsiyalar yopiladi.
- [x] **C Bandi: Xarajatlar modeli (`costs.py`):**
  - Soatlik va sessiyaviy spread profili (median va p95).
  - Rollover (21:00-22:00 UTC) va news blackout davrida kengayish.
  - Stop-Loss ijrosiga dinamik slippage (spread va ATR ga mutanosib).
  - Overnight swap: Long (-52.33 USD/lot), Short (0.0 USD), Payshanba kechasi 3x swap.
- [x] **D Bandi: Xavfsizlik va RiskGate (`risk_gate.py`):**
  - Majburiy Stop-Loss (SL siz orderlar rad etiladi).
  - 0.5% risk kapitali bo'yicha dinamik lot o'lchami.
  - Kunlik (-2.0%) va haftalik (-4.0%) zarar bloklari.
  - Kill-switch: -12.0% equity drawdown yetganda yangi orderlar to'xtatiladi.
- [x] **E Bandi: Overfittingga qarshi himoya:**
  - Holdout qulfi (`holdout.py`): har bir timeframe uchun oxirgi 20% qulflangan, audit jurnali `docs/holdout_log.md` ga yoziladi.
  - Monte Carlo Engine (`montecarlo.py`): 1000 iteratsiya bootstrap reshuffle, Median DD, 95% DD, Ruin ehtimoli, cost stress (1.0x, 1.5x, 2.0x), 10% eng yaxshi yutuqlarni olib tashlash.
  - Walk-Forward Splitter va Analyzer (`walkforward.py`): H1 (18 ta rolling oyna), M15.
- [x] **F Bandi: Baseline va Hisobotlar (`reporter.py`, `scripts/run_baseline_backtest.py`):**
  - MA Crossover va Random Entry (H1 va M15, Zero Cost va Real Cost).
  - `reports/<run_id>/` da `trades.csv`, `metrics.json`, `report.md`, `equity_curve.png`, `config_snapshot.json` yaratildi.
  - 41 ta to'liq avtomatik pytest testlari (100% yashil).

---

## 3/10 Gate Mezonlari

1. **`pytest` barcha testlar yashil:** ✅ **41/41 test yashil** (`1.14s`).
2. **Zero-lookahead qat'iy isboti:** ✅ Testlangan (`test_zero_lookahead_execution`).
3. **Konservativ intrabar ziddiyat:** ✅ Testlangan (`test_intrabar_conservative_sl_tp`).
4. **Haqiqiy xarajatlar va stress-test:** ✅ Empirik profil, 3x swap, Monte Carlo 1.5x/2.0x stress.
5. **Holdout qulfi mavjud:** ✅ Oxirgi 20% qulflangan, `docs/holdout_log.md` audit jurnali sozlangan.
6. **Baseline hisobotlari:** ✅ `reports/` katalogida barcha 6 ta eksperiment hisoboti to'liq mavjud.

