"""Check MetaTrader 5 connection and account info."""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_brain.mt5_connect import MT5Connector

def main():
    print("=================================================================")
    print("          MTD-ROBOT MT5 CONNECTION CHECK                        ")
    print("=================================================================")
    connector = MT5Connector()
    if not connector.initialize():
        print("[XATO] MT5 terminaliga ulanib bo'lmadi! Terminal ochiqligini tekshiring.")
        return 1
    
    if not connector.login():
        print("[XATO] MT5 hisobiga kirib bo'lmadi! .env dagi login/parolni tekshiring.")
        return 1

    acc = connector.get_account_info()
    if acc is None:
        print("[XATO] Hisob ma'lumotlarini olib bo'lmadi!")
        return 1

    login = getattr(acc, "login", "N/A")
    server = getattr(acc, "server", "N/A")
    balance = getattr(acc, "balance", 0.0)
    equity = getattr(acc, "equity", 0.0)
    trade_mode = getattr(acc, "trade_mode", "N/A")
    mode_desc = "DEMO" if trade_mode in (0, "DEMO") else f"NON-DEMO ({trade_mode})"

    print(f"[MUVAFFAQIN] MT5 ga muvaffaqiyatli ulandi!")
    print(f"      Hisob raqami: #{login}")
    print(f"      Server:       {server}")
    print(f"      Balans:       ${balance:.2f}")
    print(f"      Equity:       ${equity:.2f}")
    print(f"      Rejim:        {mode_desc}")
    print("=================================================================")
    return 0

if __name__ == "__main__":
    sys.exit(main())
