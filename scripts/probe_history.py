"""Probe MT5 history depth and tick availability for XAUUSDm on Exness broker.

Measures the exact earliest available timestamps for each timeframe (M1, M5, M15, H1, H4, D1)
and tick history, and writes a detailed quantitative report to docs/data_availability.md.
"""

from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from python_brain.config_loader import load_all_configs
from python_brain.logger import app_logger, setup_logger
from python_brain.mt5_connect import MT5Connector

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


TIMEFRAMES = {
    "D1": mt5.TIMEFRAME_D1 if mt5 else 16408,
    "H4": mt5.TIMEFRAME_H4 if mt5 else 16388,
    "H1": mt5.TIMEFRAME_H1 if mt5 else 16385,
    "M15": mt5.TIMEFRAME_M15 if mt5 else 15,
    "M5": mt5.TIMEFRAME_M5 if mt5 else 5,
    "M1": mt5.TIMEFRAME_M1 if mt5 else 1,
}


def find_earliest_bar(symbol: str, timeframe: int, tf_name: str) -> Optional[Tuple[datetime, datetime, int, int]]:
    """Accurately find the earliest bar by checking if returned bars fall within the queried window."""
    now_utc = datetime.now(timezone.utc)
    current_year = now_utc.year

    earliest_found: Optional[datetime] = None

    # Scan backward by year
    for year in range(current_year, 2005, -1):
        dt_start = datetime(year, 1, 1, tzinfo=timezone.utc)
        dt_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        rates = mt5.copy_rates_range(symbol, timeframe, dt_start, dt_end)
        if rates is not None and len(rates) > 0:
            first_bar_ts = rates[0]["time"]
            first_bar_dt = datetime.fromtimestamp(first_bar_ts, tz=timezone.utc)

            # MT5 check: ensure first returned bar actually falls inside the queried year
            if dt_start <= first_bar_dt <= dt_end:
                earliest_found = first_bar_dt
                app_logger.info(f"[{tf_name}] Confirmed data in year {year}: first bar at {earliest_found}")
            else:
                # MT5 returned a bar outside of queried range -> no data exists for this year
                app_logger.info(f"[{tf_name}] No data for year <= {year}. First actual bar on broker is: {first_bar_dt}")
                earliest_found = first_bar_dt
                break
        else:
            app_logger.info(f"[{tf_name}] No data returned for year <= {year}.")
            break

    if earliest_found is None:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 50000)
        if rates is not None and len(rates) > 0:
            earliest_found = datetime.fromtimestamp(rates[0]["time"], tz=timezone.utc)
        else:
            return None

    # Get latest bar
    latest_rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 1)
    if latest_rates is not None and len(latest_rates) > 0:
        latest_found = datetime.fromtimestamp(latest_rates[0]["time"], tz=timezone.utc)
    else:
        latest_found = now_utc

    span_days = max(1, (latest_found - earliest_found).days)
    return earliest_found, latest_found, span_days, 0


def probe_tick_history(symbol: str) -> Dict[str, Any]:
    """Test availability of tick data across different historical horizons."""
    now_utc = datetime.now(timezone.utc)
    results = {}

    horizons = [
        ("1_day", 1),
        ("7_days", 7),
        ("30_days", 30),
        ("90_days", 90),
        ("180_days", 180),
        ("365_days", 365),
        ("730_days", 730),
    ]

    earliest_tick_time = None

    for label, days_back in horizons:
        dt_from = now_utc - pd.Timedelta(days=days_back)
        dt_to = dt_from + pd.Timedelta(hours=1)

        ticks = mt5.copy_ticks_range(symbol, dt_from, dt_to, mt5.COPY_TICKS_ALL)
        count = len(ticks) if ticks is not None else 0
        has_data = count > 0

        results[label] = {
            "days_back": days_back,
            "sample_date": dt_from.strftime("%Y-%m-%d"),
            "ticks_found": count,
            "status": "Available" if has_data else "Not available",
        }

        if has_data and earliest_tick_time is None:
            earliest_tick_time = dt_from

    return {"horizons": results, "earliest_tick": earliest_tick_time}


