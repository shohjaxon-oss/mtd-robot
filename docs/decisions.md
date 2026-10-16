# Architecture Decision Records (ADR)

Ushbu hujjatda `mtd-robot` loyihasi bo'yicha qabul qilingan barcha muhim texnik, arxitekturaviy va risk qarorlari ularning sabablari bilan qayd etiladi.

---

## ADR-0001: Gibrid Arxitektura (Python Miya + MQL5 EA Qalqon)
- **Sana:** 2026-10-12
- **Holat:** Qabul qilindi
- **Kontekst:**
  MT5 savdo tizimini faqat MQL5 da yozish murakkab matematik va tahliliy modellarni, ma'lumotlar tahlilini qiyinlashtiradi. Faqat Python orqali savdo ochish esa terminal uzilishi, Python skripti to'xtab qolishi yoki kechikish holatlarida ochiq pozitsiyalarni xavf ostida qoldiradi.
- **Qaror:**
  Tizim ikki qatlamli qilib quriladi:
  1. **Python Brain:** Bozor tahlili, rejim klassifikatsiyasi, signallar, yangilik filtrlari, risk hisob-kitoblari.
  2. **MQL5 EA (Executor & Shield):** Terminal ichida mustaqil ishlovchi, SL/TP majburiyligini nazorat qiluvchi, Python bilan aloqa uzilganda yoki kill-switch faollashganda pozitsiyalarni himoya qiluvchi qatlam.
- **Oqibati:**
  Dastur yuqori xavfsizlik darajasiga ega bo'ladi. MQL5 EA Python o'chib qolsa ham oldindan o'rnatilgan qat'iy SL/TP tufayli kapitalni saqlaydi.

---

## ADR-0002: Risk Limitlari va Konfiguratsiyani Pydantic Bilan Qulflash
- **Sana:** 2026-10-12
- **Holat:** Qabul qilindi
- **Kontekst:**
  Inson xatosi yoki noto'g'ri config fayli sababli savdo roboti ruxsat etilgan me'yordan ortiq lot ochib yuborishi, yoki SL siz pozitsiya buyurtma qilishi mumkin.
