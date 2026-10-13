"""LiveGuard moduli uchun testlar (0-band).

Real pul xavfini oldini oluvchi to'siqni tekshiradi:
- Real hisobda bloklanishi
- Demo hisobda ruxsat berilishi
- Config bilan ishlashi
"""

from dataclasses import dataclass
import pytest

from python_brain.risk.live_guard import (
    LiveGuard,
    LiveTradingBlockedError,
    ACCOUNT_TRADE_MODE_DEMO,
    ACCOUNT_TRADE_MODE_REAL,
    ACCOUNT_TRADE_MODE_CONTEST,
)


@dataclass
class MockAccountInfo:
    login: int
    trade_mode: int
    server: str = "Exness-Real"


def test_live_guard_blocks_real_account_by_default():
    """Real hisob berilganda allow_live=False sababli istisno ko'tarilishi shart."""
    guard = LiveGuard(allow_live=False, require_demo=True)
    real_acc = MockAccountInfo(login=888888, trade_mode=ACCOUNT_TRADE_MODE_REAL, server="Exness-Real2")

    with pytest.raises(LiveTradingBlockedError) as exc_info:
        guard.verify_account(real_acc)

    assert "REAL" in str(exc_info.value)
    assert "Real pul xavf ostida" in str(exc_info.value)


def test_live_guard_allows_demo_account():
    """Demo hisob berilganda ruxsat berilishi shart."""
    guard = LiveGuard(allow_live=False, require_demo=True)
    demo_acc = MockAccountInfo(login=123456, trade_mode=ACCOUNT_TRADE_MODE_DEMO, server="Exness-MT5Trial15")

    assert guard.verify_account(demo_acc) is True


def test_live_guard_blocks_contest_account_if_demo_required():
    """Contest hisobi ham demo bo'lmagani uchun bloklanishi kerak."""
    guard = LiveGuard(allow_live=False, require_demo=True)
    contest_acc = MockAccountInfo(login=777777, trade_mode=ACCOUNT_TRADE_MODE_CONTEST)

    with pytest.raises(LiveTradingBlockedError):
        guard.verify_account(contest_acc)


def test_live_guard_with_dict_account_info():
    """AccountInfo dictionary formatida bo'lsa ham to'g'ri ishlashi."""
    guard = LiveGuard(allow_live=False)
    real_dict = {"login": 999999, "trade_mode": ACCOUNT_TRADE_MODE_REAL, "server": "LiveServer"}

    with pytest.raises(LiveTradingBlockedError):
        guard.verify_account(real_dict)

    demo_dict = {"login": 111111, "trade_mode": ACCOUNT_TRADE_MODE_DEMO, "server": "DemoServer"}
    assert guard.verify_account(demo_dict) is True


def test_live_guard_from_config():
    """Configdan to'g'ri parametrlarni yuklash."""
    cfg = {"safety": {"allow_live": False, "require_demo_trade_mode": True}}
    guard = LiveGuard.from_config(cfg)
    assert guard.allow_live is False
    assert guard.require_demo is True
