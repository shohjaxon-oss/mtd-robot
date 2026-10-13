# XAUUSD Strategiya Tanlovi va Validatsiya Xulosasi (4/10 Gate)

> **Xulosa Qarori:** **HALOL KVANT XULOSASI: REAL XARAJATLAR BILAN OUT-OF-SAMPLE EDGE TOPILMADI (GATE REJECTED)**  
> **Sana:** 2026-10-13  
> **Baho Berilgan Nomzodlar:** 4 ta oila, 9 ta parametr konfiguratsiyasi  
> **Ma'lumotlar:** Faqat Train/Dev (80%, 2014-2024). **Holdout (20%) QAT'IY MUHRLANGAN HOLDA QOLDI (Ochilmadi).**

---

## 1. B4 Gate Mezonlari va Natijalar Xulosasi

Loyiha spetsifikatsiyasi bo'yicha Gate talablari:
- **Profit Factor (OOS va Real Cost):** $\ge 1.40$
- **Max Equity Drawdown:** $\le 12.0\%$
- **Sharpe Ratio:** $\ge 1.20$
- **Recovery Factor:** $\ge 3.0$
- **WFO Barqarorligi:** $\text{OOS PF} \ge \text{IS PF} \times 0.70$
- **Savdolar Soni:** $\ge 500$
- **Xarajat Stressi (1.5x):** $\text{PF} \ge 1.20$

### Sinalgan Barcha Variantlar Jadvali (`research/experiment_log.csv` asosida):

| Exp ID | Gipoteza / Strategiya | Savdolar | Win% | Net P&L ($) | Baza PF | 1.5x Stress PF | Max DD% | Sharpe | Long P&L | Short P&L | OOS PF | Gate Holati |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **HYP01_V1** | SessionBreakout (2h window, R:R 1.5) | 843 | 41.2% | -$1,283.29 | 0.95 | 0.95 | 29.07% | -0.75 | -$1,124.5 | -$158.8 | 0.83 | ❌ REJECTED |
| **HYP01_V2** | SessionBreakout (3h window, R:R 2.0) | 1,034 | 33.0% | -$3,341.34 | 0.89 | 0.89 | 39.82% | -1.78 | -$2,512.4 | -$828.9 | 0.83 | ❌ REJECTED |
| **HYP01_V3** | SessionBreakout (3h, R:R 2.0, ATR 2.0) | 938 | 33.4% | -$2,492.03 | 0.91 | 0.91 | 33.80% | -1.36 | -$1,984.1 | -$507.9 | 0.92 | ❌ REJECTED |
| **HYP02_V1** | VolatilitySqueeze (KC 1.5, R:R 2.0) | 906 | 34.1% | -$2,453.93 | 0.90 | 0.90 | 36.74% | -1.45 | -$2,091.8 | -$362.1 | 0.92 | ❌ REJECTED |
| **HYP02_V2** | VolatilitySqueeze (KC 1.75, ATR 2.0) | 977 | 32.0% | -$4,447.72 | 0.81 | 0.81 | 49.12% | -3.12 | -$2,755.8 | -$1,691.9 | 0.80 | ❌ REJECTED |
| **HYP03_V1** | TrendPullback (EMA 20/50/200, RSI 45) | 438 | 34.0% | -$1,289.31 | 0.90 | 0.90 | 18.97% | -1.01 | -$1,681.7 | **+$392.4** | 0.82 | ❌ REJECTED |
| **HYP03_V2** | TrendPullback (EMA 20/50/200, RSI 40) | 340 | 29.7% | -$769.99 | 0.93 | 0.93 | 12.99% | -0.59 | -$1,446.2 | **+$676.2** | 0.83 | ❌ REJECTED |
| **HYP04_V1** | MeanReversion (BB 2.2, ADX < 20) | 120 | 55.0% | -$681.53 | 0.76 | 0.76 | 8.76% | -1.36 | -$312.6 | -$368.9 | n/a | ❌ REJECTED |
| **HYP04_V2** | MeanReversion (BB 2.5, ADX < 22) | 51 | 58.8% | -$417.74 | 0.64 | 0.64 | 5.69% | -1.37 | -$60.0 | -$357.7 | n/a | ❌ REJECTED |

---

