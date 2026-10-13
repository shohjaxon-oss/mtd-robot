"""SQLite asosidagi Persistent Risk State Store (1-Band).

Robot qayta ishga tushganda:
- Kill-switch holati
- Kunlik va haftalik realizatsiya qilingan PnL
- Eng yuqori Equity (Peak Equity)
- Ketma-ket zararlar soni va cooldown muddati
- Kunlik ochilgan savdolar soni
yo'qolib ketmasligi va diskda saqlanishini ta'minlaydi.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


DEFAULT_DB_PATH = Path("data/state/risk_state.db")


class RiskStateStore:
    """Risk holatini SQLite jadvalida saqlovchi va tiklovchi xavfsiz sinf."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Kerakli SQLite jadvallarini yaratadi."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    kill_switch_active INTEGER NOT NULL DEFAULT 0,
                    kill_switch_triggered_at TEXT,
                    kill_switch_reason TEXT,
                    daily_realized_pnl REAL NOT NULL DEFAULT 0.0,
                    weekly_realized_pnl REAL NOT NULL DEFAULT 0.0,
                    peak_equity REAL NOT NULL DEFAULT 0.0,
                    current_day TEXT,
                    current_week INTEGER,
                    daily_trades_count INTEGER NOT NULL DEFAULT 0,
                    consecutive_losses INTEGER NOT NULL DEFAULT 0,
                    cooldown_until TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    details_json TEXT
                )
                """
            )
            # Dastlabki qator mavjud bo'lmasa kiritish
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM risk_state WHERE id = 1")
            if cur.fetchone()[0] == 0:
                now_str = datetime.now(timezone.utc).isoformat()
                cur.execute(
                    """
                    INSERT INTO risk_state (id, kill_switch_active, updated_at)
                    VALUES (1, 0, ?)
                    """,
                    (now_str,),
                )
            conn.commit()

    def load_state(self) -> Dict[str, Any]:
        """Oxirgi risk holatini o'qiydi."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM risk_state WHERE id = 1")
            row = cur.fetchone()
            if row:
                return dict(row)
            return {}

    def save_state(self, state_updates: Dict[str, Any]) -> None:
        """Risk holatini atomik tarzda yangilaydi."""
        state_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        fields = [f"{k} = :{k}" for k in state_updates.keys()]
        query = f"UPDATE risk_state SET {', '.join(fields)} WHERE id = 1"

        with self._get_connection() as conn:
            conn.execute(query, state_updates)
            conn.commit()

    def log_audit(self, event_type: str, decision: str, reason: str, details_json: str = "{}") -> None:
        """Har bir muhim risk qarorini audit jadvaliga yozadi."""
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO risk_audit_log (timestamp, event_type, decision, reason, details_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now_str, event_type, decision, reason, details_json),
            )
            conn.commit()

    def activate_kill_switch(self, reason: str) -> None:
        """Kill-switch ni ishga tushiradi (diskda muhrlaydi)."""
        now_str = datetime.now(timezone.utc).isoformat()
        logger.critical(f"KILL-SWITCH ISHGA TUSHDI: {reason}")
        self.save_state({
            "kill_switch_active": 1,
            "kill_switch_triggered_at": now_str,
            "kill_switch_reason": reason,
        })
        self.log_audit("KILL_SWITCH_TRIGGERED", "BLOCKED", reason)

    trip_kill_switch = activate_kill_switch

    def is_kill_switch_active(self) -> bool:
        """Kill-switch faol yoki yo'qligini tekshiradi."""
        state = self.load_state()
        return bool(state.get("kill_switch_active", 0))

    def reset_kill_switch(self, reset_reason: str, force: bool = True) -> bool:
        """Kill-switch ni faqat qo'lda tasdiq va sabab bilan tozalaydi."""
        if not force:
            logger.warning("Kill-switch reset rad etildi: force=True bayrog'i talab qilinadi.")
            return False

        logger.warning(f"KILL-SWITCH QO'LDA TIKLANDI: {reset_reason}")
        self.save_state({
            "kill_switch_active": 0,
            "kill_switch_triggered_at": None,
            "kill_switch_reason": None,
        })
        self.log_audit("KILL_SWITCH_RESET", "RESET", reset_reason)
        return True
