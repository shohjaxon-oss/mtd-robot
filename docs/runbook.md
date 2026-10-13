# MTD-ROBOT OPERATSION RUNBOOK (Qo'llanma)

Ushbu hujjatda savdo tizimini boshqarish, MQL5 EA va skriptlarni MetaTrader 5 da kompilyatsiya qilish va operatsion jarayonlar bayon etilgan.

---

## 1. Iqtisodiy Kalendarni MT5 dan Eksport Qilish (ExportCalendar.mq5)

Python MetaTrader5 kutubxonasida rasmiy Economic Calendar API mavjud emas. Shuning uchun kalendar ma'lumotlari MT5 ichidagi `ExportCalendar.mq5` skripti orqali CSV formatiga eksport qilinadi.

### Qadamma-qadam yo'riqnoma:
1. **Faylni MetaTrader katalogiga ko'chirish:**
   - Loyihadagi `mql5_ea/scripts/ExportCalendar.mq5` faylidan nusxa oling.
   - MetaTrader 5 terminalini oching -> menyudan `File` -> `Open Data Folder` ni bosing.
   - Ochilgan papkada: `MQL5\Scripts\` katalogiga kiring va `ExportCalendar.mq5` faylini shu yerga joylashtiring.

2. **MetaEditor da kompilyatsiya qilish:**
   - MT5 da `F4` tugmasini bosing (yoki `Tools` -> `MetaQuotes Language Editor`).
   - Chap tomondagi *Navigator* panelidan `Scripts` papkasini oching va `ExportCalendar.mq5` ni tanlang.
   - Yuqoridagi **Compile** (`F7`) tugmasini bosing.
   - Pastdagi *Errors* panelida `0 errors, 0 warnings` chiqqaniga ishonch hosil qiling.

3. **Skriptni MT5 da ishga tushirish:**
   - Qaytadan MetaTrader 5 terminal oynasiga o'ting.
   - *Navigator* panelida (`Ctrl+N`) `Scripts` bo'limini yoying.
   - `ExportCalendar` skriptini ixtiyoriy chartga sudrab olib boring (drag and drop).
   - Parametrlar oynasida:
     - `InpCurrency`: `USD`
     - `InpStartDate`: `2020.01.01` (yoki kerakli boshlang'ich sana)
     - `InpFileName`: `economic_calendar.csv`
   - **OK** tugmasini bosing.

4. **Natijani olish va loyihaga nusxalash:**
   - Skript muvaffaqiyatli bajarilgach, MT5 *Experts* jurnalida `SUCCESS: Exported X economic events to 'economic_calendar.csv'` yozuvi chiqadi.
   - Fayl `MQL5\Files\economic_calendar.csv` da hosil bo'ladi.
   - Ushbu faylni loyiha ildizidagi `data/economic_calendar.csv` ga ko'chiring.
   - Python tomonida `python_brain/news/calendar_loader.py` uni avtomatik UTC formatida o'qiydi.

---

## 2. Kalendar Ma'lumotlari Chuqurligi
- MQL5 `CalendarValueHistory` Exness va MetaQuotes serverlarida **2015-yildan** boshlab barcha muhim makroiqtisodiy yangiliklarni (NFP, CPI, FOMC, Foiz stavkalari) o'z ichiga oladi.
- Bu 5/10 bosqichdagi yangiliklar filtri (news blackout filter) uchun 100% yetarlidir.

---

## 3. Haftalik M1 va Tick Arxivatorini Avtomatlashtirish (Task Scheduler)

Broker M1 va tick ma'lumotlarini faqat cheklangan muddat saqlagani sababli, `scripts/archive_recent.py` har hafta ishlab, o'zimizning mustaqil Parquet arxivimizni to'ldirib boradi.

### Windows Task Scheduler sozlash:
1. `Win + R` bosing, `taskschd.msc` deb yozing va Enter bosing.
2. O'ng paneldan **Create Basic Task...** ni tanlang:
   - **Name:** `MTD-Robot-Data-Archiver`
   - **Trigger:** `Weekly` (masalan, har Yakshanba kuni soat 20:00 da, bozor ochilishidan oldin).
   - **Action:** `Start a program`
   - **Program/script:** `C:\Users\Shokhjaxon\Documents\workspace\mtd-robot\.venv\Scripts\python.exe`
   - **Add arguments:** `scripts/archive_recent.py`
   - **Start in:** `C:\Users\Shokhjaxon\Documents\workspace\mtd-robot\`
3. **Finish** tugmasini bosing.
4. Bu vazifa har hafta avtomatik tarzda yangi M1 barlarni va millionlab ticklarni `data/archive/` papkasiga qo'shib boradi.

---

## 4. QO'RIQCHI EA (MTD_Guardian.mq5) Kompilyatsiyasi va O'rnatish

> [!IMPORTANT]
> **Kompilyatsiya haqida halol ma'lumot:**
> MetaQuotes MT5 da buyruqlar satri (headless CLI) kompilyatori sukut bo'yicha terminal papkasida mavjud emas. Shuning uchun MQL5 fayllari **MetaEditor GUI** orqali qo'lda kompilyatsiya qilinishi lozim.

### Qadam-baqadam o'rnatish:
1. **Faylni ko'chirish:**
   - Loyihadagi `mql5_ea/MTD_Guardian.mq5` faylidan nusxa oling.
   - MetaTrader 5 -> `File` -> `Open Data Folder` -> `MQL5\Experts\` papkasiga tashlang.
2. **MetaEditor da kompilyatsiya qilish:**
   - MT5 da `F4` bosing (MetaEditor ochiladi).
   - *Navigator* -> `Experts` -> `MTD_Guardian.mq5` ni oching.
   - `F7` (Compile) tugmasini bosing.
   - Xatolar bo'limida `0 errors, 0 warnings` ekanligini tasdiqlang.
3. **Chartga o'rnatish:**
   - MT5 da XAUUSDm grafigini oching (ixtiyoriy timeframe).
   - Navigator panelida `Experts` -> `MTD_Guardian` ni chartga sudrab tashlang.
   - "Common" bo'limida `Allow Algo Trading` katakchasini belgilang.
   - Parametrlarni tekshiring:
     - `InpHeartbeatTimeoutSec`: `30` (Python 30s jim qolsa, Safe Mode ishga tushadi)
     - `InpSafeModeAction`: `ACTION_CLOSE_ALL` (yoki `ACTION_TIGHTEN_SL`)
     - `InpDailyLossLimitPct`: `3.0` (Kunlik equity yo'qotish limiti 3%)
     - `InpMagicNumber`: `10101`
   - **OK** bosing. Chart burchagida tabassumli belgi yoki "MTD_Guardian" yozuvi paydo bo'ladi.

---

## 5. Demo Dry-Run Sinovi (scripts/demo_dry_run.py)

Demo hisobda bitta to'liq savdo davrini (ochish, server SL/TP tekshiruvi, 3 soniya kutish, yopish) qo'lda sinash:

```powershell
.venv\Scripts\python scripts/demo_dry_run.py
```

### Kutilayotgan natija:
- `[1/5] LIVE GUARD TASDIQLANDI:` (Trade Mode: DEMO)
- `[2/5] BOZOR HOLATI:` (XAUUSDm Bid/Ask va Spread)
- `[3/5] BUYURTMA YUBORILMOQDA:` (0.01 lot, Server SL/TP)
- `[4/5] BUYURTMA BROKERDA OCHILDI:` (Ticket #, Fill narxi, Serverdagi SL/TP tasdiqlandi)
- `[5/5] POZITSIYA YOPILMOQDA:` (Muvaffaqiyatli yopildi)

---

## 6. Kill-Switch ni Qo'lda Tiklash Tartibi

Agar kunlik yoki umumiy Drawdown buzilib kill-switch ishga tushsa, savdo to'liq muzlatiladi. Uni avtomatik yoqish qat'iyan taqiqlangan.

Faqat treyder sababni tahlil qilib, xavf bartaraf etilganiga ishonch hosil qilgach, quyidagi buyruq orqali tiklaydi:

```powershell
.venv\Scripts\python scripts/reset_kill_switch.py --reason "Drawdown sababi tahlil qilindi, demo sinovni davom ettirish xavfsiz" --force
```

Audit sababi majburiy bo'lib, `data/state/risk_state.db` dagi `risk_audit_log` jadvaliga muhrlanadi.

---

## 7. 48 Soatlik Uzluksiz Demo Forward Test Yo'riqnomasi

Infratuzilmani (Live Runner + Watchdog + Guardian EA) 48 soat davomida uzluksiz sinash:

1. **Telegram sozlamalari (`.env`):**
   ```env
   TELEGRAM_BOT_TOKEN="your_bot_token"
   TELEGRAM_CHAT_ID="your_chat_id"
   ```
2. **MetaTrader 5 terminali:**
   - Exness Demo hisobiga ulangan va ochiq turishi shart.
   - `MTD_Guardian.mq5` chartga biriktirilgan bo'lishi kerak.
3. **Watchdog nazoratida ishga tushirish:**
   ```powershell
   .venv\Scripts\python scripts/watchdog.py
   ```
   - Watchdog `python_brain/main.py` jarayonini fon rejimida kuzatadi.
   - Jarayon kutilmaganda to'xtasa, Telegram ga xabar yuboradi va 5 soniyadan keyin qayta tiriltiradi (soatiga maksimal 5 marta).
   - Tizim faqat **yangi yopilgan M15 barlarda** xavfsiz quvur sinovini o'tkazadi va har sekundda MT5 `FILE_COMMON` katalogiga heartbeat yuborib turadi.

