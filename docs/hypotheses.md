# XAUUSD Savdo Gipotezalari Reyestri (Pre-Registration)

> **Hujjat maqsadi:** 4/10 bosqichda overfitting (data-snooping bias) va p-hacking oldini olish.
> Har bir gipoteza natijalarni ko'rishdan OLDIN ro'yxatga olingan. Parametrlar soni <= 4 ta, parametr qiymatlari <= 5 ta.
> Barcha sinovlar faqat **Train/Dev (80%)** ma'lumotlarida o'tkaziladi. Holdout (oxirgi 20%) qulflangan.

---

## Gipoteza 1: `H1_SESSION_BREAKOUT` (Osiyo Diapazoni Breakout)
- **ID:** `HYP-01`
- **Timeframe:** H1 (filtr M15)
- **Iqtisodiy/Tuzilmaviy Mantiq:**
  Oltin bozori likvidligi Osiyo sessiyasida (Tokyo/Singapur, 00:00 - 07:00 UTC) nisbatan past bo'ladi va tor diapazon (consolidation) hosil qiladi. London institutsional sessiyasi ochilganda (07:00 - 09:00 UTC) Yevropa banklari va London bullion bozori ishtirokchilari kirib kelishi bilan narx Osiyo sessiyasi ekstremumlaridan (High/Low) kuchli impuls bilan yorib o'tadi.
- **Kirish Qoidalari:**
  - 00:00 - 07:00 UTC oralig'idagi High va Low aniqlanadi.
  - 07:00 - 10:00 UTC oralig'ida bar yopilishi Osiyo High dan yuqori bo'lsa -> BUY; Osiyo Low dan past bo'lsa -> SELL.
  - Rollover (21:00-22:00 UTC) va news blackout filtri qo'llaniladi.
- **Chiqish Qoidalari:**
  - Stop Loss: Diapazonning qarama-qarshi tomoni yoki $1.5 \times \text{ATR}(14)$ (qaysi biri kichik bo'lsa).
  - Take Profit: $2.0 \times \text{SL masofasi}$ (R:R = 2.0).
  - Time-stop (maksimal ushlab turish): 8 ta H1 bar (kun oxiri, London sessiyasi tugashi).
- **Parametrlar Gridi (<= 4 parametr, <= 4 qiymat):**
  1. `asian_start_hour`: [0] (UTC)
  2. `asian_end_hour`: [7] (UTC)
  3. `entry_window_hours`: [2, 3] (07:00-09:00 yoki 07:00-10:00)
  4. `rr_ratio`: [1.5, 2.0]
- **Kutilgan Xatti-harakat:**
  - Trendli va yuqori volatillik kunlarida yaxshi ishlaydi.
  - Bayram va past volatillik kunlarida (fakeout) yomon ishlaydi.
- **Rad Etish Sharti (Rejection Criteria):**
  - OOS Profit Factor < 1.3 yoki 1.5x xarajat stressida PF < 1.15 bo'lsa, gipoteza rad etiladi.

---

## Gipoteza 2: `H1_VOLATILITY_SQUEEZE` (Keltner & Bollinger Siqilishi)
- **ID:** `HYP-02`
- **Timeframe:** H1
- **Iqtisodiy/Tuzilmaviy Mantiq:**
  Volatillik siklik xususiyatga ega: past volatillik davri (siqilish - compression) muqarrar ravishda yuqori volatillik (kengayish - expansion) bilan almashadi. Bollinger Band (20, 2.0) Keltner Channel (20, 1.5 ATR) ichiga kirganda bozor "siqilgan" holatda bo'ladi. Narx Keltner kanalidan tashqariga chiqqanda katta momentumli trend harakati boshlanadi.
- **Kirish Qoidalari:**
  - Squeeze holati: `Bollinger_Upper < Keltner_Upper` va `Bollinger_Lower > Keltner_Lower`.
  - Squeeze tugab, bar yopilishi Keltner Upper dan yuqori bo'lsa -> BUY; Keltner Lower dan past bo'lsa -> SELL.
- **Chiqish Qoidalari:**
  - Stop Loss: $1.5 \times \text{ATR}(14)$.
  - Take Profit: $3.0 \times \text{ATR}(14)$ (R:R = 2.0).
  - Trailing Stop: Keltner o'rta chizig'i (EMA 20) yopilishi bo'yicha.
  - Max holding: 24 bar (1 sutka).
- **Parametrlar Gridi:**
  1. `bb_mult`: [2.0]
  2. `kc_mult`: [1.5, 1.75]
  3. `atr_sl_mult`: [1.5, 2.0]
  4. `max_hold_bars`: [16, 24]
- **Kutilgan Xatti-harakat:**
  - Katta yangiliklar va geosiyosiy harakatlar oldidan hosil bo'lgan impulsda katta R:R oladi.
  - Cho'zilgan tinch flet bozorida soxta signallar berishi mumkin.
- **Rad Etish Sharti:**
  - Jami savdolar soni < 150 yoki OOS PF < 1.3 bo'lsa, rad etiladi.

---

## Gipoteza 3: `H1_TREND_PULLBACK` (Ko'p Timeframe Trend Pullback)
- **ID:** `HYP-03`
- **Timeframe:** H1 (Trend filtri: D1/H4)
- **Iqtisodiy/Tuzilmaviy Mantiq:**
  Oltin uzoq muddatli kuchli makroiqtisodiy trendlarga (inflyatsiya, foiz stavkalari, markaziy banklar xaridlari) ega. Katta timeframe (D1/H4 da EMA 50 va EMA 200) trend yo'nalishini belgilaydi. H1 da narx EMA 20/EMA 50 ga qaytganda (pullback) va RSI(14) 40-50 oralig'iga soviganda trend yo'nalishida likvidlik to'plash yakunlanadi va yangi to'lqin boshlanadi.
- **Kirish Qoidalari:**
  - D1 Trend filtri: `Close_D1 > EMA200_D1` (faqat BUY), aks holda faqat SELL.
  - H1 Pullback: Narx `EMA20_H1` va `EMA50_H1` oralig'iga tushadi va `RSI(14) <= 45` (BUY uchun).
  - Trigger: H1 bar yopilishi oldingi bar High dan yuqori bo'lganda kirish.
- **Chiqish Qoidalari:**
  - Stop Loss: Mahalliy swing ekstremum yoki $1.5 \times \text{ATR}(14)$.
  - Take Profit: $2.5 \times \text{ATR}(14)$.
  - Max holding: 30 bar.
- **Parametrlar Gridi:**
  1. `h1_fast_ema`: [20]
  2. `h1_slow_ema`: [50]
  3. `rsi_threshold`: [40, 45]
  4. `atr_sl_mult`: [1.5, 2.0]
- **Kutilgan Xatti-harakat:**
  - Kuchli buqa va ayiq bozorlarida juda barqaror ishlaydi.
  - Yo'nalishsiz keng diapazonli fletda xarajatlar yeb qo'yishi mumkin.
- **Rad Etish Sharti:**
  - OOS PF < 1.35 yoki Long va Short o'rtasida haddan tashqari nomutanosiblik bo'lsa (faqat bitta yilda ishlab, boshqa yillarda minus bersa), rad etiladi.

---

## Gipoteza 4: `H1_MEAN_REVERSION_RANGE` (Rejim Filtrli Kontr-trend)
- **ID:** `HYP-04`
- **Timeframe:** H1
- **Iqtisodiy/Tuzilmaviy Mantiq:**
  ADX(14) < 20 bo'lganda (bozorda trend yo'q, diapazonli rejim), narxning Bollinger Bands 2.5 standart chetlanishidan tashqariga chiqishi haddan tashqari cho'zilish (exhaustion) hisoblanadi. Oltin narxi o'rta qiymatga (mean) qaytish tendentsiyasiga ega bo'ladi.