- **Qaror:**
  - Konfiguratsiya `config/*.yaml` fayllari orqali boshqariladi va `Pydantic v2` orqali validatsiyadan o'tkaziladi.
  - Risk chegaralari kod darajasida qat'iy tekshiriladi:
    - Bitta savdoga maksimal risk: 1.0% (boshlang'ich tavsiya 0.5%). Agar sozlamada 1.0% dan yuqori yozilsa, tizim ishga tushmaydi va qat'iy xatolik bilan to'xtaydi.
    - Kunlik maksimal drawdown: -2.0%.
    - Haftalik maksimal drawdown: -4.0%.
    - Umumiy portfel kill-switch: -12.0%.
    - Martingale, averaging, grid rejimlari dastur arxitekturasi darajasida umuman mavjud emas.
- **Oqibati:**
  Hech kim (shu jumladan operator ham) xato qilib xavfli risk parametrlarini o'rnatolmaydi.

---

## ADR-0003: Sirlarni Niqoblash va Xavfsiz Logging (Loguru)
- **Sana:** 2026-10-12
- **Holat:** Qabul qilindi
- **Kontekst:**
  MT5 hisob loginlari, parollar, server ma'lumotlari yoki API kalitlari log fayllariga yoki konsolga tushib qolishi katta xavfsizlik tahdidi hisoblanadi.
- **Qaror:**
  - `loguru` kutubxonasiga maxsus filtr/redaktor o'rnatiladi. U parollar, loginlar va tokenlarni avtomatik aniqlab `***MASKED***` bilan almashtiradi.
  - Loglar `logs/trading.log` (rotatsiya: 10MB, saqlash: 30 kun) va konsolga chiqariladi.
- **Oqibati:**
  Loglar bemalol tekshirish uchun taqdim etilishi mumkin, hech qanday hisob sirlari fosh bo'lmaydi.

---

## ADR-0004: XAUUSD Simvol Nomini Dinamik Aniqlash (Exness Sufikslari)
- **Sana:** 2026-10-12
- **Holat:** Qabul qilindi
- **Kontekst:**
  Exness brokerida hisob turiga qarab oltin simvoli har xil bo'ladi:
  - Standard hisob: `XAUUSDm` (m harfi mini/standard belgilaydi)
  - Raw Spread / Pro / Zero hisoblar: `XAUUSD`
- **Qaror:**
  `mt5_connect.py` terminalga ulanganda mavjud simvollar ro'yxatidan qidiruv o'tkazadi va to'g'ri instrumentni avtomatik aniqlaydi yoki config dagi moslikni tasdiqlaydi. Shuningdek `symbol_info` dagi barcha shartlarni (spread, stops level, min lot, step lot, contract size, tick value) to'liq xotiraga oladi.
- **Oqibati:**
  Xato simvol tufayli savdo to'xtab qolishi yoki noto'g'ri lot hisoblanishi xavfi bartaraf etiladi.

---

## ADR-0005: Parquet Formatida Tarixiy Ma'lumotlarni Saqlash
- **Sana:** 2026-10-12
- **Holat:** Qabul qilindi
- **Kontekst:**
  CSV formatida millionlab qatorli barlarni saqlash juda ko'p disk joyini egallaydi va sekin yuklanadi.
- **Qaror:**
  Tarixiy barlar `data/raw/<symbol>/<tf>/` papkasida Apache Parquet (Snappy kompressiyasi) formatida saqlanadi. Yuqori freymlar (D1, H4, H1, M15) yillik fayllar bo'yicha, quyi freymlar (M5, M1) esa oylik fayllar bo'yicha partitsiyalanadi.
- **Oqibati:**
  Ma'lumotlar hajmi 8-10 barobarga qisqardi, yuklanish tezligi 15-20 barobarga oshdi.

---

## ADR-0006: Broker Server Vaqti va Qat'iy UTC Standarti
- **Sana:** 2026-10-12
- **Holat:** Qabul qilindi
- **Kontekst:**
  Turli brokerlar turli vaqt zonalarida ishlaydi (masalan UTC+2, UTC+3 va h.k.). Bu backtest va tahlillarda soatlik xatoliklarga olib kelishi mumkin.
- **Qaror:**
  `scripts/probe_history.py` orqali Exness MT5 serveri bevosita **UTC+0** (aniq UTC) rejimida ishlashi aniqlandi va o'lchandi. Shunga qaramay, barcha ma'lumotlar bazasida `time_utc` va `broker_time` alohida saqlanishi qat'iy standart sifatida qabul qilindi.
- **Oqibati:**
  Tizim istalgan boshqa brokerga ko'chirilganda ham vaqt zonasi konvertatsiyasi 100% buzilmasdan ishlaydi.

---

## ADR-0007: M1 va M5 Tarixi Chuqurligi Bo'yicha Halol Kvant Qarori
- **Sana:** 2026-10-12 (Yangilandi: 2026-10-13)
- **Holat:** Qabul qilindi (Foydalanuvchi bilan 1-Variant tasdiqlandi)
- **Kontekst:**
  Terminal sozlamasida `maxbars` chegarasi 100,000,000 (Unlimited) qilib o'rnatildi va `copy_rates_range` orqali to'g'ridan-to'g'ri eski sanalar (masalan 2024-yil M5 yoki 2025-yil M1) so'raldi.
  Natijada broker serveri `last_error=(1, 'Success')` bilan eski barlar o'rniga faqat o'zida saqlangan eng birinchi barni (M1: 2026-07-01, M5: 2025-05-14) qaytardi. Bu broker serverida eski M1/M5 arxivi jismonan mavjud emasligini 100% isbotladi.
  `downloader.py` da esa hech qanday sun'iy cheklov mavjud emasligi tasdiqlandi.
- **Qaror:**
  1. **1-Variant tasdiqlandi:** Asosiy tadqiqot timeframe'lari sifatida **H1 (12.7 yil)** va **M15 (4.2 yil, ~100,000 bar)** qabul qilindi.
  2. M5 (~1.5 yil, 100k bar) va M1 (~3.5 oy, 101k bar) hamda tick ma'lumotlari faqat ijro (execution), slippage va bar ichidagi tartibni kalibrlash uchun ishlatiladi.
  3. `scripts/archive_recent.py` yaratildi: u haftalik ravishda yangi M1 va tick ma'lumotlarini to'plab, o'zimizning mustaqil arxivimizni shakllantiradi.
  4. Dukascopy tashqi manbasi hozircha qo'shilmaydi (4/10 bosqichda qayta ko'rib chiqiladi).
