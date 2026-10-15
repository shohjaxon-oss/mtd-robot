"""Production logging setup using Loguru with sensitive credentials masking."""

import os
import re
import sys
from pathlib import Path
from typing import Any, List, Optional
from loguru import logger


# Pattern to catch potential credentials or sensitive variables in log messages
SECRET_PATTERNS = [
    re.compile(r"(password[\"'\s:=]+)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(token[\"'\s:=]+)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(secret[\"'\s:=]+)([^\"'\s,]+)", re.IGNORECASE),
    re.compile(r"(login[\"'\s:=]+)(\d{5,})", re.IGNORECASE),
]

_known_secrets: List[str] = []


def register_secret_to_mask(secret: Optional[str]) -> None:
    """Register a specific string (like account password or API token) to be masked in logs."""
    if secret and len(str(secret).strip()) > 3:
        clean = str(secret).strip()
        if clean not in _known_secrets:
            _known_secrets.append(clean)


def mask_sensitive_text(text: str) -> str:
    """Mask known secrets and regex-matched sensitive data in text."""
    masked = text
    # Mask exact secret values
    for secret in _known_secrets:
        if secret in masked:
            masked = masked.replace(secret, "***MASKED***")

    # Mask regex matches
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub(r"\1***MASKED***", masked)

    return masked


def _log_filter(record: dict) -> bool:
    """Filter that masks sensitive content in record['message']."""
    record["message"] = mask_sensitive_text(record["message"])
    return True


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = "logs/trading.log",
    rotation: str = "10 MB",
    retention: str = "30 days",
    mask_secrets: bool = True,
    log_to_file: bool = True,
    log_file_path: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Configure Loguru logger with console and rotating file output."""
    logger.remove()

    effective_file = log_file_path or log_file
    if not log_to_file:
        effective_file = None

    # Automatically register secrets from environment variables
    if mask_secrets:
        for env_key in ["MT5_PASSWORD", "MT5_LOGIN", "TELEGRAM_BOT_TOKEN"]:
            val = os.getenv(env_key)
            if val:
                register_secret_to_mask(val)

    # Console sink
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        filter=_log_filter if mask_secrets else None,
    )

    # File sink (if specified)
    if effective_file:
        log_path = Path(effective_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            level=log_level.upper(),
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                "{name}:{function}:{line} - {message}"
            ),
            filter=_log_filter if mask_secrets else None,
        )

    logger.debug("Logger initialized successfully.")
    return logger


# Default logger instance
app_logger = logger
