//+------------------------------------------------------------------+
//|                                                 MTD_Guardian.mq5 |
//|                                Copyright 2026, MTD Robot Project |
//|                                  https://github.com/shohjaxon-oss |
//+------------------------------------------------------------------+
#property copyright "MTD Robot Project"
#property link      "https://github.com/shohjaxon-oss"
#property version   "1.00"
#property description "Mustaqil Qo'riqchi EA (Guardian). Python heartbeat va kunlik equity DD ni nazorat qiladi."
#property strict

#include <Trade\Trade.mqh>

enum ENUM_SAFE_ACTION
{
   ACTION_TIGHTEN_SL = 0, // Faqat SL ni siqish (Breakeven ga yaqinlashtirish)
   ACTION_CLOSE_ALL  = 1  // Barcha ochiq pozitsiyalarni darhol yopish
};

//--- Input parametrlari
input group "=== Heartbeat Sozlamalari ==="
input string           InpHeartbeatFile        = "mtd_heartbeat.json"; // Heartbeat fayl nomi (FILE_COMMON)
input int              InpHeartbeatTimeoutSec  = 30;                   // Heartbeat eskirish chegarasi (sekund)
input ENUM_SAFE_ACTION InpSafeModeAction       = ACTION_CLOSE_ALL;     // Eskirganda qilinadigan amal
input ulong            InpMagicNumber          = 10101;                // Nazorat qilinadigan Magic Number

input group "=== Favqulodda Himoya (Circuit Breakers) ==="
input double           InpDailyLossLimitPct    = 3.0;                  // Kunlik maksimal equity zarari (%)
input int              InpTimerIntervalSec     = 2;                    // Tekshirish davriyligi (sekund)

//--- Global o'zgaruvchilar
CTrade      g_trade;
datetime    g_current_day          = 0;
double      g_day_start_equity     = 0.0;
bool        g_daily_limit_breached = false;
bool        g_safe_mode_active     = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("MTD_Guardian ishga tushdi. Magic: ", InpMagicNumber, 
         " | Heartbeat Timeout: ", InpHeartbeatTimeoutSec, "s",
         " | Kunlik DD Limiti: ", InpDailyLossLimitPct, "%");

   g_trade.SetExpertMagicNumber(InpMagicNumber);

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   g_current_day = StructToTime(dt);
   g_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);

   EventSetTimer(InpTimerIntervalSec);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("MTD_Guardian to'xtatildi. Sabab kodi: ", reason);
}

//+------------------------------------------------------------------+
//| Timer function: Har InpTimerIntervalSec sekundda chaqiriladi    |
//+------------------------------------------------------------------+
void OnTimer()
{
   CheckDayRollover();
   CheckDailyLossLimit();
   CheckPythonHeartbeat();
}

//+------------------------------------------------------------------+
//| Kun o'zgarganda kun boshidagi equity ni yangilash                |
//+------------------------------------------------------------------+
void CheckDayRollover()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   datetime today = StructToTime(dt);

   if(today != g_current_day)
   {
      g_current_day = today;
      g_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      g_daily_limit_breached = false;
      Print("Yangi savdo kuni boshlandi. Kun boshidagi equity o'rnatildi: $", 
            DoubleToString(g_day_start_equity, 2));
   }
}

//+------------------------------------------------------------------+
//| Kunlik equity yo'qotish limitini tekshirish                      |
//+------------------------------------------------------------------+
void CheckDailyLossLimit()
{
   if(g_daily_limit_breached)
      return;

   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_day_start_equity <= 0.0)
      return;

   double dd_amount = g_day_start_equity - current_equity;
   double dd_pct = (dd_amount / g_day_start_equity) * 100.0;

   if(dd_pct >= InpDailyLossLimitPct)
   {
      g_daily_limit_breached = true;
      Alert("🚨 MTD_Guardian: KUNLIK EQUITY DRAWDOWN LIMITI BUZILDI! DD: ", 
            DoubleToString(dd_pct, 2), "% >= ", InpDailyLossLimitPct, "%. Pozitsiyalar yopilmoqda!");
      Print("KUNLIK EQUITY DRAWDOWN CHEGARASI BUZILDI! Barcha pozitsiyalar majburiy yopilmoqda.");
      CloseAllManagedPositions("DAILY_EQUITY_LIMIT_BREACH");
   }
}