- **Oqibati:**
  Loyiha 100% brokerning haqiqiy ma'lumotlariga tayangan holda davom etadi. Overfitting va lookahead xavflari holdout va walk-forward orqali qat'iy nazorat qilinadi.

---

## ADR-0008: Backtest Engine Arxitekturasi va Real Xarajatlar Modeli Standartlari
- **Sana:** 2026-10-13
- **Holat:** Qabul qilindi
- **Kontekst:**
  3/10 bosqich auditi natijasida:
  1) Swap va komissiya ikki marta yechilishi aniqlandi (kunlik balansda va yopilishda).
  2) Kill-switch tadqiqot paytida to'liq tarixni ko'rishga to'sqinlik qilib, dastlabki 119 savdodan keyin simulyatsiyani to'xtatib qo'ydi.
  3) Rollover blackout ijro barining ochilish vaqtida tekshirilishi kerak edi.
  4) Gap-down / Gap-up paytida Stop Loss bar_open narxidan yomonroq to'ldirilishi (slippage bilan) lozim edi.
- **Qaror:**
  1. **Yagona hisob-kitob (Single Accounting):** Komissiya ochilishda balansdan yechilmaydi, balki pozitsiyada saqlanadi. Swap har kuni faqat `pos.accumulated_swap` ga to'planadi (balans o'zgarmaydi, suzuvchi equityda aks etadi). Yopilish paytida `realized_pnl = gross_pnl + accumulated_swap - commission` hisoblanib, balansga FAQAT BIR MARTA qo'shiladi. Balans o'zgarishi aniq `gross P&L + swap - commission` ga teng.
  2. **`halt_on_kill_switch` bayrog'i:** Strategiya tadqiqotida (baseline, 4/10, MC, WFO) `halt_on_kill_switch = False` qilinadi, shunda butun tarix to'liq baholanadi. Biroq 12% DD ga tushgan birinchi sana `account.kill_switch_triggered_at` audit sifatida saqlanadi. Jonli ijro va risk-testlarda esa `True` qilinadi.
  3. **Spread modeli:** Default rejim `"auto_bar_or_median"` etib belgilandi (mavjud davrda real bar `spread` ishlatiladi, yo'q davrda soatlik median, rollover/news blackout paytida p95 ga kengayadi).
  4. **Swap Kunlari va Vaqti:** Python `weekday()` bo'yicha: 0=Dushanba, 1=Seshanba, 2=Chorshanba, 3=Payshanba, 4=Juma, 5=Shanba, 6=Yakshanba. Exness MT5 da `swap_rollover3days = 3` (MT5 enum bo'yicha 3 = Chorshanba, Wednesday night rollover). Python da bu `weekday() == 2` (yoki Payshanbaga o'tish kechasi) ga to'g'ri keladi. Bu qiymat config ga chiqarildi.
  5. **Min-lot Risk Toleransi:** Agar majburiy min-lot (0.01) hisobdagi 0.5% risk kapitalining 1.5 barobaridan (masalan $2.50 ning $3.75 chegarasi) oshib ketadigan keng SL bo'lsa, risk-gate buyruqni qat'iy rad etadi.
- **Oqibati:**
  Backtest motori matematik va buxgalteriya jihatidan 100% to'g'ri va real bozor fizikasiga moslandi.

---

## ADR-0009: 4/10 Strategiya Tadqiqoti, Nomzodlarni Rad Etish va Holdoutni Qulflab Qolish
- **Sana:** 2026-10-13
- **Holat:** Qabul qilindi (Halol Kvant Qarori: Edge Topilmadi)
- **Kontekst:**
  4/10 bosqichda XAUUSD uchun 4 ta klassik strategiya oilasi (`HYP-01`: SessionBreakout, `HYP-02`: VolatilitySqueeze, `HYP-03`: TrendPullback, `HYP-04`: MeanReversion) natijalarni ko'rishdan oldin `docs/hypotheses.md` da oldindan ro'yxatga olindi.
  Har bir nomzod faqat Train/Dev (80%, 2014-2024) ma'lumotlarida qat'iy protokol (WFO, 1.5x xarajat stressi, Long/Short ajratish, Monte Carlo) bilan sinovdan o'tkazildi.
- **Qaror:**
  1. **Barcha 4 ta nomzod oilasi (9 ta parametr konfiguratsiyasi) B4 Gate mezonlaridan o'ta olmadi (PF 0.64 - 0.95)**. Baza Profit Factor talabi ($\ge 1.40$) va stress talabi ($\ge 1.20$) bajarilmadi.
  2. **Holdout (oxirgi 20%) OCHILMAYDI va QAT'IY MUHRLANGAN HOLDA QOLADI.** Nomzodlar Train davrida o'zini oqlamagani sababli, holdout ma'lumotlarini ifloslantirish (data snooping) qat'iy man etiladi.
  3. **Halollik prinsipi:** Hech qanday natija bezatilmadi yoki parametrlarni haddan tashqari moslash (curve-fitting) orqali sun'iy foyda ko'rsatilmadi. Xulosa: "Edge topilmadi".
  4. **Keyingi yo'nalish:** Uzoq ushlab turiladigan long swing strategiyalaridagi og'ir swap yukini bartaraf etuvchi kun ichi (intraday non-overnight) yoki short-biased momentum modellari o'rganiladi.
- **Oqibati:**
  Bozor haqiqatiga bo'ysunildi, real kapital asrab qolindi va loyihaning ilmiy integritysi 100% saqlandi.

---

## ADR-0010: 4/10 R2 Audit Tuzatishlari, Xarajat Dekompozitsiyasi va Swap Asimmetriyasi
- **Sana:** 2026-10-13
- **Holat:** Qabul qilindi
- **Kontekst:**
  4/10 R2 doirasida audit talab qilgan 8 ta muhim vazifa bajarildi:
  1) `engine.run()` da `stress_multiplier` xatosi tuzatildi (None bo'lmaganda ustidan yozish).
  2) Xarajat dekompozitsiyasi orqali Gross PF, Net PF, Spread, Slippage, Swap va Komissiya aniq ajratildi.
  3) Engine ichida ambiguous savdolar (`is_ambiguous_exit`) sanaldi.
  4) Walk-Forward nested qilinib, barcha OOS savdolari birlashtirildi (concatenated OOS PF).
  5) Yangi gipotezalar (HYP-05 H4 Donchian, HYP-06 H1 Intraday No-Overnight, HYP-07 Short-Only Pullback) sinovdan o'tkazildi (Jami $N=15 \le 30$).
