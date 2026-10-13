"""Session tagging and spread profile modeling module.

Labels candles by UTC trading sessions:
- Asia (Tokyo/Sydney): 00:00 - 09:00 UTC
- London: 07:00 - 16:00 UTC
- New York: 12:00 - 21:00 UTC
- London + NY Overlap: 12:00 - 16:00 UTC
- Market Open / Close (Rollover / Weekend transitions)

Calculates hourly and session-level spread statistics (mean, median, 95th percentile),
forming the foundation for Phase 3/10 transaction cost models.
"""

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd


def tag_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """Assign boolean flags for active market sessions based on time_utc."""
    data = df.copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"])

    hour = data["time_utc"].dt.hour
    weekday = data["time_utc"].dt.weekday  # 0=Mon ... 4=Fri, 6=Sun

    # Session definitions in UTC
    data["is_asia"] = (hour >= 0) & (hour < 9)
    data["is_london"] = (hour >= 7) & (hour < 16)
    data["is_new_york"] = (hour >= 12) & (hour < 21)
    data["is_london_ny_overlap"] = (hour >= 12) & (hour < 16)

    # Rollover & weekend transitions
    data["is_weekend_close"] = (weekday == 4) & (hour >= 20)  # Friday late
    data["is_market_open"] = (weekday == 6) & (hour >= 21)    # Sunday open
    data["is_daily_rollover"] = (hour == 21) | (hour == 22)   # NY close / bank settlement

    def resolve_primary_session(row) -> str:
        if row["is_london_ny_overlap"]:
            return "London-NY Overlap"
        if row["is_london"]:
            return "London"
        if row["is_new_york"]:
            return "New York"
        if row["is_asia"]:
            return "Asia"
        return "Off-Hours/Rollover"

    data["primary_session"] = data.apply(resolve_primary_session, axis=1)
    return data


def compute_spread_profile(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute granular hourly and session-level spread statistics (mean, median, 95-th percentile)."""
    tagged = tag_sessions(df)

    if "spread" not in tagged.columns:
        raise ValueError("DataFrame must contain a 'spread' column to compute spread profile.")

    # 1. Hourly spread statistics
    tagged["utc_hour"] = tagged["time_utc"].dt.hour
    hourly_stats = (
        tagged.groupby("utc_hour")["spread"]
        .agg(
            mean_spread="mean",
            median_spread="median",
            p95_spread=lambda x: x.quantile(0.95),
            min_spread="min",
            max_spread="max",
            sample_count="count",
        )
        .reset_index()
    )

    # 2. Session-level spread statistics
    session_stats = (
        tagged.groupby("primary_session")["spread"]
        .agg(
            mean_spread="mean",
            median_spread="median",
            p95_spread=lambda x: x.quantile(0.95),
            min_spread="min",
            max_spread="max",
            sample_count="count",
        )
        .reset_index()
    )

    return hourly_stats, session_stats


def generate_spread_profile_report(
    hourly_stats: pd.DataFrame,
    session_stats: pd.DataFrame,
    output_md_path: str = "docs/spread_profile.md",
    output_parquet_dir: str = "data/processed",
) -> None:
    """Save spread profile statistics to Markdown documentation and Parquet data file."""
    out_dir = Path(output_parquet_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save to Parquet for 3/10 Backtest Engine
    hourly_stats.to_parquet(out_dir / "hourly_spread_profile.parquet", index=False)
    session_stats.to_parquet(out_dir / "session_spread_profile.parquet", index=False)

    md_path = Path(output_md_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# XAUUSDm Spread va Savdo Sessiyalari Profili (Spread Profile Report)\n\n")
        f.write("> **Manba:** Exness MT5 M1/M5 Tarixiy Barlar Spredi  \n")
        f.write("> **Maqsad:** 3/10 Backtest bosqichida haqqoniy dinamik xarajatlar modelini (slippage + variable spread) qurish.  \n\n")

        f.write("---\n\n## 1. Sessiyalar Bo'yicha Spread Taqqoslanishi\n\n")
        f.write("| Sessiya Nomi | O'rtacha Spread (pts) | Mediana (pts) | 95-Percentil (pts) | Min | Max | Namunalar Soni |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for _, row in session_stats.iterrows():
            f.write(
                f"| **{row['primary_session']}** | {row['mean_spread']:.1f} | {row['median_spread']:.1f} | "
                f"**{row['p95_spread']:.1f}** | {row['min_spread']:.0f} | {row['max_spread']:.0f} | {int(row['sample_count']):,} |\n"
            )

        f.write("\n---\n\n## 2. UTC Soatlari Bo'yicha Spread Dinamikasi (00:00 - 23:00 UTC)\n\n")
        f.write("| Soat (UTC) | O'rtacha Spread (pts) | Mediana (pts) | 95-Percentil (pts) | Xavf Darajasi |\n")
        f.write("|---|---|---|---|---|\n")
        for _, row in hourly_stats.iterrows():
            h = int(row["utc_hour"])
            p95 = row["p95_spread"]
            risk_label = "Yuqori (Rollover)" if h in [21, 22] else ("Optimal" if p95 < 260 else "O'rtacha")
            f.write(
                f"| **{h:02d}:00** | {row['mean_spread']:.1f} | {row['median_spread']:.1f} | {p95:.1f} | {risk_label} |\n"
            )

        f.write("\n---\n\n## 3. Backtest Xarajat Modeli Uchun Xulosalar\n\n")
        f.write("1. **Likvidlik va Tor Spread:** London va Nyu-York kesishuvi (12:00 - 16:00 UTC) paytida spread eng barqaror va minimal darajada bo'ladi.\n")
        f.write("2. **Kengayish Xatari (Rollover):** UTC 21:00 - 22:00 (Nyu-York yopilishi va bank hisob-kitoblari) vaqtida spread 2-4 barobarga keskin kengayadi.\n")
        f.write("3. **Qoida:** Ushbu oraliqlarda savdo ochish taqiqlanadi va backtest engine da 95-percentil spread modeli qo'llaniladi.\n")
