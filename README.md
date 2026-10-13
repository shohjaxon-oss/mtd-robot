# MTD-ROBOT: XAUUSD Automated Trading System (Exness MT5)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-MetaTrader%205-orange.svg)](https://www.metatrader5.com/)
[![Broker](https://img.shields.io/badge/Broker-Exness-green.svg)](https://www.exness.com/)
[![Risk](https://img.shields.io/badge/Capital%20Protection-First-critical.svg)]()

Production-grade avtomatlashtirilgan XAUUSD savdo tizimi. Loyiha qat'iy miqdoriy tahlil (quant), nol-taxmin (zero-illusion) risk menejmenti va gibrid (Python miya + MQL5 himoya qalqoni) arxitekturasi ustiga qurilgan.

---

## Asosiy Qoidalar
1. **100% winrate mavjud emas.** Bosh maqsad — ijobiy matematik kutilma (positive expectancy) va nazorat qilingan drawdown.
2. **Kapital himoyasi ustuvor.** Har doim majburiy Stop Loss (SL).
3. **Qat'iy taqiqlar:** Martingale, grid, averaging-down va SL siz pozitsiyalar mutlaqo man etiladi.
4. **Gibrid xavfsizlik:** Python tahlil/signal qilsa ham, MQL5 EA terminal ichida mustaqil ravishda har bir buyruqda SL/TP mavjudligini ta'minlaydi va avariya holatlarida kill-switch sifatida ishlaydi.
5. **Hech qanday sirlar kodda bo'lmaydi:** Barcha hisob ma'lumotlari faqat `.env` da saqlanadi.

---

## Loyiha Strukturasi
```text
mtd-robot/
├─ README.md
├─ mtd-robot.md              # Yagona texnik topshiriq (TZ)
├─ .env.example              # Konfiguratsiya shabloni
├─ .gitignore
├─ pyproject.toml            # Bog'liqliklar va paket sozlamalari
├─ config/
│  ├─ settings.yaml          # Tizim va ulanish sozlamalari
│  ├─ risk.yaml              # Risk limitlari va qoidalari
│  └─ symbols.yaml           # XAUUSD parametrlari
├─ data/                     # raw/ processed/ ma'lumotlar
├─ research/                 # Kvant tadqiqotlari va notebooklar
├─ python_brain/             # Analitika, rejim, signallar, risk dvigateli
├─ mql5_ea/                  # MQL5 himoyalangan ijro EA va kutubxonalar
├─ tests/                    # Avtomatlashtirilgan pytest to'plami
├─ scripts/                  # Smoke-test va diagnostika skriptlari
├─ docs/                     # Arxitektura qarorlari (ADR), taraqqiyot hisoboti
└─ logs/                     # Tizim loglari
```

---

## 1/10 Bosqich: Poydevor va Spetsifikatsiya
- [x] Papka strukturasi va gitkeep fayllari
- [x] `.env.example`, `.gitignore`, `pyproject.toml`, `README.md`
- [x] `config/*.yaml` qat'iy risk limitlari bilan
- [x] Pydantic asosida xatolikka murosasiz config validatsiyasi
- [x] Loguru xavfsiz logging (sirlarni niqoblash)
- [x] MT5 ulanish moduli va XAUUSD `symbol_info` diagnostikasi
- [x] Pytest to'plami (unit va mock testlar)

---

## Tez Boshlash (1-bosqich tekshiruvi)
```powershell
# 1. Virtual muhit yaratish va faollashtirish
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Bog'liqliklarni o'rnatish
pip install -e ".[dev]"

# 3. .env faylini yaratish
cp .env.example .env
# .env fayliga Exness demo hisob ma'lumotlarini kiriting

# 4. Testlarni ishga tushirish
pytest -v

# 5. MT5 ulanish tutun testini ishga tushirish
python scripts/smoke_test_mt5.py
```
