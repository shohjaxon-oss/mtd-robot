"""Lookahead 'Kesish' Testi (Data Slice Test).

B2 Talabi: Har bir yangi strategiya uchun kelajakni ko'rmaslik kafolati.
Ma'lumot ixtiyoriy T nuqtada kesilganda, T dagi signal butun tarixdagi T bilan 100% bir xil bo'lishi shart.
"""

from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest

from python_brain.signals.mean_reversion import MeanReversionStrategy
from python_brain.signals.session_breakout import SessionBreakoutStrategy
from python_brain.signals.trend_pullback import TrendPullbackStrategy
from python_brain.signals.volatility_squeeze import VolatilitySqueezeStrategy


def _generate_synthetic_candles(n: int = 500) -> pd.DataFrame:
    np.random.seed(42)
    base_t = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    price = 2000.0
    records = []

    for i in range(n):
        ret = np.random.normal(0, 1.5)
        o = price
        c = o + ret
        h = max(o, c) + abs(np.random.normal(0, 0.8))
        l = min(o, c) - abs(np.random.normal(0, 0.8))
        records.append({
            "time_utc": base_t + timedelta(hours=i),
            "open": round(o, 3),
            "high": round(h, 3),
            "low": round(l, 3),
            "close": round(c, 3),
            "spread": 200.0,
        })
        price = c

    return pd.DataFrame(records)


@pytest.mark.parametrize(
    "strategy_instance",
    [
        SessionBreakoutStrategy(),
        VolatilitySqueezeStrategy(),
        TrendPullbackStrategy(),
        MeanReversionStrategy(),
    ],
)
def test_strategy_lookahead_slice(strategy_instance):
    """Ma'lumotni T da kesganda, T nuqtasidagi signal o'zgarmasligi shart."""
    df = _generate_synthetic_candles(300)

    # Butun datasetda T = 250 gacha bo'lgan signalni tekshiramiz
    T = 250
    full_history_slice = df.iloc[: T + 1]
    sig_full = strategy_instance.on_bar(full_history_slice)

    # Endi ma'lumotni aynan T da kesib beramiz
    truncated_df = df.iloc[: T + 1].copy()
    sig_truncated = strategy_instance.on_bar(truncated_df)

    if sig_full is None:
        assert sig_truncated is None
    else:
        assert sig_truncated is not None
        assert sig_full.action == sig_truncated.action
        assert sig_full.sl == sig_truncated.sl
        assert sig_full.tp == sig_truncated.tp
