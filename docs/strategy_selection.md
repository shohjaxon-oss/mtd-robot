# XAUUSD Strategiya Tanlovi va Validatsiya Xulosasi (4/10 R2)

> **Xulosa Qarori:** **HALOL KVANT XULOSASI: REAL XARAJATLAR BILAN OUT-OF-SAMPLE EDGE TOPILMADI (GATE REJECTED)**  
> **Sana:** 2026-10-13 (R2 Yangilanishi)  
> **Jami Sinalgan Variantlar ($N$):** **15 ta** (7 ta oila: HYP-01 .. HYP-07)  
> **Ma'lumotlar:** Faqat Train/Dev (80%, 2014-2024). **Holdout (20%) QAT'IY QULFLANGAN (Ochilmadi).**

---

## 1. Jami Sinalgan Barcha 15 ta Nomzod Natijalari (`research/experiment_log.csv`)

| Exp ID | Gipoteza / Strategiya | TF | Trades | Win% | Gross PF | Net PF | Corrected 1.5x Stress PF | Old Buggy 1.5x PF | Net PnL ($) | Long Swap ($) | Ambiguous% | OOS Combined PF | Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **HYP01_V1** | SessionBreakout (2h, RR 1.5) | H1 | 843 | 41.2% | **1.10** | 0.95 | **0.90** | 0.95 | -$1,283.29 | -$150.2 | 0.71% | 0.88 | ❌ REJ |
| **HYP01_V2** | SessionBreakout (3h, RR 2.0) | H1 | 1,034 | 33.0% | 1.03 | 0.89 | **0.85** | 0.95 | -$3,341.34 | -$391.9 | 0.68% | n/a (scr) | ❌ REJ |
| **HYP01_V3** | SessionBreakout (3h, ATR 2.0) | H1 | 938 | 33.4% | 1.03 | 0.91 | **0.86** | 0.95 | -$2,492.03 | -$725.8 | 0.53% | n/a (scr) | ❌ REJ |
| **HYP02_V1** | VolatilitySqueeze (KC 1.5) | H1 | 906 | 34.1% | **1.06** | 0.90 | **0.87** | 0.90 | -$2,453.93 | -$1,261.7 | 0.66% | 0.94 | ❌ REJ |
| **HYP02_V2** | VolatilitySqueeze (KC 1.75) | H1 | 977 | 32.0% | 0.94 | 0.81 | **0.78** | 0.81 | -$4,447.72 | -$1,485.1 | 0.20% | n/a (scr) | ❌ REJ |
| **HYP03_V1** | TrendPullback (EMA 20/50/200) | H1 | 438 | 34.0% | **1.06** | 0.90 | **0.87** | 0.90 | -$1,289.31 | -$768.7 | 0.23% | 0.80 | ❌ REJ |
| **HYP03_V2** | TrendPullback (RSI 40, RR 2.5) | H1 | 340 | 29.7% | **1.07** | 0.93 | **0.91** | 0.93 | -$769.99 | -$692.3 | 0.00% | 0.80 | ❌ REJ |
| **HYP04_V1** | MeanReversion (BB 2.2) | H1 | 120 | 55.0% | 0.93 | 0.76 | **0.74** | 0.76 | -$681.53 | -$97.9 | 5.83% | n/a (scr) | ❌ REJ |
| **HYP04_V2** | MeanReversion (BB 2.5) | H1 | 51 | 58.8% | 0.76 | 0.64 | **0.63** | 0.64 | -$417.74 | -$33.0 | 5.88% | n/a (scr) | ❌ REJ |
| **HYP05_V1** | DonchianTrend (H4, RR 2.5) | H4 | 398 | 30.6% | **1.11** | 0.92 | **0.89** | n/a | -$906.40 | **-$1,506.6** | 0.00% | 0.97 | ❌ REJ |
| **HYP05_V2** | DonchianTrend (H4, RR 3.0) | H4 | 353 | 27.8% | **1.17** | 0.95 | **0.94** | n/a | -$603.64 | **-$1,851.4** | 0.00% | 0.97 | ❌ REJ |
| **HYP06_V1** | IntradayNoOvernight (RR 1.5) | H1 | 1,101 | 39.4% | 1.02 | 0.89 | **0.84** | n/a | -$3,420.19 | -$182.1 | 1.09% | n/a (scr) | ❌ REJ |
| **HYP06_V2** | IntradayNoOvernight (RR 2.0) | H1 | 951 | 33.3% | 1.03 | 0.91 | **0.86** | n/a | -$2,582.88 | -$756.2 | 0.53% | n/a (scr) | ❌ REJ |
| **HYP07_V1** | ShortOnlyPullback (RSI 55) | H1 | 845 | 31.0% | 0.96 | 0.86 | **0.83** | n/a | -$3,389.98 | **$0.00** | 0.83% | n/a (scr) | ❌ REJ |
| **HYP07_V2** | ShortOnlyPullback (RSI 50) | H1 | 563 | 27.7% | 0.99 | 0.91 | **0.89** | n/a | -$1,565.71 | **$0.00** | 0.18% | n/a (scr) | ❌ REJ |

*(Izoh: `n/a (scr)` - R2-6 qoidasiga ko'ra Gross PF < 1.05 bo'lgani sababli "NO EDGE" deb belgilandi va to'liq WFO ga o'tkazilmadi).*

---

