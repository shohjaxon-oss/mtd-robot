"""MT5 Ijro Qatlami (Execution Layer) Testlari (2-Band).

Mock MT5 mijozi yordamida:
- Server SL/TP bilan buyurtma ijrosi
- Idempotentlik (dublikat savdolar oldini olish)
- Turli retcode'lar va retry mexanikasi
- Reconciliation (ochiq pozitsiyalarni sinxronlash)
- LiveGuard himoyasi
tekshiriladi.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest

from python_brain.execution.broker_executor import (
    MT5BrokerExecutor,
    RETCODE_DONE,
    RETCODE_REQUOTE,
    RETCODE_NO_MONEY,
)
from python_brain.risk.live_guard import LiveGuard, ACCOUNT_TRADE_MODE_DEMO, ACCOUNT_TRADE_MODE_REAL


@dataclass
class MockTick:
    ask: float = 2000.30
    bid: float = 2000.00


@dataclass
class MockOrderSendResult:
    retcode: int
    order: int = 12345
    price: float = 2000.35
    comment: str = "Request executed"


@dataclass
class MockPosition:
    ticket: int
    symbol: str
    type: int
    volume: float
    price_open: float
    sl: float
    tp: float
    comment: str
    magic: int
    time: int = 1770000000


class MockMT5Client:
    def __init__(self, trade_mode: int = ACCOUNT_TRADE_MODE_DEMO) -> None:
        self.trade_mode = trade_mode
        self.positions: List[MockPosition] = []
        self.send_order_calls: List[Dict[str, Any]] = []
        self.retcode_queue: List[int] = [RETCODE_DONE]
        self.last_err: int = 0

    def account_info(self):
        @dataclass
        class Info:
            login: int = 123456
            trade_mode: int = self.trade_mode
            server: str = "MockDemo"
        return Info()

    def symbol_info_tick(self, symbol: str):
        return MockTick()

    def positions_get(self, symbol: Optional[str] = None, ticket: Optional[int] = None):
        if ticket is not None:
            return [p for p in self.positions if p.ticket == ticket]
        return self.positions

    def order_send(self, request: Dict[str, Any]):
        self.send_order_calls.append(request)
        retcode = self.retcode_queue.pop(0) if self.retcode_queue else RETCODE_DONE
        return MockOrderSendResult(retcode=retcode, order=99999, price=request["price"])

    def last_error(self):
        return self.last_err


def test_order_send_with_server_sl_tp():
    """Serverda SL va TP bilan buyurtma berilishi va slippage hisoblanishi."""
    mock = MockMT5Client()
    executor = MT5BrokerExecutor(symbol="XAUUSDm", magic_number=10101, mt5_client=mock)

    res = executor.send_market_order(side="BUY", volume=0.01, sl=1990.0, tp=2020.0, comment="Test_Order_1")

    assert res.success is True
    assert res.ticket == 99999
    assert len(mock.send_order_calls) == 1

    req = mock.send_order_calls[0]
    assert req["sl"] == 1990.0
    assert req["tp"] == 2020.0
    assert req["magic"] == 10101
    assert req["comment"] == "Test_Order_1"


def test_idempotency_prevents_duplicate_order():
    """Shu magic va comment bilan pozitsiya mavjud bo'lsa, takroriy order rad etilishi."""
    mock = MockMT5Client()
    # Brokerda allaqachon ochiq pozitsiya mavjud
    mock.positions.append(
        MockPosition(
            ticket=55555, symbol="XAUUSDm", type=0, volume=0.01,
            price_open=2000.0, sl=1990.0, tp=2020.0, comment="Signal_Bar_120", magic=10101
        )
    )
    executor = MT5BrokerExecutor(symbol="XAUUSDm", magic_number=10101, mt5_client=mock)

    # Aynan shu 'Signal_Bar_120' bilan yangi buyurtma yuborish
    res = executor.send_market_order(side="BUY", volume=0.01, sl=1990.0, comment="Signal_Bar_120")

    assert res.success is False
    assert "DUPLICATE_ORDER_REJECTED" in res.comment
    assert len(mock.send_order_calls) == 0  # Brokerga hech narsa yuborilmadi!


def test_requote_retry_mechanism():
    """Requote (10004) holatida qayta urinish va 2-urinishda muvaffaqiyat."""
    mock = MockMT5Client()
    mock.retcode_queue = [RETCODE_REQUOTE, RETCODE_DONE]  # 1-urinish requote, 2-urinish done
    executor = MT5BrokerExecutor(symbol="XAUUSDm", retry_delay_seconds=0.01, mt5_client=mock)

    res = executor.send_market_order(side="BUY", volume=0.01, sl=1990.0)

    assert res.success is True
    assert len(mock.send_order_calls) == 2  # 2 marta urinildi!


def test_fatal_retcode_no_retry():
    """Mablag' yetarli emas (RETCODE_NO_MONEY) da behuda qayta urinilmasdan to'xtash."""
    mock = MockMT5Client()
    mock.retcode_queue = [RETCODE_NO_MONEY]
    executor = MT5BrokerExecutor(symbol="XAUUSDm", mt5_client=mock)

    res = executor.send_market_order(side="BUY", volume=0.01, sl=1990.0)

    assert res.success is False
    assert len(mock.send_order_calls) == 1  # 1-urinishda to'xtadi


def test_reconciliation_reads_bot_positions():
    """Ishga tushganda faqat bot magic numberiga mos pozitsiyalarni ajratib olish."""
    mock = MockMT5Client()
    mock.positions = [
        MockPosition(ticket=1, symbol="XAUUSDm", type=0, volume=0.01, price_open=2000.0, sl=1990.0, tp=2020.0, comment="BotPos", magic=10101),
        MockPosition(ticket=2, symbol="XAUUSDm", type=1, volume=0.10, price_open=2010.0, sl=2020.0, tp=1990.0, comment="ManualTrade", magic=0),
    ]
    executor = MT5BrokerExecutor(symbol="XAUUSDm", magic_number=10101, mt5_client=mock)

    reconciled = executor.reconcile_open_positions()
    assert len(reconciled) == 1
    assert reconciled[0]["ticket"] == 1
    assert reconciled[0]["magic"] == 10101