- **Kirish Qoidalari:**
  - ADX(14) < 20 (Flet filtri).
  - Narx `Lower_BB(20, 2.5)` dan pastga tushib, qayta ichkariga yopilsa -> BUY; `Upper_BB` dan yuqoriga chiqib qaytsa -> SELL.
- **Chiqish Qoidalari:**
  - Stop Loss: $1.2 \times \text{ATR}(14)$ (qat'iy qisqa SL, chunki kutilmagan breakout yuz bersa tez chiqish kerak).
  - Take Profit: Bollinger o'rta chizig'i (SMA 20).
  - Max holding: 12 bar.
- **Parametrlar Gridi:**
  1. `adx_max`: [20, 22]
  2. `bb_std`: [2.2, 2.5]
  3. `atr_sl_mult`: [1.2, 1.5]
- **Kutilgan Xatti-harakat:**
  - Tinch konsolidatsiya davrlarida yuqori Win Rate (60-65%).
  - Trend boshlanishida ketma-ket SL olish xavfi yuqori.
- **Rad Etish Sharti:**
  - 1.5x xarajat stressida Net PnL < 0 bo'lsa, darhol rad etiladi (mean-reversion friksiyaga juda sezgir).

---

## Gipoteza 5: `DIAGNOSTIC_SEASONALITY` (Diagnostik Vaqt/Sessiya Tahlili)
- **ID:** `DIAG-01`
- **Turi:** Diagnostik tadqiqot (Strategiya emas, boshqa gipotezalar uchun filtr manbai).
- **Mantiq:** Hafta kunlari (Dushanba-Juma) va UTC soatlari (00:00 - 23:00) bo'yicha XAUUSD volatilligi va yo'nalishli qaytimini o'rganish.
- **Natija:** Qaysi soatlarda savdo qilish qat'iy taqiqlanishi yoki ruxsat etilishi aniqlanadi.
