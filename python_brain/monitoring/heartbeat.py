"""Heartbeat emitter for Python Brain <-> MTD_Guardian EA synchronization.

Periodically updates a heartbeat file in MetaTrader 5's common file directory
(FILE_COMMON, typically %APPDATA%/MetaQuotes/Terminal/Common/Files).
The MTD_Guardian EA monitors this file. If the heartbeat expires beyond
timeout seconds, the EA enters Safe Mode.
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mtd.monitoring.heartbeat")


def get_default_common_files_dir() -> Path:
    """Returns the MetaTrader 5 Common Files directory path."""
    appdata = os.getenv("APPDATA")
    if appdata:
        common_path = Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"
        if common_path.exists():
            return common_path
    # Fallback to local state folder
    fallback = Path("data") / "state"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


class HeartbeatEmitter:
    """Writes periodic heartbeat files to FILE_COMMON directory."""

    def __init__(self, filename: str = "mtd_heartbeat.json", target_dir: Optional[Path] = None):
        self.filename = filename
        self.target_dir = Path(target_dir) if target_dir else get_default_common_files_dir()
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.target_dir / self.filename
        self.last_beat_time: float = 0.0

    def beat(self, status: str = "HEALTHY", extra_info: Optional[dict] = None) -> bool:
        """Writes current timestamp and status to the heartbeat file atomically."""
        now = time.time()
        payload = {
            "epoch": int(now),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "status": status,
            "pid": os.getpid(),
        }
        if extra_info:
            payload.update(extra_info)

        try:
            # Write to temporary file first then rename for atomic update
            temp_path = self.filepath.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            temp_path.replace(self.filepath)
            self.last_beat_time = now
            return True
        except Exception as e:
            logger.error(f"Failed to write heartbeat to {self.filepath}: {e}")
            return False

    def is_stale(self, max_delay_seconds: float = 30.0) -> bool:
        """Checks if the heartbeat file is older than max_delay_seconds."""
        if not self.filepath.exists():
            return True
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            epoch = data.get("epoch", 0)
            return (time.time() - epoch) > max_delay_seconds
        except Exception:
            return True
