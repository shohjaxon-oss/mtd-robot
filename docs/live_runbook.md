# MTD-ROBOT FU-M3 JONLI DEMO RUNBOOK (LIVE RUNBOOK)

Ushbu qo'llanma MTD-ROBOT tizimini Exness demo (yoki MetaQuotes-Demo) hisobida xavfsiz va ishonchli ishga tushirish, nazorat qilish va nosozliklarni bartaraf etish bo'yicha to'liq amaliy ko'rsatmadir.

---

## 1. ISHGA TUSHIRISH KETMA-KETLIGI (STARTUP SEQUENCE)

### 1-qadam: Preflight tekshiruvi (Majburiy)
Har qanday jonli savdoni boshlashdan oldin diagnostika skriptini ishga tushiring:
```powershell
.venv\Scripts\python scripts/preflight.py
```
**Kutilgan natija:**
- Barcha 12 ta band bo'yicha `[PASS]` chiqishi shart:
  * MT5 Terminal Connection: PASS
  * MT5 Account Login: PASS (Trade Mode: DEMO)
  * Algo Trading: PASS (Terminalda Algo Trading yoqilgan)
  * Symbol Visibility: PASS (XAUUSD / XAUUSDm FULL rejimida)
  * Live Spread: PASS (Joriy spread < 450 punkt)
  * Clock Drift: PASS (Sub-minute drift <= 5s)
  * Heartbeat Emitter: PASS (`mtd_heartbeat.json` yangilandi)

### 2-qadam: MT5 Terminalida MTD_Guardian EA ni o'rnatish
1. MT5 terminalida istalgan chartni (masalan, `XAUUSD, M1`) oching.
2. `MTD_Guardian.mq5` EA sini chartga tashlang.
3. Sozlamalarda:
   * **Allow Algo Trading** (Algoritmik savdoga ruxsat berish) katagiga belgi qo'ying.
   * `HeartbeatFileName`: `mtd_heartbeat.json`
   * `HeartbeatTimeoutSeconds`: `10`
4. Grafikning yuqori o'ng burchagida ko'k qalqon belgisi va "Guardian Active" statusi paydo bo'lishini tekshiring.

### 3-qadam: Botni Ishga Tushirish
```powershell
.venv\Scripts\python python_brain/main.py
```
*Eslatma: `--timeframe` argumenti FAQAT `M3` ni qabul qiladi (boshqa har qanday qiymatda xato beradi).*

---

## 2. KUTILGAN LOG QATORLARI (LOG MONITORING)

Bot har bir yangi yopilgan M3 barda bitta aniq va tushunarli diagnostika log qatorini chiqaradi:

### Signal bo'lmaganda (Oddiy holat):
```text
[BAR_EVAL] Time: 2026-10-15 12:45 UTC | O: 4150.20 H: 4152.10 L: 4149.80 C: 4151.30 | FU: NO_TREND (1/3 bullish trend candles) | Risk: N/A | Exec: IDLE
```

### Allaqachon pozitsiya ochiq bo'lganda (Bitta setup qoidasi):
```text
[BAR_EVAL] Time: 2026-10-15 12:48 UTC | O: 4151.30 H: 4153.00 L: 4150.50 C: 4152.80 | FU: FU_SELL_FORMED | Risk: SETUP_ACTIVE | Exec: SKIP
```

### Signal hosil bo'lib, buyurtmalar ochilganda:
```text
RISK APPROVED: FU 2-Leg ochilmoqda: Side=SELL, SL=4156.11, TP_A=4154.11, TP_B=4153.11
SAVDO IJRO ETILDI! Ticket: #10964928235, Fill: 4158.11, Slippage: 0.0 pts
SAVDO IJRO ETILDI! Ticket: #10964928245, Fill: 4158.11, Slippage: 0.0 pts
[BAR_EVAL] Time: 2026-10-15 12:51 UTC | O: 4152.80 H: 4158.11 L: 4151.00 C: 4153.20 | FU: SELL | Risk: APPROVED | Exec: OPENED (A: #10964928235, B: #10964928245)
```

### Leg A TP ga yetganda (Breakeven):
```text
🎯 Leg A TP bilan yopildi! Leg B (#10964928245) SL kirish narxiga (4158.11) ko'chirildi (Breakeven).
```

---

## 3. TO'XTATISH VA XAVFSIZLIK (GRACEFUL SHUTDOWN)

### Botni to'xtatish:
Terminalda oddiygina `Ctrl + C` bosing.
- Bot xavfsiz to'xtatish signalini qabul qiladi.
- Heartbeat holatini `STOPPED` ga o'tkazadi.
- MT5 bilan aloqani uzadi.
- **MUHIM:** Barcha ochiq broker pozitsiyalari serverda qattiq SL va TP bilan himoyalangan holda qoladi.

---

## 4. NOSOZLIKLAR VA ULARNI HAL QILISH (TROUBLESHOOTING)

| Xato / Alomat | Sababi | Yechim |
| :--- | :--- | :--- |
| `RETCODE 10027` | MT5 terminalida AutoTrading o'chiq | Terminalning yuqori menyusidagi **"Algo Trading"** yashil tugmasini bosing va `Tools -> Options -> Expert Advisors -> Allow Algo Trading` ni yoqing. |
| `RETCODE 10016` | Invalid stops (SL bozor narxiga juda yaqin) | Broker `stops_level` masofasi talabiga qarang. Preflight skripti buni avtomatik ko'rsatadi. |
| `RETCODE 10030` | Unsupported filling mode | Broker ushbu simvolda bu rejimni qabul qilmadi. Bot avtomatik FOK/IOC/RETURN ni tanlaydi. |
| `SOAT DRIFTI > 5s` | Kompyuter soati sinxron emas | Windows sozlamalarida `Time & Language -> Date & Time -> Sync now` tugmasini bosing. |
| `SPREAD_TOO_HIGH` | Spread ruxsat etilgan limitdan yuqori | Rollover paytida (21:00-22:00 UTC) yoki yuqori o'zgaruvchanlikda bot xavfsizlik uchun savdoni o'tkazib yuboradi. Limit: 450 pt. |
| `SETUP_SKIPPED_ENTRY_DELAY` | Bar ochilishidan 5s o'tib ketgan | Bot yangi bar ochilgandan so'ng darhol kirmasa, slippage xavfini oldini olish uchun kechikkan signalni o'tkazib yuboradi. |

---

## 5. DIAGNOSTIKA BUYRUQLARI

1. **Preflight sinovi:**
   ```powershell
   .venv\Scripts\python scripts/preflight.py
   ```
2. **Oxirgi 5 kunda nega pozitsiya ochilmaganini tahlil qilish (Signal Replay):**
   ```powershell
   .venv\Scripts\python scripts/replay_signals.py --days 5
   ```
3. **Qo'lda bitta to'liq 2-leg sinovini o'tkazish (Dry Run):**
   ```powershell
   .venv\Scripts\python scripts/demo_dry_run.py
   ```
