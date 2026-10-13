# MTD-ROBOT: XAUUSD uchun MetaTrader 5 avtomatik savdo robot (Texnik Topshiriq)

> Versiya: 1.0 | Instrument: **XAUUSD** | Broker: **Exness (MT5)** | Platforma: Windows VPS
> Agent: Google Antigravity | Strategiya va nazorat: Claude

---

## 0. Asosiy tamoyillar (hamma bosqichlarda majburiy)

1. **100% winrate mavjud emas.** Maqsad winrate emas, **ijobiy kutilma + nazorat qilingan drawdown**.
2. **Kapital himoyasi birinchi, foyda ikkinchi.** Har qanday qarorda risk ustun.
3. **Martingale, grid, averaging-down, SL siz pozitsiya TAQIQLANGAN.**
4. **Har bosqich "Gate" bilan yopiladi.** Gate o'tmasa, keyingi bosqichga o'tilmaydi.
5. **Overfitting asosiy dushman.** Faqat out-of-sample va walk-forward natijalariga ishonamiz.
6. **Demo → mikro-live → masshtab.** Bosqichni o'tkazib yuborish yo'q.
7. **Sirlar (parol, API kalit) hech qachon kodda yoki gitda bo'lmaydi** (`.env`).
8. Boshqa odamlarning mablag'ini boshqarish ko'p davlatlarda **litsenziya** talab qiladi. Ishga tushirishdan oldin yuridik tekshiruv shart.

---

## 1. Maqsad va muvaffaqiyat mezonlari

### Maqsad
XAUUSD'da MT5 orqali to'liq avtomatik savdo qiladigan, o'zi pozitsiya ochadigan/yopadigan, SL/TP qo'yadigan, balansni nazorat qiladigan, yangilik va bozor rejimini hisobga oladigan, xavfsiz robot.

### Qabul mezonlari (backtest + forward)

| Ko'rsatkich | Minimal talab |
|---|---|
| Profit Factor | >= 1.4 (xarajatlar bilan) |
| Max Drawdown | <= 12% (qattiq limit 15%) |
| Sharpe | >= 1.2 |
| Recovery Factor | >= 3 |
| Savdolar soni (test) | >= 500 |
| Out-of-sample PF | In-sample PF ning kamida 70% i |
| Monte Carlo 95-percentil DD | <= 20% |
| Demo forward-test | >= 8 hafta, backtest bilan mos |

**Winrate** faqat ma'lumot uchun kuzatiladi, maqsad emas.

---

## 2. Arxitektura (Gibrid)

```
 ┌───────────────────────────── PYTHON "MIYA" ─────────────────────────────┐
 │ Data → Features → Regime → Signal → Risk Engine → Order Request         │
 │ News/Calendar filter │ Monitoring │ Logging │ Telegram                   │
 └───────────────────────────────┬─────────────────────────────────────────┘
                                 │ ZeroMQ (localhost)  /  heartbeat
 ┌───────────────────────────────▼─────────────────────────────────────────┐
 │ MQL5 EA "QO'L VA QALQON"                                                │
 │ Buyurtma ijrosi │ SL/TP majburiy │ Spread/slippage nazorati             │
 │ Mustaqil kill-switch │ Python o'lsa pozitsiyani himoyalash              │
 └───────────────────────────────┬─────────────────────────────────────────┘
                                 │
                        MetaTrader 5 (Exness)
```

**Nega gibrid:** Python tadqiqot, ML, yangilik uchun qulay. MQL5 EA esa terminal ichida ishlaydi va Python yiqilsa ham pozitsiyalarni himoya qiladi.

