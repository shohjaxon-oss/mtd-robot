"""MT5 Broker Ijro Qatlami (Execution Layer, 2-Band).

Talablar:
- order_send orqali buyurtma yuborish.
- SL va TP majburiy ravishda buyurtmaning o'zida (broker serverida) o'rnatiladi.
- Magic number va comment bilan markalash.
- Deviation (slippage) chegarasi (masalan, 20-30 points).
- Retcode ishlovi: requote, off quotes, no money, market closed, trade disabled va b.
- Qayta urinish (retry) mexanikasi (maksimal 3 marta).
- IDEMPOTENTLIK: yuborishdan oldin brokerda shu magic/comment bilan ochiq pozitsiya
  yoki order bor-yo'qligini tekshirish (dublikat savdolar oldini olish).
- Reconciliation: ishga tushishda brokerdagi barcha ochiq pozitsiyalarni o'qib olish.
- Pozitsiyani yopish (close_position) va SL/TP ni o'zgartirish (modify_position).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from loguru import logger

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from python_brain.backtest.models import OrderSide
from python_brain.risk.live_guard import LiveGuard


# MT5 Standart Retcode Konstantalari
RETCODE_DONE = 10009
RETCODE_PLACED = 10008
RETCODE_REQUOTE = 10004
RETCODE_OFF_QUOTES = 10021
RETCODE_NO_MONEY = 10019
RETCODE_MARKET_CLOSED = 10018
RETCODE_TRADE_DISABLED = 10017
RETCODE_TIMEOUT = 10024
RETCODE_PRICE_CHANGED = 10020

RETCODE_MAP = {
    10004: "Requote",
    10006: "Request rejected",
    10007: "Request canceled",
    10008: "Order placed",
    10009: "Order executed (Done)",
    10014: "Invalid volume",
    10015: "Invalid price",
    10016: "Invalid stops (SL/TP): SL/TP narxi joriy bozor narxiga juda yaqin yoki broker stops_level ichida",
    10017: "Trade disabled",
    10018: "Market closed",
    10019: "No money / Margin exceeded",
    10020: "Price changed",
    10021: "No quotes / Off quotes",
    10024: "Timeout",
    10027: "AutoTrading disabled by client terminal! Yoqish uchun: MT5 -> Tools -> Options -> Expert Advisors -> 'Allow Algo Trading' ni yoqing",
    10030: "Unsupported filling mode! Broker ushbu filling rejimini qo'llab-quvvatlamaydi",
}


@dataclass
class ExecutionResult:
    success: bool
    retcode: int
    comment: str
    ticket: Optional[int] = None
    volume: float = 0.0
    requested_price: float = 0.0
    fill_price: float = 0.0
    slippage_pts: float = 0.0
    slippage_usd: float = 0.0
    order_type: str = "BUY"
    time_utc: Optional[datetime] = None

    def __bool__(self) -> bool:
        return self.success

    @property
    def slippage_points(self) -> float:
        return self.slippage_pts



OrderExecutionResult = ExecutionResult


class MT5BrokerExecutor:
    """MetaTrader 5 bilan to'g'ridan-to'g'ri bog'lanuvchi ijrochi sinf."""

    def __init__(
        self,
        symbol: str = "XAUUSDm",
        magic_number: int = 10101,
        default_deviation_pts: int = 30,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        allow_live: bool = False,
        live_guard: Optional[LiveGuard] = None,
        mt5_client: Optional[Any] = None,
        slippage_points: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        self.symbol = symbol
        self.magic_number = magic_number
        self.default_deviation_pts = slippage_points if slippage_points is not None else default_deviation_pts
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.live_guard = live_guard or LiveGuard(allow_live=allow_live, require_demo=True)
        self._mt5 = mt5_client if mt5_client is not None else mt5

    def _ensure_connected(self) -> None:
        if self._mt5 is None:
            raise RuntimeError("MetaTrader5 moduli o'rnatilmagan yoki ulanmagan!")

    def reconcile_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Ishga tushishda brokerdagi botga tegishli ochiq pozitsiyalarni o'qiydi (Reconciliation)."""
        self._ensure_connected()
        sym = symbol or self.symbol
        positions = self._mt5.positions_get(symbol=sym)
        if positions is None:
            logger.warning(f"Reconciliation: {sym} bo'yicha pozitsiyalarni o'qib bo'lmadi.")
            return []

        bot_positions = []
        for pos in positions:
            # Agar magic number mos kelsa yoki barcha pozitsiyalarni ko'rish
            if getattr(pos, "magic", 0) == self.magic_number:
                bot_positions.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == 0 else "SELL",
                    "volume": pos.volume,
                    "open_price": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "comment": pos.comment,
                    "magic": pos.magic,
                    "time": datetime.fromtimestamp(pos.time, tz=timezone.utc),
                })

        logger.info(f"Reconciliation yakunlandi: {len(bot_positions)} ta ochiq pozitsiya topildi (Magic: {self.magic_number}).")
        return bot_positions

    def get_filling_mode(self) -> int:
        """Broker simvoli bo'yicha ruxsat etilgan filling mode ni dinamik aniqlaydi."""
        if self._mt5 is None or not hasattr(self._mt5, "symbol_info"):
            return 1
        sym_info = self._mt5.symbol_info(self.symbol)
        if sym_info is None:
            return 1
        modes = getattr(sym_info, "filling_mode", 0)
        # SYMBOL_FILLING_IOC = 2 -> ORDER_FILLING_IOC = 1
        # SYMBOL_FILLING_FOK = 1 -> ORDER_FILLING_FOK = 0
        if modes & 2:
            return 1  # ORDER_FILLING_IOC
        elif modes & 1:
            return 0  # ORDER_FILLING_FOK
        return 2  # ORDER_FILLING_RETURN

    def has_duplicate_order(self, comment_tag: str) -> bool:
        """Idempotentlik tekshiruvi: shu magic yoki comment bilan pozitsiya bormi?"""
        self._ensure_connected()
        positions = self._mt5.positions_get(symbol=self.symbol)
        if positions:
            for p in positions:
                if getattr(p, "magic", 0) == self.magic_number and comment_tag in getattr(p, "comment", ""):
                    logger.warning(f"IDEMPOTENT BLOKIROVKA: {comment_tag} belgili pozitsiya (# {p.ticket}) allaqachon mavjud!")
                    return True
        return False

    def send_market_order(
        self,
        side: OrderSide | str,
        volume: float,
        sl: float,
        tp: Optional[float] = None,
        comment: str = "MTD_Live",
        deviation_pts: Optional[int] = None,
    ) -> ExecutionResult:
        """Brokerga server darajasidagi SL/TP bilan bozor buyurtmasini yuboradi."""
        self._ensure_connected()

        # 0. Live Guard himoyasi
        acc_info = self._mt5.account_info()
        self.live_guard.verify_account(acc_info)

        # 1. Idempotentlik tekshiruvi
        if self.has_duplicate_order(comment_tag=comment):
            return ExecutionResult(
                success=False,
                retcode=99999,
                comment=f"DUPLICATE_ORDER_REJECTED: Tag '{comment}' allaqachon ochiq!",
                order_type=str(side),
            )

        side_str = side.value if isinstance(side, OrderSide) else str(side)
        is_buy = side_str.upper() == "BUY"

        tick = self._mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return ExecutionResult(success=False, retcode=10001, comment="TICK_NOT_AVAILABLE", order_type=side_str)

        req_price = tick.ask if is_buy else tick.bid
        order_type_mt5 = 0 if is_buy else 1  # 0 = ORDER_TYPE_BUY, 1 = ORDER_TYPE_SELL
        dev = deviation_pts if deviation_pts is not None else self.default_deviation_pts
        filling_type = self.get_filling_mode()

        request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": self.symbol,
            "volume": float(volume),
            "type": order_type_mt5,
            "price": float(req_price),
            "sl": float(sl),
            "tp": float(tp) if tp is not None else 0.0,
            "deviation": int(dev),
            "magic": int(self.magic_number),
            "comment": comment,
            "type_time": 0,  # ORDER_TIME_GTC
            "type_filling": filling_type,
        }

        # Cheklangan qayta urinish (Retry)
        last_result = None
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Buyurtma yuborilmoqda (Urinish {attempt}/{self.max_retries}): {side_str} {volume} lot @ {req_price}, SL={sl}, TP={tp}")
            try:
                result = self._mt5.order_send(request)
            except Exception as e:
                logger.error(f"order_send exception: {e}")
                return ExecutionResult(
                    success=False,
                    retcode=-1,
                    comment=f"ORDER_SEND_EXCEPTION: {e}",
                    order_type=side_str,
                )

            last_result = result

            if result is None:
                logger.error(f"order_send natijasi None qaytdi (no response from MT5 terminal)")
                # Qayta urinishdan oldin brokerda allaqachon ochilganini tekshiramiz (dublikat bo'lmasligi uchun)
                existing_positions = self._mt5.positions_get(symbol=self.symbol)
                if existing_positions:
                    for p in existing_positions:
                        if getattr(p, "magic", 0) == self.magic_number and comment in getattr(p, "comment", ""):
                            logger.success(f"Buyurtma aslida terminalda ochilgani aniqlandi! Ticket #{p.ticket}")
                            return ExecutionResult(
                                success=True,
                                retcode=RETCODE_DONE,
                                comment="EXECUTED_CONFIRMED_ON_RECONCILE",
                                ticket=p.ticket,
                                volume=p.volume,
                                requested_price=req_price,
                                fill_price=p.price_open,
                                order_type=side_str,
                                time_utc=datetime.now(timezone.utc),
                            )
                time.sleep(self.retry_delay_seconds)
                continue

            retcode = result.retcode
            logger.info(f"order_send javobi: retcode={retcode}, comment='{result.comment}'")

            # Muvaffaqiyatli ijro
            if retcode in [RETCODE_DONE, RETCODE_PLACED]:
                fill_price = result.price if result.price > 0 else req_price
                slip_diff = (fill_price - req_price) if is_buy else (req_price - fill_price)
                slip_pts = round(slip_diff / 0.001, 1)
                slip_usd = round(slip_diff * 100.0 * volume, 2)

                logger.success(
                    f"SAVDO IJRO ETILDI! Ticket: #{result.order}, Fill: {fill_price}, "
                    f"Slippage: {slip_pts} pts (${slip_usd})"
                )
                return ExecutionResult(
                    success=True,
                    retcode=retcode,
                    comment=result.comment,
                    ticket=result.order,
                    volume=volume,
                    requested_price=req_price,
                    fill_price=fill_price,
                    slippage_pts=slip_pts,
                    slippage_usd=slip_usd,
                    order_type=side_str,
                    time_utc=datetime.now(timezone.utc),
                )

            # Timeout holatida ham qayta urinishdan oldin pozitsiyalarni tekshirish
            if retcode == RETCODE_TIMEOUT:
                logger.warning(f"Timeout ({retcode}). Qayta urinishdan oldin pozitsiyalar tekshirilmoqda...")
                existing_positions = self._mt5.positions_get(symbol=self.symbol)
                if existing_positions:
                    for p in existing_positions:
                        if getattr(p, "magic", 0) == self.magic_number and comment in getattr(p, "comment", ""):
                            logger.success(f"Timeoutdan so'ng buyurtma terminalda topildi! Ticket #{p.ticket}")
                            return ExecutionResult(
                                success=True,
                                retcode=RETCODE_DONE,
                                comment="EXECUTED_CONFIRMED_AFTER_TIMEOUT",
                                ticket=p.ticket,
                                volume=p.volume,
                                requested_price=req_price,
                                fill_price=p.price_open,
                                order_type=side_str,
                                time_utc=datetime.now(timezone.utc),
                            )

            # Requote yoki Narx o'zgargan bo'lsa yangi narx bilan qayta urinish
            if retcode in [RETCODE_REQUOTE, RETCODE_PRICE_CHANGED]:
                logger.warning(f"Requote/PriceChanged ({retcode}). Yangi narx yangilanmoqda...")
                new_tick = self._mt5.symbol_info_tick(self.symbol)
                if new_tick is not None:
                    req_price = new_tick.ask if is_buy else new_tick.bid
                    request["price"] = float(req_price)
                time.sleep(self.retry_delay_seconds)
                continue

            # Agar qat'iy xatolar bo'lsa (mablag' yetarli emas, bozor yopiq, savdo taqiqlangan, invalid stops, autotrading disabled)
            if retcode in [RETCODE_NO_MONEY, RETCODE_MARKET_CLOSED, RETCODE_TRADE_DISABLED, 10016, 10027, 10030]:
                mapped = RETCODE_MAP.get(retcode, result.comment)
                logger.error(f"Tiklanmaydigan broker xatosi: retcode={retcode} -> {mapped}")
                break

            time.sleep(self.retry_delay_seconds)

        if last_result is None:
            return ExecutionResult(
                success=False,
                retcode=-1,
                comment="ORDER_SEND_FAILED: no response from MT5 terminal (connection drop)",
                order_type=side_str,
            )

        err_comment = last_result.comment if last_result else "UNKNOWN_ERROR"
        err_code = last_result.retcode if last_result else 99999
        mapped_desc = RETCODE_MAP.get(err_code, err_comment)
        return ExecutionResult(
            success=False,
            retcode=err_code,
            comment=f"ORDER_SEND_FAILED: {mapped_desc} ({err_comment})",
            order_type=side_str,
        )

    def execute_signal(self, signal: Any, volume: float) -> ExecutionResult:
        """Adapter to execute a Strategy Signal."""
        return self.send_market_order(
            side=getattr(signal, "action", "BUY"),
            volume=volume,
            sl=getattr(signal, "sl", 0.0) or 0.0,
            tp=getattr(signal, "tp", None),
            comment=getattr(signal, "comment", "MTD_Signal") or "MTD_Signal",
        )

    def get_position_by_ticket(self, ticket: int) -> Optional[Any]:
        """Returns position object from broker if exists."""
        self._ensure_connected()
        positions = self._mt5.positions_get(ticket=ticket)
        if positions and len(positions) > 0:
            return positions[0]
        return None

    def close_position(self, ticket: int, deviation_pts: Optional[int] = None) -> ExecutionResult:
        """Ochiq pozitsiyani zudlik bilan yopadi."""
        self._ensure_connected()
        positions = self._mt5.positions_get(ticket=ticket)
        if not positions:
            logger.warning(f"Yopish uchun #{ticket} pozitsiyasi topilmadi.")
            return ExecutionResult(success=False, retcode=10013, comment=f"Position #{ticket} not found")

        pos = positions[0]
        is_buy = pos.type == 0
        tick = self._mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return ExecutionResult(success=False, retcode=10001, comment="Tick not available for close")

        close_price = tick.bid if is_buy else tick.ask
        close_type = 1 if is_buy else 0  # Qarama-qarshi tomon
        dev = deviation_pts if deviation_pts is not None else self.default_deviation_pts

        request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "position": ticket,
            "symbol": self.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": float(close_price),
            "deviation": int(dev),
            "magic": int(self.magic_number),
            "comment": f"Close_{ticket}",
            "type_time": 0,
            "type_filling": self.get_filling_mode(),
        }

        res = self._mt5.order_send(request)
        if res and res.retcode in [RETCODE_DONE, RETCODE_PLACED]:
            logger.success(f"Pozitsiya #{ticket} muvaffaqiyatli yopildi! Narx: {res.price}")
            return ExecutionResult(
                success=True,
                retcode=res.retcode,
                comment=res.comment,
                ticket=ticket,
                fill_price=res.price if res.price > 0 else close_price,
            )
        err_msg = getattr(res, "comment", "Unknown order_send error")
        err_code = getattr(res, "retcode", -1) if res else -1
        logger.error(f"Pozitsiya #{ticket} yopilmadi: retcode={err_code} ({err_msg})")
        return ExecutionResult(success=False, retcode=err_code, comment=f"Failed to close: {err_msg}")

    def modify_position_sl_tp(self, ticket: int, sl: float, tp: Optional[float] = None) -> ExecutionResult:
        """Modifies Stop Loss and Take Profit of an existing open position."""
        self._ensure_connected()
        positions = self._mt5.positions_get(ticket=ticket)
        if not positions:
            logger.warning(f"Modifikatsiya uchun #{ticket} pozitsiyasi topilmadi.")
            return ExecutionResult(success=False, retcode=10013, comment=f"Position #{ticket} not found")

        pos = positions[0]
        current_tp = tp if tp is not None else pos.tp

        request = {
            "action": 6,  # TRADE_ACTION_SLTP
            "position": ticket,
            "symbol": pos.symbol,
            "sl": float(sl),
            "tp": float(current_tp),
        }

        res = self._mt5.order_send(request)
        if res and res.retcode in [RETCODE_DONE, RETCODE_PLACED, 10025]:
            logger.success(f"Pozitsiya #{ticket} SL/TP yangilandi: SL={sl}, TP={current_tp} (retcode={res.retcode})")
            return ExecutionResult(
                success=True,
                retcode=res.retcode,
                comment=res.comment,
                ticket=ticket,
            )
        err_msg = getattr(res, "comment", "Unknown order_send error")
        err_code = getattr(res, "retcode", -1) if res else -1
        logger.error(f"Pozitsiya #{ticket} SL/TP yangilanmadi: retcode={err_code} ({err_msg})")
        return ExecutionResult(success=False, retcode=err_code, comment=f"Failed to modify SL/TP: {err_msg}")

