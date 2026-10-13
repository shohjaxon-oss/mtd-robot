"""Kill-switch ni xavfsiz va qo'lda tiklash skripti (1-Band).

Foydalanish:
python scripts/reset_kill_switch.py --reason "Bozor tahlili o'tkazildi, sabab bartaraf etildi" --force
"""

import argparse
import sys
from pathlib import Path

# Loyiha ildizini PYTHONPATH ga qo'shish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from python_brain.risk.state_store import RiskStateStore


def main():
    parser = argparse.ArgumentParser(description="MTD-ROBOT Kill-Switch ni qo'lda tiklash vositasi.")
    parser.add_argument("--reason", type=str, required=True, help="Kill-switch ni tiklash sababi (majburiy audit)")
    parser.add_argument("--force", action="store_true", help="Qat'iy tasdiqlovchi bayroq")
    parser.add_argument("--db-path", type=str, default="data/state/risk_state.db", help="SQLite holat bazasi yo'li")

    args = parser.parse_args()

    if not args.force:
        logger.error("XATO: Kill-switch ni tiklash uchun --force bayrog'ini kiritish shart!")
        sys.exit(1)

    if len(args.reason.strip()) < 10:
        logger.error("XATO: Sabab (reason) kamida 10 ta belgidan iborat batafsil audit yozuvi bo'lishi shart!")
        sys.exit(1)

    store = RiskStateStore(db_path=args.db_path)
    state = store.load_state()

    if state.get("kill_switch_active", 0) == 0:
        logger.info("Kill-switch hozirda faol emas (o'chiq holatda).")
        sys.exit(0)

    logger.warning(f"Eski holat: Kill-switch faol. Sababi: {state.get('kill_switch_reason')}")
    success = store.reset_kill_switch(reset_reason=args.reason, force=True)

    if success:
        logger.success(f"MUVAFFAQIYAT: Kill-switch muvaffaqiyatli tiklandi! Sabab auditga yozildi: {args.reason}")
    else:
        logger.error("Kill-switch ni tiklashda xatolik yuz berdi!")
        sys.exit(1)


if __name__ == "__main__":
    main()
