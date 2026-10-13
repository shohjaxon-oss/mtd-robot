"""Download complete available historical data from MT5 broker for XAUUSDm,
perform full quality audit, compute session spread profiles, and generate reports.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from python_brain.config_loader import load_all_configs
from python_brain.data.downloader import HistoricalDataDownloader
from python_brain.data.quality import DataQualityAuditor
from python_brain.data.session_profile import (
    compute_spread_profile,
    generate_spread_profile_report,
)
from python_brain.logger import app_logger, setup_logger
from python_brain.mt5_connect import MT5Connector


def run_pipeline() -> int:
    config = load_all_configs()
    setup_logger(log_level="INFO", mask_secrets=True)

    connector = MT5Connector(
        path=config.env.MT5_PATH,
        login=config.env.MT5_LOGIN,
        password=config.env.MT5_PASSWORD,
        server=config.env.MT5_SERVER,
    )

    if not connector.connect():
        print("[ERROR] Could not connect to MT5.")
        return 1

    symbol = "XAUUSDm"
    downloader = HistoricalDataDownloader(
        symbol=symbol,
        base_dir="data/raw",
        broker_utc_offset_hours=0.0,  # Exness is UTC+0
    )
    auditor = DataQualityAuditor(spike_atr_multiplier=6.0, max_spread_points=800.0)

    # Timeframe start years based on probe_history.py measurements:
    # D1, H4, H1: from 2014
    # M15: from 2022
    # M5: from 2025 (or earliest available)
    # M1: from 2026 (or earliest available)
    tf_configs = [
        ("D1", 2014),
        ("H4", 2014),
        ("H1", 2014),
        ("M15", 2022),
        ("M5", 2025),
        ("M1", 2026),
    ]

    quality_reports = []
    combined_m5_df = None

    for tf_name, start_year in tf_configs:
        print(f"\n>>> Downloading {symbol} [{tf_name}] from {start_year} ...")
        res = downloader.download_and_save_timeframe(tf_name, start_year=start_year)
        print(f"    Saved {res['total_bars']:,} bars across {len(res['saved_files'])} parquet chunks.")

        # Load back to run Quality Audit
        df = downloader.load_timeframe_data(tf_name)
        if not df.empty:
            q_rep = auditor.audit(df, timeframe=tf_name)
            quality_reports.append(q_rep)
            print(f"    [Audit] Total: {q_rep.total_bars:,} bars | Duplicates: {q_rep.duplicate_count} | OHLC errors: {q_rep.invalid_ohlc_count} | Clean: {q_rep.is_clean}")

            if tf_name == "M5":
                combined_m5_df = df

    # Generate docs/data_quality.md
    quality_doc = Path("docs/data_quality.md")
    quality_doc.parent.mkdir(parents=True, exist_ok=True)
    with open(quality_doc, "w", encoding="utf-8") as f:
        f.write("# XAUUSDm Ma'lumotlar Sifati Tekshiruvi (Data Quality Audit Report)\n\n")
        f.write(f"> **Broker:** Exness (`{config.env.MT5_SERVER}`)  \n")
        f.write(f"> **Tekshiruv Sanasi:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  \n")
        f.write(f"> **Qoida:** Nol-taxmin va to'liq oshkoralik (hech qanday ma'lumot jimgina tuzatilmadi).  \n\n")

        f.write("---\n\n## 1. Sifat Tekshiruvi Xulosasi\n\n")
        f.write("| TF | Jami Barlar | Oraliq (UTC) | Dublikatlar | Tartibsiz | Bo'shliqlar | OHLC Xatolari | ATR Sakrashlar | Nol Hajm | Holat |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for qr in quality_reports:
            status_badge = "✅ TOZA" if qr.is_clean else "⚠️ OGOHLANTIRISH"
            f.write(
                f"| **{qr.timeframe}** | {qr.total_bars:,} | {qr.start_time[:10]} - {qr.end_time[:10]} | "
                f"{qr.duplicate_count} | {qr.unordered_count} | {qr.unexpected_gap_count} | {qr.invalid_ohlc_count} | "
                f"{qr.spike_count} | {qr.zero_volume_count} | {status_badge} |\n"
            )

        f.write("\n---\n\n## 2. Tafsilotlar va Izohlar\n\n")
        for qr in quality_reports:
            f.write(f"### Timeframe: {qr.timeframe}\n")
            for note in qr.summary_notes:
                f.write(f"- {note}\n")
            f.write("\n")

    print(f"\n[OK] Quality audit report generated at: {quality_doc}")

    # Generate Spread Profile on M5 data
    if combined_m5_df is not None and not combined_m5_df.empty:
        print("\n>>> Computing session and hourly spread profile on M5 data...")
        hourly_stats, session_stats = compute_spread_profile(combined_m5_df)
        generate_spread_profile_report(
            hourly_stats=hourly_stats,
            session_stats=session_stats,
            output_md_path="docs/spread_profile.md",
            output_parquet_dir="data/processed",
        )
        print("    [OK] Spread profile report saved to docs/spread_profile.md and data/processed/*.parquet")

    connector.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
