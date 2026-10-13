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
| 3 | **Backtest engine va xarajat modeli** | ✅ Yopildi | ✅ O'tdi | Event-driven, A1-A12 audit tuzatishlari, 47/47 test |
| 4 | **Strategiya tadqiqoti va validatsiya** | ✅ Yopildi | ⚠️ Rad etildi (Halol) | 4 oila sinaldi, xarajatlar ostida edge topilmadi, Holdout qulfda |
| 5 | **Signal engine, rejim aniqlash, yangilik filtri** | 🔄 Keyingi | Kutilmoqda | Yangi gipotezalar (intraday/short-bias), rejim detektorlari |
| 6 | **Risk engine (eng muhim modul)** | ✅ Yopildi (Demo) | ✅ O'tdi | SQLite persistent state, kill-switch reset, 12 ta xavfsizlik cheklovi |
| 7 | **MQL5 EA ijro qatlami va ko'prik** | ✅ Yopildi (Demo) | ✅ O'tdi | Server SL/TP, idempotentlik, DLL-siz MTD_Guardian.mq5 |
| 8 | **Monitoring, logging, ogohlantirish, testlar** | ✅ Yopildi (Demo) | ✅ O'tdi | LiveRunner, Telegram, Watchdog, Dry-run, 87/87 test |
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

1. **`pytest` barcha testlar yashil:** ✅ **51/51 test yashil** (`2.07s`).
2. **Zero-lookahead qat'iy isboti:** ✅ Testlangan (`test_zero_lookahead_execution`).
3. **Konservativ intrabar ziddiyat:** ✅ Testlangan (`test_intrabar_conservative_sl_tp`).
4. **Haqiqiy xarajatlar va stress-test:** ✅ Empirik profil, 3x swap, Monte Carlo 1.5x/2.0x stress.
5. **Holdout qulfi mavjud:** ✅ Oxirgi 20% qulflangan, `docs/holdout_log.md` audit jurnali sozlangan.
6. **Baseline hisobotlari:** ✅ `reports/` katalogida barcha baseline va tajriba hisobotlari to'liq mavjud.

---

## 4/10 Bosqich: Strategiya Tadqiqoti va Validatsiya Natijalari

- [x] **Pre-registration (`docs/hypotheses.md`):** 7 ta oila (`HYP-01` .. `HYP-07`) va 1 ta diagnostika (`DIAG-01`) natijalarni ko'rishdan oldin ro'yxatga olindi.
- [x] **Strategiya kodlari:** `SessionBreakout`, `VolatilitySqueeze`, `TrendPullback`, `MeanReversion`, `DonchianTrend`, `IntradayNoOvernight`, `ShortOnlyTrendPullback`.
- [x] **Lookahead kesish testi:** `tests/test_strategy_lookahead_slice.py` barcha 7 ta strategiyada 0-lookahead ni isbotladi (7/7 yashil).
- [x] **R2-1 Stress Xatosi Tuzatildi:** 1.5x stress xarajati to'liq amalga oshirildi (`test_r2_1_stress_multiplier_passed_correctly`).
- [x] **R2-2 Xarajat Dekompozitsiyasi:** Gross PF, Net PF, Spread, Slippage, Swap va Komissiya aniq ajratildi. Long swap HYP-03 da ziyonning 45.7-47.9% ini, HYP-05 H4 da 73.9-78.4% ini tashkil etgani raqamlar bilan fosh qilindi.
- [x] **R2-3 Ambiguous Trades:** Engine ichida haqiqiy bar to'qnashuvi o'lchandi (atigi 0.0% – 1.09%).
- [x] **R2-4 Walk-Forward (Nested):** OOS savdolari birlashtirildi, yig'ma OOS PF hisoblandi.
- [x] **R2-5 Kalendar:** `ExportCalendar.mq5` diagnostikasi kuchaytirildi, `RuleBasedNewsCalendar` zaxira generatori yaratildi.
- [x] **R2-6 Skrining:** Gross PF < 1.05 bo'lgan 9 ta variant "NO EDGE" deb belgilandi.
- [x] **Eksperimentlar Jurnali:** `research/experiment_log.csv` ga barcha $N=15$ ta tajriba to'liq qayd etildi.
- [x] **Gate Natijasi:** Barcha 15 ta nomzod B4 Gate mezonlaridan o'tmadi. **Edge topilmadi.**
- [x] **Holdout:** Holdout qat'iy muhrlangan holda qoldi.
- [x] **Hujjat:** `docs/strategy_selection.md` va `docs/decisions.md` (ADR-0010) to'liq yangilandi.