- **Asosiy Kashfiyotlar va Qaror:**
  1. **Long Swap Halokati:** XAUUSD da uzoq muddatli trend-following (HYP-05 H4) sof narxda **Gross PF = 1.17** ga ega! Biroq jami $2,361 xarajatning **78.4% i (-$1,851)** aynan Long Swap foiziga ketgan. Natijada Net PF 0.95 ga tushgan.
  2. **Ambiguous Trades Haqiqati:** H1 va H4 da bar ichida SL va TP bir vaqtda tegishi nazariy 8-20% emas, balki realda atigi **0.0% – 1.09%** ekanligi isbotlandi. SL-first qoidasi natijalarni buzmagan.
  3. **Skrining (R2-6):** Gross PF < 1.05 bo'lgan 9 ta variant xarajatdan emas, sof ustunlik yo'qligidan (NO EDGE) darhol rad etildi.
  4. **Holdout Qulfi:** B4 mezonlaridan o'tgan nomzod topilmagani sababli, holdout (oxirgi 20%) ochilmadi.
- **Oqibati:**
  Strategiya tadqiqotining barcha zaif nuqtalari matematik aniqlikda fosh qilindi. Retail MT5 hisobidagi swap cheklovlari va kelgusidagi arxitektura yo'nalishi (kun ichi / swap-free / komissiyali fyucherslar) aniq belgilandi.

---

## ADR-0011: Strict Live Guard va Demo-Only Enforcement (6-8 Bosqichlar)
- **Sana:** 2026-10-13
- **Holati:** Qabul qilindi
- **Kontekst:**
  Infratuzilma bosqichida (Risk Engine, Broker Execution, Live Runner, Watchdog) real pul xavf ostida qolmasligi kafolatlanishi shart. Strategiya tadqiqoti hali yakunlanmagan.