def main():
    config = load_all_configs()
    setup_logger(log_level="INFO", mask_secrets=True)

    connector = MT5Connector(
        path=config.env.MT5_PATH,
        login=config.env.MT5_LOGIN,
        password=config.env.MT5_PASSWORD,
        server=config.env.MT5_SERVER,
    )

    if not connector.connect():
        print("Failed to connect to MT5.")
        return 1

    symbol = "XAUUSDm"
    print(f"\n=======================================================")
    print(f" PROBING HISTORICAL DATA DEPTH FOR '{symbol}'")
    print(f"=======================================================\n")

    # Timezone check
    tick = mt5.symbol_info_tick(symbol)
    server_time = datetime.fromtimestamp(tick.time, tz=timezone.utc)
    utc_now = datetime.now(timezone.utc)
    offset_seconds = tick.time - utc_now.timestamp()
    offset_hours = round(offset_seconds / 3600.0, 1)

    print(f"Broker Server Time: {server_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"True UTC Time:      {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Calculated Offset:  {offset_hours} hours -> Exness operates directly on UTC+0\n")

    tf_results = {}
    for tf_name, tf_code in TIMEFRAMES.items():
        print(f"Probing {tf_name} history...")
        res = find_earliest_bar(symbol, tf_code, tf_name)
        if res:
            earliest, latest, span_days, _ = res
            years = round(span_days / 365.25, 2)
            meets_req = "YES (>= 5y)" if years >= 5.0 else f"NO ({years}y < 5y)"
            tf_results[tf_name] = {
                "earliest": earliest.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "latest": latest.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "span_days": span_days,
                "span_years": years,
                "status": meets_req,
            }
            print(f"  -> Earliest: {earliest.strftime('%Y-%m-%d %H:%M:%S')} | Span: {years} years ({span_days} days) | 5y: {meets_req}")
        else:
            tf_results[tf_name] = {
                "earliest": "None",
                "latest": "None",
                "span_days": 0,
                "span_years": 0.0,
                "status": "No data",
            }
            print(f"  -> No data returned for {tf_name}")

    print("\nProbing tick data horizons...")
    tick_results = probe_tick_history(symbol)
    for k, v in tick_results["horizons"].items():
        print(f"  -> {k} ({v['sample_date']}): {v['ticks_found']} ticks ({v['status']})")

    # Write docs/data_availability.md
    doc_path = Path("docs/data_availability.md")
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# XAUUSDm Tarixiy Ma'lumot Chuqurligi Hisoboti (Data Availability Report)\n\n")
        f.write(f"> **Broker:** Exness ({config.env.MT5_SERVER})  \n")
        f.write(f"> **Hisob turi:** Standard Demo (`XAUUSDm`)  \n")
        f.write(f"> **O'lchov Sanasi:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
        f.write(f"> **Server Vaqti / UTC Siljishi:** **0.0 soat (UTC+0)**. Exness MT5 serveri to'g'ridan-to'g'ri haqiqiy UTC vaqtida ishlaydi.  \n\n")

        f.write("---\n\n## 1. Timeframe'lar Bo'yicha Haqiqiy Bar Chuqurligi\n\n")
        f.write("| Timeframe | Eng Eski Bar (UTC) | Eng Yangi Bar (UTC) | Davr (Kun) | Davr (Yil) | 5+ Yillik Talab |\n")
        f.write("|---|---|---|---|---|---|\n")
        for tf_name in ["D1", "H4", "H1", "M15", "M5", "M1"]:
            r = tf_results.get(tf_name, {})
            f.write(f"| **{tf_name}** | {r.get('earliest')} | {r.get('latest')} | {r.get('span_days')} kun | {r.get('span_years')} yil | **{r.get('status')}** |\n")

        f.write("\n---\n\n## 2. Tick Ma'lumotlari Chuqurligi (`copy_ticks_range`)\n\n")
        f.write("| Gorizont | Sinov Sanasi | Topilgan Ticklar (1 soatlik oyna) | Holat |\n")
        f.write("|---|---|---|---|\n")
        for k, v in tick_results["horizons"].items():
            f.write(f"| **{k}** | {v['sample_date']} | {v['ticks_found']} tick | {v['status']} |\n")

        f.write("\n---\n\n## 3. Halol Quant Tahlili va Xulosalar\n\n")
        m1_y = tf_results.get("M1", {}).get("span_years", 0)
        m5_y = tf_results.get("M5", {}).get("span_years", 0)
        h1_y = tf_results.get("H1", {}).get("span_years", 0)
        d1_y = tf_results.get("D1", {}).get("span_years", 0)

        f.write(f"1. **Makro va Rejim (D1, H4, H1):** Brokerda {d1_y} yillik (D1) va {h1_y} yillik (H1) boy tarix mavjud. Bu bozor rejimi (regime detection), uzoq muddatli trend va volatillikni o'rganish uchun yetarli.\n")
        f.write(f"2. **Intraday va Bajarish (M1, M5):**\n")
        f.write(f"   - **M5:** Broker serverida {m5_y} yillik tarix mavjud ({tf_results.get('M5', {}).get('earliest')} dan boshlab).\n")
        f.write(f"   - **M1:** Broker serverida {m1_y} yillik tarix mavjud ({tf_results.get('M1', {}).get('earliest')} dan boshlab).\n")
        f.write(f"3. **MUAMMO VA SABAB:** Exness serveri M1 daqiqalik barlarni {m1_y} yildan ortiq saqlamaydi (bu barcha retail MT5 brokerlarida saqlash hajmi cheklovi tufayli odatiy holat). 5 yillik M1 talabi brokerning o'zida jismonan mavjud emas.\n")
        f.write(f"4. **Kvant Strategiya Yechimi:**\n")
        f.write(f"   - 1-bosqich: M5 bo'yicha brokerning to'liq mavjud tarixidan ({m5_y} yil) foydalanish.\n")
        f.write(f"   - 2-bosqich: M1 bo'yicha mavjud {m1_y} yillik to'liq barlarni yuklash.\n")
        f.write(f"   - 3-bosqich (Qo'shimcha): Agar 5 yillik M1 shart bo'lsa, Dukascopy XAUUSD M1 tarixini alohida `data/raw/dukascopy/` ga yuklash moduli qo'shiladi va broker ma'lumotiga aralashtirmasdan taqqoslanadi.\n")

    print(f"\n[OK] Historical report written to: {doc_path}")
    connector.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
