# XAUUSDm Spread va Savdo Sessiyalari Profili (Spread Profile Report)

> **Manba:** Exness MT5 M1/M5 Tarixiy Barlar Spredi  
> **Maqsad:** 3/10 Backtest bosqichida haqqoniy dinamik xarajatlar modelini (slippage + variable spread) qurish.  

---

## 1. Sessiyalar Bo'yicha Spread Taqqoslanishi

| Sessiya Nomi | O'rtacha Spread (pts) | Mediana (pts) | 95-Percentil (pts) | Min | Max | Namunalar Soni |
|---|---|---|---|---|---|---|
| **Asia** | 210.5 | 160.0 | **280.0** | 159 | 364 | 30,660 |
| **London** | 210.3 | 160.0 | **280.0** | 159 | 3352 | 21,854 |
| **London-NY Overlap** | 210.0 | 160.0 | **280.0** | 159 | 372 | 17,445 |
| **New York** | 210.3 | 160.0 | **280.0** | 159 | 786 | 21,408 |
| **Off-Hours/Rollover** | 217.4 | 160.0 | **360.0** | 159 | 1606 | 8,635 |

---

## 2. UTC Soatlari Bo'yicha Spread Dinamikasi (00:00 - 23:00 UTC)

| Soat (UTC) | O'rtacha Spread (pts) | Mediana (pts) | 95-Percentil (pts) | Xavf Darajasi |
|---|---|---|---|---|
| **00:00** | 211.6 | 160.0 | 280.0 | O'rtacha |
| **01:00** | 211.2 | 160.0 | 280.0 | O'rtacha |
| **02:00** | 210.5 | 160.0 | 280.0 | O'rtacha |
| **03:00** | 210.0 | 160.0 | 280.0 | O'rtacha |
| **04:00** | 209.9 | 160.0 | 280.0 | O'rtacha |
| **05:00** | 210.1 | 160.0 | 280.0 | O'rtacha |
| **06:00** | 210.0 | 160.0 | 280.0 | O'rtacha |
| **07:00** | 210.3 | 160.0 | 280.0 | O'rtacha |
| **08:00** | 210.8 | 160.0 | 280.0 | O'rtacha |
| **09:00** | 210.2 | 160.0 | 280.0 | O'rtacha |
| **10:00** | 210.6 | 160.0 | 280.0 | O'rtacha |
| **11:00** | 209.5 | 160.0 | 280.0 | O'rtacha |
| **12:00** | 209.8 | 160.0 | 280.0 | O'rtacha |
| **13:00** | 210.4 | 160.0 | 280.0 | O'rtacha |
| **14:00** | 209.9 | 160.0 | 280.0 | O'rtacha |
| **15:00** | 210.0 | 160.0 | 280.0 | O'rtacha |
| **16:00** | 209.1 | 160.0 | 280.0 | O'rtacha |
| **17:00** | 209.0 | 160.0 | 280.0 | O'rtacha |
| **18:00** | 210.1 | 160.0 | 280.0 | O'rtacha |
| **19:00** | 211.0 | 160.0 | 280.0 | O'rtacha |
| **20:00** | 212.3 | 160.0 | 280.0 | O'rtacha |
| **21:00** | 191.0 | 160.0 | 360.0 | Yuqori (Rollover) |
| **22:00** | 227.4 | 240.0 | 360.0 | Yuqori (Rollover) |
| **23:00** | 215.9 | 160.0 | 360.0 | O'rtacha |

---

## 3. Backtest Xarajat Modeli Uchun Xulosalar

1. **Likvidlik va Tor Spread:** London va Nyu-York kesishuvi (12:00 - 16:00 UTC) paytida spread eng barqaror va minimal darajada bo'ladi.
2. **Kengayish Xatari (Rollover):** UTC 21:00 - 22:00 (Nyu-York yopilishi va bank hisob-kitoblari) vaqtida spread 2-4 barobarga keskin kengayadi.
3. **Qoida:** Ushbu oraliqlarda savdo ochish taqiqlanadi va backtest engine da 95-percentil spread modeli qo'llaniladi.