## 2. R2-1: Stress Xatosi Tahlili (OLDIN va KEYIN)
- `engine.run()` da `costs.stress_multiplier = stress_multiplier` qatori tufayli oldingi hisobda barcha 1.5x testlar yana 1.0x multiplikatoriga qaytib qolgan edi.
- Tuzatilgandan so'ng, haqiqiy 1.5x xarajat stressi ostida barcha Profit Factorlar **0.03 – 0.06 punktga pasaydi** (masalan, HYP01_V1 0.95 dan 0.90 ga, HYP02_V2 0.81 dan 0.78 ga, HYP05_V1 0.92 dan 0.89 ga tushdi).
- Eski qiymatlar `cost_stress_1_5x_pf_old_buggy` sifatida saqlandi.

---

## 3. R2-2: Xarajat Dekompozitsiyasi va Swap Asimmetriyasi (Aniq Raqamlar)

1. **HYP-03 (H1 Trend Pullback) da Swap Halokati:**
   - Long natijasi: **-$1,681.70** (V1) va **-$1,446.20** (V2).
   - Long Swap xarajati: V1 da **-$768.73 (45.7%)**, V2 da **-$692.33 (47.9%)**!
   - Short Swap esa: **$0.00 (swap-free)**!
   - Ya'ni Long savdolarining ziyonining qariyb **yarmi** aynan brokerning overnight swap foizi hisobiga to'g'ri kelgan.

2. **HYP-05 (H4 Donchian Trend) da Swap Giganti:**
   - V1: Gross PF = **1.11**, lekin Net PF = **0.92**. Jami xarajat $2,039.95, shundan **Long Swap: -$1,506.58 (73.9%)**!
   - V2: Gross PF = **1.17** (bozorda sezilarli sof trend ustunligi bor!), lekin Net PF = **0.95**. Jami xarajat $2,361.26, shundan **Long Swap: -$1,851.44 (78.4%)**!
   - H4 da shamlar kam, spread xarajati past ($215 - $233), ammo pozitsiyalar haftalab ushlab turilgani tufayli har kecha yechilgan -$52.62/lot to'liq sof foydani yo'qqa chiqargan.

3. **HYP-07 (Short-Only) da Swap-Free natijasi:**
   - Swap haqiqatan **$0.00** bo'ldi. Biroq, oltinning 10 yillik o'sish fonida ayiq pullbacklari xom narxda Gross PF < 1.00 (0.96 - 0.99) berib, o'z-o'zidan ustunlikka ega emasligi isbotlandi.

---

## 4. R2-3: Ambiguous-Bar Tekshiruvi
- Engine ichida bir barda ham SL, ham TP tegishi aniq qayd etildi (`is_ambiguous_exit`).
- Barcha H1 va H4 strategiyalarida ikkilamchi savdolar foizi atigi **0.0% – 1.09%** oralig'ida bo'ldi.
- Bu shuni isbotlaydiki: SL-first konservativ qoidasi natijalarni buzmagan, strategiyalarning yutqazishi model xatosi emas, bozor friksiyasi va ustunlikning zaifligidandir.

---

## 5. R2-4: Walk-Forward Birlashtirilgan OOS Savdolari (Nested WFO)
- OOS oynalari birlashtirilib yagona equity curve hisoblandi:
  - HYP01_V1: OOS Combined PF = **0.88** (Sharpe: -1.27, Profitable windows: 22.2%)
  - HYP02_V1: OOS Combined PF = **0.94** (Sharpe: -0.65, Profitable windows: 33.3%)
  - HYP03_V1: OOS Combined PF = **0.80** (Sharpe: -1.36, Profitable windows: 22.2%)
  - HYP05_V1: OOS Combined PF = **0.97** (Sharpe: -0.19, Profitable windows: 25.0%)
  - HYP05_V2: OOS Combined PF = **0.97** (Sharpe: -0.19, Profitable windows: 25.0%)
- Foydali oynalar ulushi 60% ga yetmadi (22% – 33%).

---

## 6. R2-6: Skrining Natijalari (Edge vs Cost)
- **Gross PF < 1.05 bo'lganlar (Edge yo'q, xarajatdan emas):**
  - HYP01_V2, HYP01_V3, HYP02_V2, HYP04_V1, HYP04_V2, HYP06_V1, HYP06_V2, HYP07_V1, HYP07_V2.
  - Bu nomzodlar xarajatlar bo'lmaganda ham g'olib bo'la olmaydi.
- **Gross PF >= 1.05 bo'lganlar (Xarajat yeb qo'ygan nomzodlar):**
  - HYP01_V1 (Gross PF 1.10 -> Net 0.95)
  - HYP02_V1 (Gross PF 1.06 -> Net 0.90)
  - HYP03_V1 (Gross PF 1.06 -> Net 0.90)
  - HYP03_V2 (Gross PF 1.07 -> Net 0.93)
  - **HYP05_V2 (Gross PF 1.17 -> Net 0.95)** — eng yaqin nomzod! Uni o'ldirgan yagona narsa: **Long Swap (-$1,851.44)**.

---

## 7. Yakuniy Kvant Qarori va Holdout Holati

- **GATE XULOSASI:** B4 talablarini (Net PF >= 1.4, Max DD <= 12%, Sharpe >= 1.2, Savdolar >= 500) bajargan nomzod **TOPILMADI (GATE REJECTED)**.
- **HOLDOUT:** B5 protokoli bo'yicha **Holdout (2024-10-25 -> 2026-10-12) QAT'IY OCHILMADI VA TOZA SAQLANDI**.
- **Eng Muhim Kashfiyot:** XAUUSD bo'yicha H4 Trend-Following sof narxda 1.17 PF ga ega. Agar u "Swap-Free" islomiy/maxsus hisobda yoki fyucherslarda (swap o'rniga faqat komissiya to'lanadigan platformada) ishlatilsa, Net PF 1.15+ bo'lishi mumkin! Ammo Exness Standard Retail hisobidagi og'ir overnight swap (-$52.62/lot) uni manfiyga tushiradi.
