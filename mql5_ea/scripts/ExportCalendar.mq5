//+------------------------------------------------------------------+
//|                                               ExportCalendar.mq5 |
//|                                  MTD-ROBOT Quantitative Systems |
//|               Exports MetaTrader 5 Economic Calendar to CSV file |
//+------------------------------------------------------------------+
#property copyright "MTD-ROBOT Quant Team"
#property link      "https://mtd-robot.local"
#property version   "1.00"
#property script_show_inputs

input string   InpCurrency     = "USD";        // Target Currency Filter
input datetime InpStartDate    = D'2020.01.01'; // Export Start Date
input string   InpFileName     = "economic_calendar.csv"; // Export File Name

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
   Print("Starting Economic Calendar export for currency: ", InpCurrency, " from: ", TimeToString(InpStartDate));
   
   datetime date_to = TimeCurrent();
   MqlCalendarValue values[];
   
   // Request calendar events history from broker server
   int count = CalendarValueHistory(values, InpStartDate, date_to, NULL, InpCurrency);
   
   if(count <= 0)
   {
      PrintFormat("CalendarValueHistory failed or returned 0 events. Error code: %d", GetLastError());
      Print("Tip: Ensure 'Allow WebRequest' and Calendar are updated in MT5 terminal.");
      return;
   }
   
   PrintFormat("Retrieved %d calendar records from MT5. Writing to CSV: %s ...", count, InpFileName);
   
   // Open CSV in MT5 Common or local Files directory (MQL5\Files\)
   int file_handle = FileOpen(InpFileName, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(file_handle == INVALID_HANDLE)
   {
      PrintFormat("Failed to open file '%s' for writing. Error code: %d", InpFileName, GetLastError());
      return;
   }
   
   // Write CSV Header
   FileWrite(file_handle, 
      "event_id", 
      "time_broker", 
      "currency", 
      "event_name", 
      "importance", 
      "actual_value", 
      "forecast_value", 
      "previous_value", 
      "revised_value"
   );
   
   int written_count = 0;
   
   for(int i = 0; i < count; i++)
   {
      MqlCalendarEvent event;
      if(!CalendarEventById(values[i].event_id, event))
         continue;
         
      // Filter by specified currency if requested
      if(StringLen(InpCurrency) > 0 && event.currency != InpCurrency)
         continue;
         
      string importance_str = "None";
      switch(event.importance)
      {
         case CALENDAR_IMPORTANCE_NONE:   importance_str = "Low"; break;
         case CALENDAR_IMPORTANCE_LOW:    importance_str = "Low"; break;
         case CALENDAR_IMPORTANCE_MODERATE: importance_str = "Medium"; break;
         case CALENDAR_IMPORTANCE_HIGH:   importance_str = "High"; break;
      }
      
      string time_str = TimeToString(values[i].time, TIME_DATE | TIME_SECONDS);
      
      FileWrite(file_handle,
         IntegerToString(values[i].event_id),
         time_str,
         event.currency,
         event.name,
         importance_str,
         DoubleToString(values[i].actual_value, 4),
         DoubleToString(values[i].forecast_value, 4),
         DoubleToString(values[i].prev_value, 4),
         DoubleToString(values[i].revised_prev_value, 4)
      );
      
      written_count++;
   }
   
   FileClose(file_handle);
   PrintFormat("SUCCESS: Exported %d economic events to '%s' (Folder: Terminal MQL5\\Files\\%s)", 
      written_count, InpFileName, InpFileName);
}
//+------------------------------------------------------------------+
