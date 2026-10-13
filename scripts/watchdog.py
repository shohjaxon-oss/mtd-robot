"""Watchdog process for MTD-ROBOT Live Runner.

Monitors the python_brain/main.py process. If it crashes or dies unexpectedly,
sends a Telegram alert and restarts the process with exponential backoff / limit.
"""

import sys
import time
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path

from python_brain.monitoring.telegram_notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Watchdog] %(message)s",
)
logger = logging.getLogger("mtd.watchdog")


def run_watchdog(max_restarts: int = 5, window_seconds: int = 3600):
    notifier = TelegramNotifier()
    restart_timestamps = []

    script_path = Path("python_brain") / "main.py"
    python_bin = sys.executable

    logger.info(f"Starting MTD-ROBOT Watchdog. Supervising: {script_path}")
    notifier.send_message("🛡️ <b>MTD Watchdog ishga tushdi</b>\nLive Runner nazorati boshlandi.")

    while True:
        # Prune old restart timestamps outside window
        now = time.time()
        restart_timestamps = [t for t in restart_timestamps if now - t < window_seconds]

        if len(restart_timestamps) >= max_restarts:
            msg = (
                f"🚨 <b>WATCHDOG FATAL TO'XTATISH</b> 🚨\n"
                f"Live Runner 1 soat ichida {max_restarts} marta quladi.\n"
                f"Avtomatik qayta ishga tushirish to'xtatildi. Tizimni qo'lda tekshiring!"
            )
            logger.critical(msg)
            notifier.send_message(msg)
            sys.exit(1)

        logger.info("Spawning Live Runner process...")
        process = subprocess.Popen([python_bin, str(script_path)])

        exit_code = process.wait()
        logger.warning(f"Live Runner exited with code {exit_code}")

        if exit_code == 0:
            logger.info("Live Runner stopped normally (code 0). Watchdog exiting.")
            notifier.send_message("ℹ️ Live Runner normal tartibda to'xtatildi (Exit code 0).")
            break
        else:
            restart_timestamps.append(time.time())
            alert_msg = (
                f"⚠️ <b>LIVE RUNNER QULADI</b>\n"
                f"<b>Exit Code:</b> {exit_code}\n"
                f"<b>Urinish:</b> {len(restart_timestamps)}/{max_restarts}\n"
                f"5 soniyadan keyin qayta ishga tushiriladi..."
            )
            logger.error(alert_msg)
            notifier.send_message(alert_msg)
            time.sleep(5)


if __name__ == "__main__":
    run_watchdog()
