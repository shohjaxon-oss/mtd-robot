"""Qoidaga asoslangan zaxira iqtisodiy taqvim generatori (R2-5).

Broker tarixi yetarli bo'lmaganda (ERR_CALENDAR_NO_DATA holatida),
AQShning takrorlanuvchi yuqori ta'sirli (High Impact) makroiqtisodiy hodisalarini
taqvim qoidalari asosida avtomatik hosil qiladi:
1. Non-Farm Payrolls (NFP): Har oyning 1-juma kuni 12:30 / 13:30 UTC.
2. CPI (Inflyatsiya): Har oyning o'rtasidagi Chorshanba kuni 12:30 / 13:30 UTC.
3. FOMC Rate Decision: Yiliga 8 marta, Chorshanba oqshomi 18:00 / 19:00 UTC.

Cheklovlar:
- Faqat rejalashtirilgan takroriy e'lonlar uchun ishlaydi; kutilmagan favqulodda
  bayonotlarni qamrab olmaydi.
- AQSh yozgi/qishki (Daylight Saving) vaqt o'zgarishi taxminiy hisobga olingan.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List
import pandas as pd


class RuleBasedNewsCalendar:
    """Tarixiy broker kalendari bo'lmaganda zaxira yangiliklar jadvali."""

    def __init__(self, start_year: int = 2014, end_year: int = 2026) -> None:
        self.start_year = start_year
        self.end_year = end_year
        self.events: List[datetime] = self._generate_recurring_events()

    def _generate_recurring_events(self) -> List[datetime]:
        events = []
        for year in range(self.start_year, self.end_year + 1):
            for month in range(1, 13):
                # 1. NFP: Oyning birinchi Juma kuni
                # 1-sana haftaning qaysi kuni?
                first_day = datetime(year, month, 1, tzinfo=timezone.utc)
                # Friday = weekday 4 (Monday = 0)
                days_until_friday = (4 - first_day.weekday()) % 7
                nfp_day = first_day + timedelta(days=days_until_friday)
                # Yoz oylarida (mart oxiri - noyabr boshi) 12:30 UTC, qishda 13:30 UTC
                nfp_hour = 12 if (4 <= month <= 10) else 13
                events.append(datetime(year, month, nfp_day.day, nfp_hour, 30, tzinfo=timezone.utc))

                # 2. CPI: Odatda oyning 10-15 sanalari oralig'idagi 2-chorshanba
                # Wednesday = 2
                day_10 = datetime(year, month, 10, tzinfo=timezone.utc)
                days_until_wed = (2 - day_10.weekday()) % 7
                cpi_day = day_10 + timedelta(days=days_until_wed)
                cpi_hour = 12 if (4 <= month <= 10) else 13
                events.append(datetime(year, month, cpi_day.day, cpi_hour, 30, tzinfo=timezone.utc))

                # 3. FOMC: 8 ta asosiy oylar (1, 3, 5, 6, 7, 9, 11, 12)
                if month in [1, 3, 5, 6, 7, 9, 11, 12]:
                    day_15 = datetime(year, month, 15, tzinfo=timezone.utc)
                    days_until_fomc = (2 - day_15.weekday()) % 7
                    fomc_day = day_15 + timedelta(days=days_until_fomc)
                    fomc_hour = 18 if (4 <= month <= 10) else 19
                    events.append(datetime(year, month, fomc_day.day, fomc_hour, 0, tzinfo=timezone.utc))

        events.sort()
        return events

    def is_blackout(
        self,
        dt: datetime,
        before_minutes: int = 15,
        after_minutes: int = 15,
    ) -> bool:
        """Berilgan vaqt yuqori ta'sirli hodisaning xavfli oynasiga tushadimi?"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        before_delta = timedelta(minutes=before_minutes)
        after_delta = timedelta(minutes=after_minutes)

        for ev in self.events:
            if (ev - before_delta) <= dt <= (ev + after_delta):
                return True
            if ev > dt + after_delta:
                # Ro'yxat tartiblangan, uzoqqa qarab ketganda to'xtash
                break

        return False
