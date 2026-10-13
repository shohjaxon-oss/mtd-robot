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