### Texnologiyalar
- Python 3.11+, `MetaTrader5`, `pandas`, `numpy`, `numba`, `scikit-learn`, `vectorbt` yoki o'zimizning backtest engine, `pyzmq`, `pydantic`, `pytest`, `loguru`
- MQL5 (EA), ZeroMQ (DLL kutubxona yoki fayl/socket ko'prik)
- SQLite/Parquet (ma'lumot), Telegram Bot API (ogohlantirish)
- Git (har bosqich alohida commit/tag)

### Exness va XAUUSD bo'yicha eslatmalar (tekshirilsin)
- Hisob turiga qarab symbol nomi farq qilishi mumkin (masalan `XAUUSD` yoki `XAUUSDm`). Agent MT5'dan haqiqiy nomni o'qib config'ga yozadi.
- XAUUSD OTC instrument: **haqiqiy order book (DOM) odatda yo'q.** "Book map" o'rniga tick hajmi, spread dinamikasi, volatillik va likvidlik proksilari ishlatiladi.
- Spread, komissiya, swap, kontrakt hajmi, minimal lot, stops level hisob turiga bog'liq. Ularni MT5 `symbol_info()` dan o'qib, backtest xarajat modeliga kiritamiz.
- Haftalik ochilish/yopilish va yangilik paytlarida spread keskin kengayadi, bu savdoga bevosita ta'sir qiladi.

---

## 3. Papka strukturasi

```
mtd-robot/
├─ README.md
├─ mtd-robot.md              # shu fayl (TZ)
├─ .env.example
├─ .gitignore
├─ pyproject.toml
├─ config/
│  ├─ settings.yaml          # umumiy sozlamalar
│  ├─ risk.yaml              # risk limitlari
│  └─ symbols.yaml           # XAUUSD parametrlari
├─ data/                     # raw/ processed/ (gitga kirmaydi)
├─ research/                 # notebooklar, tajribalar
├─ python_brain/
│  ├─ data/                  # yuklash, tozalash, sifat tekshiruvi
│  ├─ features/
│  ├─ regime/
│  ├─ signals/
│  ├─ news/
│  ├─ risk/
│  ├─ backtest/
│  ├─ bridge/                # EA bilan aloqa
│  ├─ monitoring/
│  └─ main.py
├─ mql5_ea/
│  ├─ MTD_Executor.mq5
│  └─ include/
├─ tests/
├─ scripts/
├─ docs/
│  ├─ decisions.md           # arxitektura qarorlari (ADR)
│  ├─ progress.md            # bosqich holati
│  └─ runbook.md
└─ logs/
```

---

## 4. 10 BOSQICHLI REJA

### 1/10 — Poydevor va spetsifikatsiyani qulflash
**Maqsad:** loyiha skeleti, muhit, qarorlar.
**Vazifalar:**
- Papka strukturasi, git, `pyproject.toml`, `.env.example`, `.gitignore`
- `config/*.yaml` shablonlari (risk limitlari boshlang'ich qiymatlar bilan)
- `docs/decisions.md`, `docs/progress.md`
- Python muhit, `MetaTrader5` ulanish smoke-testi (terminalga ulanish, hisob turi, symbol nomi, spread, kontrakt parametrlarini o'qish)
- Logging va config yuklash moduli, birinchi unit testlar

**Gate:** `pytest` yashil; MT5'ga ulanib XAUUSD `symbol_info` chiqadi; hujjatlar to'ldirilgan.

---

### 2/10 — Data layer
**Maqsad:** ishonchli, tozalangan tarixiy ma'lumot.
**Vazifalar:**
- MT5'dan M1/M5/M15/H1/H4/D1 barlar va (mumkin bo'lgan) tick ma'lumotlarini yuklash
- Sifat tekshiruvi: bo'shliqlar, dublikatlar, anomal narxlar, hafta oxiri gap'lar, vaqt zonasi (broker vaqti → UTC)
- Parquet saqlash, versiyalash, qayta yuklash skripti
- Spread tarixi va sessiyalar (Osiyo/London/Nyu-York) markirovkasi
- Iqtisodiy kalendar tarixi (manba aniqlanadi: MT5 kalendar yoki tashqi)

**Gate:** kamida 5+ yillik M1/M5 ma'lumot, sifat hisoboti (`docs/data_quality.md`), testlar.

---

### 3/10 — Backtest engine va xarajat modeli
**Maqsad:** haqqoniy, "o'zini aldamaydigan" backtest.
**Vazifalar:**
- Hodisaga asoslangan (event-driven) backtest: kirish/chiqish, SL/TP, bar ichidagi tartib (konservativ taxmin)
- Xarajatlar: spread (o'zgaruvchan), komissiya, slippage modeli, swap
- Lookahead bias va survivorship xatolariga qarshi testlar
- Metrikalar: PF, DD, Sharpe, Sortino, Recovery, expectancy, savdolar taqsimoti, oylik/yillik hisobot
- Walk-forward va Monte Carlo (savdolar tartibini aralashtirish, xarajatni oshirish) infratuzilmasi

**Gate:** ma'lum oddiy strategiya (masalan MA kesishuvi) natijalari mustaqil hisob-kitob bilan mos; lookahead testlari o'tadi.

---

### 4/10 — Strategiya tadqiqoti va validatsiya
**Maqsad:** haqiqiy ustunlik (edge) borligini isbotlash yoki rad etish.
**Vazifalar:**
- 3–5 ta mustaqil g'oya (masalan: sessiya breakout, volatillik siqilishi, trend-pullback, mean-reversion range rejimida)
- Har biri uchun: gipoteza, nega ishlashi kerak, parametrlar soni (kam bo'lsin)
- Train/Validation/Test bo'linishi, walk-forward, parametr barqarorligi xaritasi
- Monte Carlo, xarajat stress-testi (spread x2), slippage stress
- Ensemble yoki bitta eng barqaror strategiyani tanlash; ML faqat qo'shimcha filtr sifatida va qat'iy validatsiya bilan

**Gate:** 1-bo'limdagi qabul mezonlari **out-of-sample** da bajariladi. Bajarilmasa, yangi g'oyalar bilan qaytamiz. Edge topilmasa, loyiha shu yerda halol to'xtatiladi.

---

### 5/10 — Signal engine, rejim aniqlash, yangilik filtri
**Vazifalar:**
- Rejim klassifikatori: trend / range / yuqori volatillik / past likvidlik
- Signal generatori (4/10 da tanlangan strategiya) real vaqt rejimida, backtest bilan **bir xil kod**
- Yangilik filtri: yuqori ta'sirli hodisalar (NFP, CPI, FOMC, Fed nutqlari) atrofida savdo yo'q; oyna davomiyligi sozlanadi
- Spread/likvidlik filtri, sessiya filtri
- "Book map" o'rniga proksi: tick intensivligi, spread kengayishi, volatillik portlashi

**Gate:** real vaqt signallari backtest signallari bilan bir xil (replay test); filtrlar savdolar sonini oqilona kamaytiradi va PF/DD yaxshilaydi.

---

### 6/10 — Risk engine (eng muhim modul)
**Qoidalar (boshlang'ich, `risk.yaml` da):**
- Bitta savdoga risk: **0.5%** (maks 1%)
- Majburiy SL (ATR yoki tuzilmaga asoslangan), TP/chiqish mantiqi
- Kunlik zarar limiti: **-2%** → shu kun savdo to'xtaydi
- Haftalik limit: **-4%**, umumiy DD kill-switch: **-12%** → bot o'chadi, qo'lda tasdiq kerak
- Bir vaqtda maks pozitsiyalar soni, maks umumiy risk
- Lot hisoblash: balans, SL masofasi, tick value, min/max/step lot bo'yicha yaxlitlash
- Ketma-ket zarar kutish (cooldown), spread chegarasi, margin tekshiruvi
- Hamma qoidalar uchun unit va stress testlar

**Gate:** risk engine ni "buzishga" urinadigan testlar (noto'g'ri lot, uzilgan ma'lumot, spread portlashi) hammasi xavfsiz rad etiladi.

---

### 7/10 — MQL5 EA ijro qatlami va Python ko'prigi
**Vazifalar:**
- `MTD_Executor.mq5`: Python'dan buyruq qabul qilish, buyurtma ochish/o'zgartirish/yopish
- EA ichidagi **mustaqil himoya**: SL majburiyligi, spread/slippage cheklovi, kunlik limit, kill-switch, heartbeat yo'qolsa xavfsiz rejim
- Retcode'larni qayta ishlash, qayta urinish mantiqi, dublikat buyurtmalardan himoya (idempotentlik)
- Pozitsiya va hisob holatini Python'ga qaytarish, sinxronizatsiya (restart'dan keyin holatni tiklash)
- MT5 Strategy Tester'da EA ni tekshirish

**Gate:** demo hisobda uzilish stsenariylari (Python o'chishi, internet uzilishi, terminal qayta ishga tushishi) ostida pozitsiyalar himoyalangan; dublikat savdo yo'q.

---

### 8/10 — Monitoring, logging, ogohlantirish, test to'plami
**Vazifalar:**
- Strukturali loglar (har signal, qaror, rad etish sababi, ijro natijasi)
- Telegram: savdo ochildi/yopildi, limit yaqinlashdi, xato, kill-switch, kunlik hisobot
- Oddiy dashboard (balans, equity, DD, ochiq pozitsiyalar, kunlik PnL)
- Health-check va watchdog (jarayon o'lsa qayta ishga tushirish + ogohlantirish)
- To'liq test to'plami: unit, integratsiya, replay, chaos (uzilishlar)

**Gate:** 48 soat uzluksiz demo ishlash, xatosiz log, barcha ogohlantirishlar ishlaydi.

---

### 9/10 — Demo forward-test (minimum 8–12 hafta)
**Vazifalar:**
- Exness demo hisobda real vaqt rejimida ishlatish
- Haftalik hisobot: backtest bilan taqqoslash (PF, DD, savdolar soni, o'rtacha slippage va spread)
- Backtest va demo o'rtasidagi farqlarni tahlil qilish va tuzatish
- Strategiya parametrlarini **o'zgartirmasdan** kuzatish (aks holda test bekor)

**Gate:** demo natijalari backtest taxminlari doirasida (PF >= 1.2, DD limit ichida), kritik xato yo'q.

---

### 10/10 — Mikro-live, VPS, masshtablash va operatsiya
**Vazifalar:**
- Windows VPS (Exness VPS shartlari tekshirilsin yoki boshqa provayder), avto-restart, vaqt sinxronizatsiyasi
- **Mikro-live:** juda kichik haqiqiy summa (yo'qotilishi og'riqsiz) bilan 4–8 hafta
- Haqiqiy ijro sifatini o'lchash (slippage, rekvotlar, spread), kerak bo'lsa xarajat modelini yangilash
- Bosqichma-bosqich kapitalni oshirish qoidalari (faqat gate'lar bajarilsa)
- `docs/runbook.md`: favqulodda holatlar, kill-switch, qayta ishga tushirish, strategiyani o'chirish mezonlari ("strategiya o'ldi" qoidasi)
- Hisobot shaffofligi: investor/foydalanuvchilar uchun real statistika, risk ogohlantirishlari, **kafolatsiz va'dalarsiz**

**Gate:** mikro-live natijalari kutilgan diapazonda; runbook sinovdan o'tgan; yuridik masalalar hal qilingan (agar boshqalarning pulini boshqarilsa).

---

## 5. Agent ish qoidalari (Antigravity uchun)

1. **Bir vaqtda faqat bitta bosqich.** Gate o'tmaguncha keyingisiga o'tma.
2. Har bosqich oxirida `docs/progress.md` yangilanadi: nima qilindi, nima sinaldi, natijalar, ochiq muammolar.
3. Har o'zgarish uchun test yoziladi. Testsiz kod qabul qilinmaydi.
4. Faqat **haqiqiy ma'lumot va haqiqiy natijalar**. Natijani to'qima, taxmin qilma; noaniq bo'lsa, so'ra.
5. Backtest va live uchun **bir xil signal kodi**.
6. Sirlar faqat `.env` da. Hisob parolini hech qachon logga yozma.
7. Qaror qabul qilganda `docs/decisions.md` ga sababi bilan yoz.
8. Strategiyaning yaxshi natijasiga "moslashtirish" (curve-fitting) taqiqlanadi. Parametrlar kam, mantiqiy asosli bo'lsin.
9. Bosqich yakunida hisobot formati: **Bajarildi / Test natijalari / Gate holati / Xavflar / Keyingi qadam**.

---

## 6. Asosiy xavflar ro'yxati

| Xavf | Chora |
|---|---|
| Overfitting | Walk-forward, out-of-sample, kam parametr |
| Spread/slippage yangilikda | Yangilik filtri, spread limiti, EA himoyasi |
| Texnik uzilish | Heartbeat, EA mustaqil SL, VPS, watchdog |
| Strategiya eskirishi (regime change) | Monitoring, "o'chirish mezoni", qayta validatsiya |
| Backtest va live farqi | Demo + mikro-live bosqichlari |
| Broker xavfi (rekvot, stop level) | Retcode ishlovi, qayta urinish, hisob turini to'g'ri tanlash |
| Yuridik/litsenziya | Ishga tushirishdan oldin maslahat |
| Inson xatosi (sozlamani buzish) | Config validatsiyasi, o'zgarishlar logi |

---

## 7. Bosqichlar holati (progress)

- [ ] 1/10 Poydevor
- [ ] 2/10 Data layer
- [ ] 3/10 Backtest engine
- [ ] 4/10 Strategiya tadqiqoti
- [ ] 5/10 Signal, rejim, yangilik
- [ ] 6/10 Risk engine
- [ ] 7/10 MQL5 EA + ko'prik
- [ ] 8/10 Monitoring va testlar
- [ ] 9/10 Demo forward-test
- [ ] 10/10 Mikro-live va operatsiya