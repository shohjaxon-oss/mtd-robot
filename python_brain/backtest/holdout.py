"""Holdout Qulfi Moduli (Overfitting oldini olish mexanizmi).

Har bir timeframe uchun ma'lumotning oxirgi 20% qismi muhrlangan (Holdout).
Standart rejimda:
- Tadqiqot, optimallashtirish va ishlab chiqish faqat birinchi 80% (Train/Dev) da amalga oshiriladi.
- Holdout qismiga ruxsat BERILMAYDI.

Faqat yakuniy tekshiruv (Production validation) uchun `--final-test` (allow_holdout=True)
orqali bir martalik ruxsat beriladi va bu holat zudlik bilan docs/holdout_log.md ga yoziladi.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import pandas as pd
from loguru import logger


HOLDOUT_RATIO = 0.20  # Oxirgi 20%
LOG_FILE_PATH = Path("docs/holdout_log.md")


class HoldoutManager:
    """Datasetni Train/Dev va Holdout qismlariga ajratuvchi va qulfni nazorat qiluvchi sinf."""

    def __init__(self, log_path: Path | str = LOG_FILE_PATH) -> None:
        self.log_path = Path(log_path)
        self._ensure_log_exists()

    def _ensure_log_exists(self) -> None:
        if not self.log_path.exists():
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            header = (
                "# Holdout Kirish Jurnali (Audit Log)\n\n"
                "Ushbu fayl muhrlangan Holdout (oxirgi 20%) ma'lumotlariga har bir kirishni qayd etadi.\n"
                "Holdout ma'lumotlari faqat strategiya to'liq tayyor bo'lgach, yakuniy tasdiqlash uchun ochiladi.\n\n"
                "| Sana (UTC) | Timeframe | Barlar Soni | Sana Oralig'i | Sabab / Strategiya | Tasdiqlovchi |\n"
                "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            )
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write(header)

    def log_holdout_access(
        self,
        timeframe: str,
        bar_count: int,
        date_range_str: str,
        reason: str,
        operator: str = "Automated Engine",
    ) -> None:
        """Holdout ochilishini audit jurnaliga yozadi."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        entry = f"| {now_str} | {timeframe} | {bar_count:,} | {date_range_str} | {reason} | {operator} |\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        logger.warning(
            f"HOLDOUT UNLOCKED! Access recorded in {self.log_path} for {timeframe}: {reason}"
        )

    def split(
        self,
        df: pd.DataFrame,
        timeframe: str,
        allow_holdout: bool = False,
        reason: str = "Final Production Validation",
    ) -> Tuple[pd.DataFrame, pd.DataFrame | None]:
        """Datasetni (Train/Dev, Holdout) ga bo'ladi.

        Args:
            df: Xronologik tartiblangan DataFrame (indeks datetime bo'lishi shart).
            timeframe: Timeframe nomi (masalan H1, M15).
            allow_holdout: True bo'lsa holdout qismi ochiladi va loglanadi. False bo'lsa Holdout=None.
            reason: Holdout ochilish sababi.

        Returns:
            Tuple[train_df, holdout_df]. allow_holdout=False bo'lsa holdout_df=None.
        """
        if df.empty:
            raise ValueError("Dataset bo'sh!")

        total_bars = len(df)
        split_idx = int(total_bars * (1.0 - HOLDOUT_RATIO))

        train_df = df.iloc[:split_idx].copy()
        raw_holdout_df = df.iloc[split_idx:].copy()

        # Sana chegaralarini aniqlash (indeks yoki time_utc ustuni bo'yicha)
        if isinstance(df.index, pd.DatetimeIndex):
            train_start = df.index[0]
            train_end = df.index[split_idx - 1]
            holdout_start = df.index[split_idx]
            holdout_end = df.index[-1]
        elif "time_utc" in df.columns:
            train_start = pd.to_datetime(train_df["time_utc"].iloc[0])
            train_end = pd.to_datetime(train_df["time_utc"].iloc[-1])
            holdout_start = pd.to_datetime(raw_holdout_df["time_utc"].iloc[0])
            holdout_end = pd.to_datetime(raw_holdout_df["time_utc"].iloc[-1])
        else:
            train_start = f"bar_0"
            train_end = f"bar_{split_idx-1}"
            holdout_start = f"bar_{split_idx}"
            holdout_end = f"bar_{total_bars-1}"

        logger.info(
            f"[{timeframe}] Jami barlar: {total_bars:,} | "
            f"Train/Dev: {len(train_df):,} ({train_start} -> {train_end}) | "
            f"Holdout: {len(raw_holdout_df):,} ({holdout_start} -> {holdout_end})"
        )

        if not allow_holdout:
            logger.info(f"[{timeframe}] Holdout QULFLANGAN (Standart rejim). Faqat Train/Dev berildi.")
            return train_df, None

        # Agar allow_holdout=True bo'lsa
        if hasattr(holdout_start, "strftime"):
            date_range_str = f"{holdout_start.strftime('%Y-%m-%d')} .. {holdout_end.strftime('%Y-%m-%d')}"
        else:
            date_range_str = f"{holdout_start} .. {holdout_end}"
        self.log_holdout_access(
            timeframe=timeframe,
            bar_count=len(raw_holdout_df),
            date_range_str=date_range_str,
            reason=reason,
        )
        return train_df, raw_holdout_df

    def get_train_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Faqat train/dev qismini xavfsiz olish."""
        train_df, _ = self.split(df, timeframe=timeframe, allow_holdout=False)
        return train_df

    def get_holdout_data(
        self, df: pd.DataFrame, timeframe: str, allow_holdout: bool, reason: str
    ) -> pd.DataFrame:
        """Holdout qismini olish. allow_holdout=False bo'lsa PermissionError tashlaydi."""
        if not allow_holdout:
            raise PermissionError(
                f"[{timeframe}] Holdout ma'lumotlariga ruxsat berilmagan! "
                "Overfittingning oldini olish uchun faqat --final-test flagi bilan ruxsat etiladi."
            )
        _, holdout_df = self.split(df, timeframe=timeframe, allow_holdout=True, reason=reason)
        assert holdout_df is not None
        return holdout_df
