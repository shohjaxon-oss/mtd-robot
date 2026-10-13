"""Diagnostik Vaqt va Mavsumiylik Tahlili (DIAG-01).

XAUUSD H1 Train ma'lumotlarida:
- Hafta kunlari (Dushanba..Juma) bo'yicha o'rtacha return, volatillik (ATR).
- UTC soatlari (00:00..23:00) bo'yicha o'rtacha return, diapazon (High - Low).
Natijalar docs/hypotheses.md va docs/strategy_selection.md uchun empirik dalil bo'lib xizmat qiladi.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np

from python_brain.data.downloader import HistoricalDataDownloader
from python_brain.backtest.holdout import HoldoutManager

def run_seasonality_analysis():
    downloader = HistoricalDataDownloader(symbol="XAUUSDm")
    holdout_mgr = HoldoutManager()
    
    df_h1 = downloader.load_timeframe_data("H1")
    train_h1, _ = holdout_mgr.split(df_h1, timeframe="H1", allow_holdout=False)
    
    train_h1 = train_h1.copy()
    dt = pd.to_datetime(train_h1["time_utc"])
    train_h1["ret"] = train_h1["close"] - train_h1["open"]
    train_h1["range"] = train_h1["high"] - train_h1["low"]
    train_h1["hour"] = dt.dt.hour
    train_h1["weekday"] = dt.dt.day_name()
    train_h1["day_idx"] = dt.dt.weekday
    
    # Soatlik tahlil
    hourly = train_h1.groupby("hour").agg(
        mean_ret=("ret", "mean"),
        std_ret=("ret", "std"),
        mean_range=("range", "mean"),
        count=("ret", "count")
    ).reset_index()
    
    # Kunlik tahlil
    daily = train_h1.groupby(["day_idx", "weekday"]).agg(
        mean_ret=("ret", "mean"),
        std_ret=("ret", "std"),
        mean_range=("range", "mean"),
        count=("ret", "count")
    ).reset_index()
    
    hourly.to_csv("reports/seasonality_hourly.csv", index=False)
    daily.to_csv("reports/seasonality_daily.csv", index=False)
    print("Seasonality data saved to reports/seasonality_hourly.csv and daily.csv")
    print("\n--- UTC Soatlari Bo'yicha O'rtacha Diapazon (High-Low) ---")
    print(hourly[["hour", "mean_range", "mean_ret"]].to_string(index=False))
    print("\n--- Hafta Kunlari Bo'yicha Tahlil ---")
    print(daily[["weekday", "mean_range", "mean_ret"]].to_string(index=False))

if __name__ == "__main__":
    run_seasonality_analysis()
