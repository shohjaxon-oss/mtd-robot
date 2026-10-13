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

