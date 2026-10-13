"""Live Guard Moduli: Haqiqiy pul hisobida savdo qilishni qat'iy taqiqlovchi xavfsizlik qalqoni.

0-Band Talabi:
- Barcha ijro kodi account.trade_mode ni tekshirsin.
- Agar hisob DEMO (ACCOUNT_TRADE_MODE_DEMO = 0) bo'lmasa va configda allow_live: false bo'lsa,
  savdo qilishdan mutlaqo bosh tortadi va favqulodda xato chiqaradi.
- Bu bayroq faqat 10/10 bosqich gate'i o'tgandan keyin qo'lda yoqiladi.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from loguru import logger


# MT5 enum konstanta qiymatlari (kutubxona import qilinmagan holatda ham ishlashi uchun)
ACCOUNT_TRADE_MODE_DEMO = 0
ACCOUNT_TRADE_MODE_CONTEST = 1
ACCOUNT_TRADE_MODE_REAL = 2


class LiveTradingBlockedError(PermissionError):
    """Real pul hisobida savdo qilish qat'iy bloklanganda yuzaga keladigan xavfsizlik xatosi."""
    pass


class LiveGuard:
    """Ijro qatlami va robotning real pul xavfiga qarshi birinchi himoya to'sig'i."""

    def __init__(self, allow_live: bool = False, require_demo: bool = True) -> None:
        self.allow_live = allow_live
        self.require_demo = require_demo

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> LiveGuard:
        safety_cfg = config.get("safety", {})
        return cls(
            allow_live=safety_cfg.get("allow_live", False),
            require_demo=safety_cfg.get("require_demo_trade_mode", True),
        )

    def verify_account(self, account_info: Any) -> bool:
        """Broker account_info obyektini tekshiradi.
        
        Agar hisob real bo'lsa yoki trade_mode demo bo'lmasa va allow_live=False bo'lsa,
        LiveTradingBlockedError ko'taradi.
        """
        if account_info is None:
            raise LiveTradingBlockedError("LIVE GUARD RAD ETDI: Account info mavjud emas (None)!")

        # trade_mode ni aniqlash (MT5 AccountInfo obyekti yoki dict)
        trade_mode = getattr(account_info, "trade_mode", None)
        if trade_mode is None and isinstance(account_info, dict):
            trade_mode = account_info.get("trade_mode")

        login = getattr(account_info, "login", None) or (account_info.get("login") if isinstance(account_info, dict) else "unknown")
        server = getattr(account_info, "server", None) or (account_info.get("server") if isinstance(account_info, dict) else "unknown")

        logger.info(f"LiveGuard tekshiruvi: Login={login}, Server={server}, TradeMode={trade_mode}, allow_live={self.allow_live}")

        # 1. Agar DEMO bo'lmasa (Real yoki Contest)
        if trade_mode != ACCOUNT_TRADE_MODE_DEMO:
            mode_name = "REAL" if trade_mode == ACCOUNT_TRADE_MODE_REAL else f"NON-DEMO({trade_mode})"
            if not self.allow_live:
                err_msg = (
                    f"XAVFSIZLIK TO'SIG'I (LIVE GUARD): Hisob {mode_name} (login: {login}) rejimida! "
                    f"Configda 'allow_live: false' o'rnatilgan. Real pul xavf ostida! "
                    f"Har qanday buyurtma va savdo faoliyati QAT'IY BLOKLANDI!"
                )
                logger.critical(err_msg)
                raise LiveTradingBlockedError(err_msg)
            else:
                logger.warning(f"DIQQAT: allow_live=True yoqilgan! Real hisobda savdo ruxsat etildi: {login}")

        # 2. Agar require_demo yoqilgan bo'lsa va trade_mode demo bo'lmasa
        if self.require_demo and trade_mode != ACCOUNT_TRADE_MODE_DEMO:
            raise LiveTradingBlockedError("XAVFSIZLIK: require_demo_trade_mode yoqilgan, faqat DEMO hisoblarga ruxsat!")

        return True