---

## Infratuzilma Bosqichi: 6/10 + 7/10 + 8/10 (Faqat DEMO)

Strategiya tadqiqotidan mustaqil, mustahkam va xavfsiz ijro infratuzilmasi to'liq qurildi:

- [x] **0. Live Guard (Xavfsizlik Qalqoni):**
  - `python_brain/risk/live_guard.py` yaratildi.
  - `account.trade_mode == 0` (DEMO) qat'iy tekshiriladi; REAL hisobda darhol `LiveTradingBlockedError` beradi.
  - `config/settings.yaml` da `safety.allow_live: false` o'rnatildi.
- [x] **1. Risk Engine (`python_brain/risk/`):**
  - SQLite persistent state store (`data/state/risk_state.db`): kill-switch, kunlik/haftalik PnL, ketma-ket zararlar va cooldown muddati diskda saqlanadi.
  - Kill-switch ni qo'lda tiklash: `scripts/reset_kill_switch.py --reason "..." --force`.
  - `ProductionRiskGate`: 12 ta xavfsizlik cheklovi (0.5% lot risk, margin tekshiruvi, juma kechki yopish, spread filtri, ketma-ket zararlardan keyin 60 daqiqa cooldown).
- [x] **2. MT5 Ijro Qatlami (`python_brain/execution/`):**
  - `MT5BrokerExecutor`: Server darajasidagi majburiy Stop-Loss va Take-Profit (hech qanday pozitsiya SL siz ketmaydi).
  - Magic number `10101`, max deviation (slippage) 30-50 punkt.
  - Idempotentlik: shu magic/comment bilan ochiq order bo'lsa dublikat ochilishidan 100% himoya.
  - Ishga tushishda broker bilan holat sinxronizatsiyasi (`reconcile_open_positions`).
  - Retcode'lar ishlovi (requote, off quotes, no money, market closed, timeout) va qayta urinish (retry).
- [x] **3. Live Runner (`python_brain/main.py`):**
  - Faqat **yangi yopilgan M15 barlarda** ishlaydi (intrabar tick shovqinidan xoli).
  - Broker vaqt drifti tekshiruvi (ogohlantirish).
  - Graceful shutdown: dastur to'xtaganda brokerdagi pozitsiyalar server SL/TP bilan xavfsiz qoladi.
- [x] **4. Qo'riqchi EA (`mql5_ea/MTD_Guardian.mq5`):**
  - Tashqi DLL siz, sof MQL5.
  - Python `FILE_COMMON` katalogidagi `mtd_heartbeat.json` ni kuzatadi (30s timeout eskirsa Safe Mode).
  - Kunlik equity yo'qotishi 3.0% ga yetsa, barcha pozitsiyalarni brokerda majburiy yopadi va yangi savdoni bloklaydi.
- [x] **5. Monitoring va Watchdog:**
  - `python_brain/monitoring/telegram_notifier.py`: Standart `urllib` orqali xavfsiz Telegram ogohlantirishlari.
  - `scripts/watchdog.py`: LiveRunner qulasa avtomatik qayta tiriltirish va Telegram xabarnomasi.
- [x] **6. Quvur Sinov Strategiyasi:**
  - `python_brain/signals/pipeline_test.py`: "FOYDA UCHUN EMAS, FAQAT QUVUR SINOVI" (0.01 lot, ATR SL/TP, faqat demo).
- [x] **7. Testlar va Dry-Run:**
  - Mock MT5 bilan ulanish uzilishi, barcha retcode'lar, dublikatlar, reconciliation, kill-switch reset, heartbeat testlandi.
  - `scripts/demo_dry_run.py`: Demo hisobda 0.01 lot savdoni ochib, server SL/TP tekshirib, yopuvchi sinov skripti.
  - Jami testlar: **87/87 test 100% yashil** (`pytest`).