//+------------------------------------------------------------------+
//| Python Brain Heartbeat faylini tekshirish (FILE_COMMON)          |
//+------------------------------------------------------------------+
void CheckPythonHeartbeat()
{
   // Agar fayl mavjud bo'lmasa yoki ochib bo'lmasa
   int handle = FileOpen(InpHeartbeatFile, FILE_READ | FILE_TXT | FILE_COMMON | FILE_SHARE_READ);
   if(handle == INVALID_HANDLE)
   {
      // Fayl hali yaratilmagan bo'lishi mumkin
      return;
   }

   string content = "";
   while(!FileIsEnding(handle))
   {
      content += FileReadString(handle);
   }
   FileClose(handle);

   // JSON ichidan epoch qiymatini topish: "epoch": 1791892800
   int pos = StringFind(content, "\"epoch\":");
   if(pos < 0)
      return;

   string after_epoch = StringSubstr(content, pos + 8);
   long beat_epoch = StringToInteger(after_epoch);
   if(beat_epoch <= 0)
      return;

   datetime now_gmt = TimeGMT();
   long diff_seconds = (long)now_gmt - beat_epoch;

   if(diff_seconds > InpHeartbeatTimeoutSec)
   {
      if(!g_safe_mode_active)
      {
         g_safe_mode_active = true;
         Alert("⚠️ MTD_Guardian: Python Heartbeat eskirgan! Orada ", diff_seconds, 
               "s kechikish. Xavfsiz rejimga o'tilmoqda.");
         Print("HEARTBEAT TIMEOUT! Oxirgi signal: ", diff_seconds, "s avval. Xavfsiz rejim.");
         
         if(InpSafeModeAction == ACTION_CLOSE_ALL)
         {
            CloseAllManagedPositions("HEARTBEAT_TIMEOUT_CLOSE");
         }
         else if(InpSafeModeAction == ACTION_TIGHTEN_SL)
         {
            TightenStopLosses();
         }
      }
   }
   else
   {
      if(g_safe_mode_active)
      {
         g_safe_mode_active = false;
         Print("Python Heartbeat tiklandi. Xavfsiz rejim bekor qilindi.");
      }
   }
}

//+------------------------------------------------------------------+
//| Faqat bizning Magic Number ga tegishli pozitsiyalarni yopish     |
//+------------------------------------------------------------------+
void CloseAllManagedPositions(string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         ulong magic = PositionGetInteger(POSITION_MAGIC);
         if(magic == InpMagicNumber)
         {
            Print("Pozitsiya majburiy yopilmoqda #", ticket, " Sabab: ", reason);
            g_trade.PositionClose(ticket);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Ochiq pozitsiyalar Stop Loss'ini foyda/breakeven ga siqish        |
//+------------------------------------------------------------------+
void TightenStopLosses()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         ulong magic = PositionGetInteger(POSITION_MAGIC);
         if(magic == InpMagicNumber)
         {
            string symbol = PositionGetString(POSITION_SYMBOL);
            double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
            double current_sl = PositionGetDouble(POSITION_SL);
            double current_tp = PositionGetDouble(POSITION_TP);
            ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

            // Agar pozitsiya foydada bo'lsa, SL ni ochilish narxiga (breakeven) ko'chirish
            if(pos_type == POSITION_TYPE_BUY)
            {
               double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
               if(bid > open_price && (current_sl < open_price || current_sl == 0.0))
               {
                  Print("SL Breakeven ga siqilmoqda #", ticket);
                  g_trade.PositionModify(ticket, open_price, current_tp);
               }
            }
            else if(pos_type == POSITION_TYPE_SELL)
            {
               double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
               if(ask < open_price && (current_sl > open_price || current_sl == 0.0))
               {
                  Print("SL Breakeven ga siqilmoqda #", ticket);
                  g_trade.PositionModify(ticket, open_price, current_tp);
               }
            }
         }
      }
   }
}