- **Qaror:**
  1. `LiveGuard` va `validate_demo_account` moduli joriy qilindi.
  2. Barcha ijro nuqtalari (`MT5BrokerExecutor`, `LiveRunner`, `PipelineTestStrategy`, `demo_dry_run`) `account.trade_mode == 0` (DEMO) ekanligini qat'iy tekshiradi.
  3. `config/settings.yaml` da `safety.allow_live: false` o'rnatildi. Faqat 10/10 Gate'dan o'tgandan keyin qo'lda o'zgartiriladi.
  4. Real hisob aniqlanganda yoki `allow_live=True` ruxsatsiz berilganda tizim darhol `LiveTradingBlockedError` bilan to'xtaydi.
- **Oqibati:**
  Real hisobda tasodifiy yoki xato buyurtma berilish ehtimoli 100% istisno qilindi.

---

## ADR-0012: Persistent Risk Engine va MTD_Guardian EA Circuit Breakers
- **Sana:** 2026-10-13
- **Holati:** Qabul qilindi
- **Kontekst:**
  Python jarayoni qayta ishga tushganda yoki tarmoq uzilganda kunlik/haftalik DD xotirasi yo'qolmasligi, kill-switch saqlanib qolishi va broker terminali tomondan mustaqil xavfsizlik zanjiri bo'lishi lozim.
- **Qaror:**
  1. SQLite asosidagi `RiskStateStore` (`data/state/risk_state.db`) yaratildi: Kill-switch holati, kunlik/haftalik PnL, ketma-ket zararlar va cooldown muddati diskda saqlanadi.
  2. Kill-switch faollashganda avtomatik qayta yoqilmaydi; faqat `scripts/reset_kill_switch.py --reason "..." --force` orqali qo'lda tiklanadi.
  3. MQL5 tomonida DLL-siz toza `MTD_Guardian.mq5` yaratildi. U MT5 ning `FILE_COMMON` katalogidagi `mtd_heartbeat.json` ni kuzatadi. Agar Python 30 soniyadan ko'proq jim qolsa, barcha ochiq savdolarni favqulodda yopadi (Safe Mode).
  4. Kunlik equity yo'qotishi 3.0% ga yetsa, EA barcha pozitsiyalarni mustaqil ravishda yopadi.
- **Oqibati:**
  Ikki tomonlama mustaqil himoya (Python Brain Risk Gate + MT5 MQL5 Guardian EA) ta'minlandi.

---

## ADR-0013: FU Formation Strategiyasi va Multi-Leg Breakeven Arxitekturasi
- **Sana:** 2026-10-13
- **Holati:** Qabul qilindi
- **Kontekst:**
  Loyiha egasi (trader) tomonidan "FU Formation" nomli scalping strategiyasi (HYP-09) taqdim etildi. Strategiya 2 ta legdan iborat bo'lib (har biri 0.01 lot, Leg A TP: 20 pip, Leg B TP: 30 pip), Leg A yopilgach Leg B SL'i kirish narxiga (breakeven) ko'chirilishi shart.