## 2. Nega Birorta Ham Strategiya Gate'dan O'tmadi? (Chuqur Kvant Tahlili)

### 1. Broker Xarajatlari Asimmetriyasi (Swap Zarbi)
- Exness MT5 hisobida **Long swap -$52.62 / lot / kecha**, **Short swap esa $0 (swap-free)**.
- `HYP-03` (Trend Pullback) natijalarida juda muhim anomaliya ko'rindi:
  - Short pozitsiyalar **ijobiy natija berdi:** V1 da **+$392.4**, V2 da **+$676.2**!
  - Ammo Long pozitsiyalar qattiq ziyon ko'rdi: V1 da **-$1,681.7**, V2 da **-$1,446.2**.
  - Chunki bir necha kunlab ushlangan long pozitsiyalar har kecha og'ir swap to'lovi tufayli yemirilib ketgan.

### 2. Oltin (XAUUSD) Dinamikasi va Whipsaw Muammosi
- XAUUSD likvidligi yuqori bo'lsa-da, H1 va M15 barlarida to'g'ridan-to'g'ri breakoutlar (Session Breakout va Squeeze) ko'p hollarda "soxta yorilish" (liquidity sweep / fakeout) bilan tugaydi.
- R:R = 2.0 yoki 2.5 bo'lgan breakoutlarda g'alaba foizi atigi 32-34% atrofida bo'lib, har bir savdoga to'langan spread ($0.21 - $0.28) va slippage kutilmani manfiy tomonga surib yuboradi.

### 3. Mean Reversion da "Qora Oqqush" (Tail Risk)
- `HYP-04` da g'alaba foizi 55-58% ga yetgan bo'lsa-da, foyda omili (PF) eng past (0.64 - 0.76) bo'ldi.
- Flet rejimidan kutilmaganda chiqqan kuchli trend harakatlari bir nechta SL orqali to'plangan kichik foydalarni birdaniga yo'q qildi.

---

## 3. Holdout Boshqaruvi (Holdout Lock)

- `B5` talabiga ko'ra, **faqat B4 dan o'tgan nomzodlar uchun** holdout ochilishi mumkin.
- Hech bir nomzod B4 dan o'tmagani sababli, **Holdout (2024-10-25 -> 2026-10-12) QAT'IY QULFLANGAN HOLDA SAQLANDI**.
- Bu ma'lumotlar ifloslanishining (data contamination) oldini oldi va kelajakdagi rivojlangan gipotezalar uchun xolis sinov bazasi sifatida saqlab qolindi.

---

## 4. O'rganilgan Saboqlar va Keyingi Gipotezalar Yo'nalishi

1. **Short-Biased yoki Intraday No-Overnight Model:**
   - Long pozitsiyalarni tungi rollover (21:00 UTC) ga qoldirmaslik (kun oxirida yopish yoki faqat intraday savdo).
   - Yoki swap-free bo'lgan Short tomonga ko'proq e'tibor berish yoki broker bilan "swap-free" shartlarini kelishish.
2. **Volatillik va Sessiya Diagnostikasi (DIAG-01):**
   - Eng yuqori o'rtacha diapazon 12:00 - 15:00 UTC (AQSh ochilishi) oralig'ida ($6.00 - $7.60).
   - London va Nyu-York kesishgan (12:00 - 16:00 UTC) soatlarda momentumga asoslangan qisqa muddatli intraday impulslar o'rganilishi kerak.
3. **Rejim Filtrlari:**
   - Oddiy EMA/ADX filtrlari o'rniga, yuqori tartibli rejim aniqlovchilar (masalan, ATR nisbati, Volatility Term Structure yoki London sessiyasi vaqt zonalari) talab etiladi.

---

## 5. Xulosa

Spetsifikatsiya va foydalanuvchi talabiga ko'ra:
> *"Edge topilmasa, 'edge topilmadi' deb yozish muvaffaqiyatli natija hisoblanadi. Hech qachon natijani to'qima."*

Biz sinovdan o'tkazgan 4 ta klassik strategiya oilasi Exness XAUUSD ning real institutsional xarajatlari ostida 2014-2024 yillar davomida barqaror ustunlikka ega emasligi isbotlandi va barcha nomzodlar qat'iy rad etildi.
