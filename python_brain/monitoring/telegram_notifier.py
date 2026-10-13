"""Telegram notification system for MTD-ROBOT monitoring and alerting."""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger("mtd.monitoring.telegram")


class TelegramNotifier:
    """Sends structured alerts and status updates to Telegram."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        # Load environment variables if not provided
        load_dotenv()
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)

        if not self.enabled:
            logger.info("Telegram credentials not configured. Telegram alerts are disabled.")

    def send_message(self, message: str) -> bool:
        """Sends a text message via Telegram Bot API (Non-blocking failure)."""
        if not self.enabled:
            logger.debug(f"[Telegram Disabled] Message: {message}")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True
                else:
                    logger.warning(f"Telegram API returned status: {resp.status}")
                    return False
        except Exception as e:
            logger.warning(f"Failed to send Telegram notification: {e}")
            return False

    def notify_trade_opened(self, ticket: int, symbol: str, side: str, volume: float, price: float, sl: float, tp: Optional[float]):
        msg = (
            f"🟢 <b>SAVDO OCHILDI</b>\n"
            f"<b>Chipta:</b> #{ticket}\n"
            f"<b>Simvol:</b> {symbol}\n"
            f"<b>Harakat:</b> {side}\n"
            f"<b>Lot:</b> {volume}\n"
            f"<b>Narx:</b> {price}\n"
            f"<b>SL:</b> {sl}\n"
            f"<b>TP:</b> {tp or 'Yoʻq'}"
        )
        return self.send_message(msg)

    def notify_trade_closed(self, ticket: int, symbol: str, profit: float, reason: str):
        icon = "💰" if profit >= 0 else "🔻"
        msg = (
            f"{icon} <b>SAVDO YOPILDI</b>\n"
            f"<b>Chipta:</b> #{ticket}\n"
            f"<b>Simvol:</b> {symbol}\n"
            f"<b>Foyda/Zarar:</b> ${profit:+.2f}\n"
            f"<b>Sabab:</b> {reason}"
        )
        return self.send_message(msg)

    def notify_kill_switch(self, reason: str):
        msg = (
            f"🚨 <b>KILL-SWITCH ISHGA TUSHDI!</b> 🚨\n"
            f"Savdo butunlay to'xtatildi.\n"
            f"<b>Sabab:</b> {reason}\n"
            f"<i>Qayta yoqish uchun: python scripts/reset_kill_switch.py talab qilinadi.</i>"
        )
        return self.send_message(msg)

    def notify_limit_warning(self, metric: str, current: float, threshold: float):
        msg = (
            f"⚠️ <b>XAVF CHEGARASI YAQINLASHDI</b>\n"
            f"<b>Ko'rsatkich:</b> {metric}\n"
            f"<b>Joriy:</b> {current:.2f}%\n"
            f"<b>Chegara:</b> {threshold:.2f}%"
        )
        return self.send_message(msg)

    def notify_heartbeat_loss(self, last_seen_seconds: float):
        msg = (
            f"⚠️ <b>HEARTBEAT UZILISHI</b>\n"
            f"Python va MT5 o'rtasidagi aloqa {last_seen_seconds:.1f} soniyadan beri eskirgan!"
        )
        return self.send_message(msg)

    def notify_error(self, component: str, error_msg: str):
        msg = (
            f"❌ <b>XATOLIK ({component})</b>\n"
            f"<code>{error_msg}</code>"
        )
        return self.send_message(msg)

    def notify_daily_summary(self, balance: float, equity: float, pnl: float, dd_pct: float, trades_count: int):
        msg = (
            f"📊 <b>KUNLIK HISOBOT</b>\n"
            f"<b>Balans:</b> ${balance:.2f}\n"
            f"<b>Equity:</b> ${equity:.2f}\n"
            f"<b>Bugungi PnL:</b> ${pnl:+.2f}\n"
            f"<b>Kunlik DD:</b> {dd_pct:.2f}%\n"
            f"<b>Savdolar soni:</b> {trades_count}"
        )
        return self.send_message(msg)