- **Qaror:**
  1. **Pip Birligi:** XAUUSDm da 1 pip = 0.10 USD (100 point). Agar 0.01 USD olinsa, brokerning median spreadi (160 pt = 1.6 pip = $0.16) Leg A TP ($0.20) dan oshib, savdoni iqtisodiy jihatdan imkonsiz qilar edi. Pip narxi `config/risk.yaml` ga kiritildi va hardcode qilinmadi.
  2. **Multi-Leg va Guruh Ijrosi:** Backtest dvigateli (`engine.py`) va RiskGate (`risk_gate.py`) kengaytirildi:
     - Har bir setup bitta `group_id` ostida bir nechta leglarga ajratiladi.
     - RiskGate setup darajasida atomik tasdiqlaydi (ikkala leg birga o'tadi yoki rad etiladi).
     - Fixed lot (0.01 + 0.01) rejimi qo'llab-quvvatlandi.
     - Setup umumiy riski ($0.02 \times \text{SL masofasi} \times 100$) balansning $1\%$ idan oshsa, qat'iy rad etiladi.
  3. **Bar Ichidagi Konservativ Tartib:**
     - (i) SL va TP bitta barda tegsa, SL birinchi deb hisoblanadi (konservativ prinsip saqlanadi).
     - (ii) Breakeven SL keyingi bardan kuchga kiradi (lookahead/intra-bar cheating oldini olish uchun).
     - (iii) Bitta barda TP_A va TP_B ikkalasiga ham tegsa: Leg B faqat narx qaytib BE ga urilmagan bo'lsa TP_B da yopiladi; aks holda Leg B BE da yopilgan deb olinadi va setup `is_ambiguous_exit=True` deb belgilanadi.
     - (iv) Boshlang'ich SL ikkala legni ham darhol yopadi.
  4. **Risk Profil Override:** Standart `risk.yaml` dagi `min_risk_reward_ratio: 1.5` global qoidasi o'zgartirilmasdan, `strategy_profiles.fu_formation.min_risk_reward_ratio: 0.5` override qilindi (chunki dinamik SL 15-20 pip va TP 20/30 pip bo'lganda R:R odatda 0.8-1.2 atrofida bo'ladi).
- **Oqibati:**
  Backtest dvigateli va Live ijro arxitekturasi orqaga to'liq mos holda multi-leg va breakeven funksiyalariga ega bo'ldi. Mavjud 87 ta regression testlari 100% yashil qoldi.

---

### ADR-0014: FU-M3 Jonli Ijro Tuzatishlari, Realistik Spread (450 pt) va Demo Data Collection Profili
- **Sana:** 2026-10-15
- **Status:** Qabul qilindi
- **Kontekst:**
  MTD-ROBOT Exness demo hisobida ishga tushirilganda birorta ham pozitsiya ochmagan edi. Kod auditi quyidagi sabablarni aniqladi:
  1. `max_spread_points: 40.0` bo'lib qolgan edi. XAUUSD real spreadi odatda 180-260 punkt, p95 280-360 punkt, rolloverda 1600+ punkt. Oqibatda har bir signal `SPREAD_TOO_HIGH` xatosi bilan bloklangan.
  2. `main.py` da `risk_gate.evaluate(...)` mavjud emas edi (`AttributeError`).
  3. `ProductionRiskGate` config wiring noto'g'ri bo'lib, `risk_per_trade_pct` ga `max_allowed_risk_per_trade_pct` (1.0%) olingan, drawdown limitlari o'qilmagan.
  4. `fu_formation.py` strategiyasi `tp_pips` qaytargan, lekin `main.py` `leg.tp` (None) ni yuborgani sababli MT5 ga TP umuman qo'yilmagan.
  5. Timeframe M3 qulflanmagan va bitta setup qoidasi to'liq tekshirilmagan.
- **Qaror:**
  1. **Spread Chegarasi:** `config/risk.yaml` dagi `max_spread_points` 450.0 punktga ko'tarildi (`docs/spread_profile.md` dagi p95 parametrlariga asoslanib).
  2. **Yagona Evaluate API:** `ProductionRiskGate` ga `evaluate()` metodi qo'shildi va `AccountState` MT5 ning real deal tarixidan (bugungi va haftalik realized PnL) hisoblanadigan `build_account_state()` funksiyasi yaratildi.
  3. **FU 2-Leg Atomik Ijro va Fill Narxidan TP:** Buyurtma yuborishda so'rov narxidan server-side TP yuboriladi, fill bo'lgach esa haqiqiy fill narxiga nisbatan aniq TP ga `modify_position_sl_tp` qilinadi.
  4. **Breakeven Trailing:** Leg A TP bilan yopilganda Leg B ning SL i kirish narxiga ko'chiriladi. Leg A SL bilan yopilsa BE ishlamaydi.
  5. **Demo Data Collection Profili:** Demo hisobda kunlik savdo soni 30 tagacha kengaytirildi, cooldown o'chirildi; lekin kunlik 2% va umumiy 12% kill-switch to'liq faol qoladi. Profil faqat DEMO da ishlaydi, REAL da xato berib to'xtaydi.
  6. **Ishonchlilik:** 5 soniya kechikish filtri, `stops_level` tekshiruvi, bitta setup qoidasi, alohida oqimdagi heartbeat va diskka state saqlash joriy etildi.
- **Oqibati:**
  MTD-ROBOT Exness demo hisobida to'liq avtonom, qat'iy atomik va kuzatiladigan holatga keltirildi. Barcha tekshiruvlar preflight va replay_signals vositalari orqali tasdiqlandi.

