//+------------------------------------------------------------------+
//| ExportBars.mq5                                                   |
//| Exports price bars for a list of symbols to CSV files, with the  |
//| broker's server time AND UTC, so signals can be checked against  |
//| real prices.                                                     |
//|                                                                  |
//| Output folder: MQL5\Files\BarsExport\                            |
//|   <SYMBOL>_<TIMEFRAME>.csv  - one file per symbol                |
//|   _export_info.txt          - server time offset + summary       |
//+------------------------------------------------------------------+
#property copyright "Alizane"
#property version   "1.00"
#property script_show_inputs

//--- Inputs (a settings box appears when you drop the script on a chart)
input string          InpSymbols   = "EURUSD,GBPUSD,XAUUSD";  // Pairs, comma-separated
input string          InpSuffix    = "";                      // Broker suffix, e.g. ".r" (blank if none)
input datetime        InpFrom      = D'2026.01.01 00:00';     // Start date
input datetime        InpTo        = D'2026.10.10 00:00';     // End date
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5;               // Timeframe

//+------------------------------------------------------------------+
void OnStart()
  {
   //--- Measure the server's offset from UTC (rounded to 15 min)
   int offset = (int)(TimeTradeServer() - TimeGMT());
   offset = (int)MathRound(offset / 900.0) * 900;
   double offsetHours = offset / 3600.0;

   string folder = "BarsExport\\";
   string summary = "";

   string parts[];
   int n = StringSplit(InpSymbols, ',', parts);
   if(n <= 0)
     {
      Alert("ExportBars: no symbols entered.");
      return;
     }

   int ok = 0, failed = 0;

   for(int i = 0; i < n; i++)
     {
      string sym = parts[i];
      StringTrimLeft(sym);
      StringTrimRight(sym);
      if(sym == "")
         continue;
      sym = sym + InpSuffix;

      //--- Make sure the symbol exists and is in Market Watch
      if(!SymbolSelect(sym, true))
        {
         summary += sym + ": NOT FOUND on this server (check spelling/suffix)\n";
         failed++;
         continue;
        }

      //--- Copy bars, retrying while the terminal downloads history
      MqlRates rates[];
      ArraySetAsSeries(rates, false);
      int got = -1;
      for(int attempt = 0; attempt < 30; attempt++)
        {
         got = CopyRates(sym, InpTimeframe, InpFrom, InpTo, rates);
         if(got > 0 && (bool)SeriesInfoInteger(sym, InpTimeframe, SERIES_SYNCHRONIZED))
            break;
         Sleep(1000);
        }

      if(got <= 0)
        {
         summary += sym + ": NO DATA (error " + IntegerToString(GetLastError()) + ")\n";
         failed++;
         continue;
        }

      int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
      string fname = folder + sym + "_" + EnumToString(InpTimeframe) + ".csv";
      int h = FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(h == INVALID_HANDLE)
        {
         summary += sym + ": could not create file (error " + IntegerToString(GetLastError()) + ")\n";
         failed++;
         continue;
        }

      FileWrite(h, "time_server", "time_utc_approx", "open", "high", "low", "close", "spread_points");
      for(int k = 0; k < got; k++)
        {
         datetime t = rates[k].time;
         FileWrite(h,
                   TimeToString(t, TIME_DATE | TIME_MINUTES),
                   TimeToString(t - offset, TIME_DATE | TIME_MINUTES),
                   DoubleToString(rates[k].open,  digits),
                   DoubleToString(rates[k].high,  digits),
                   DoubleToString(rates[k].low,   digits),
                   DoubleToString(rates[k].close, digits),
                   IntegerToString(rates[k].spread));
        }
      FileClose(h);

      summary += sym + ": " + IntegerToString(got) + " bars, "
                 + TimeToString(rates[0].time, TIME_DATE | TIME_MINUTES) + " to "
                 + TimeToString(rates[got - 1].time, TIME_DATE | TIME_MINUTES) + " (server time)\n";
      ok++;
     }

   //--- Info file: offset + per-symbol summary
   int hi = FileOpen(folder + "_export_info.txt", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(hi != INVALID_HANDLE)
     {
      FileWriteString(hi, "Exported at (server): " + TimeToString(TimeTradeServer(), TIME_DATE | TIME_SECONDS) + "\n");
      FileWriteString(hi, "Exported at (UTC):    " + TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS) + "\n");
      FileWriteString(hi, "Server offset from UTC right now: " + DoubleToString(offsetHours, 2) + " hours\n");
      FileWriteString(hi, "Note: time_utc_approx uses today's offset for every bar; daylight-saving shifts are corrected later.\n");
      FileWriteString(hi, "Server: " + AccountInfoString(ACCOUNT_SERVER) + "\n");
      FileWriteString(hi, "Timeframe: " + EnumToString(InpTimeframe) + "\n");
      FileWriteString(hi, "Max bars setting: " + IntegerToString(TerminalInfoInteger(TERMINAL_MAXBARS)) + "\n\n");
      FileWriteString(hi, summary);
      FileClose(hi);
     }

   Alert("ExportBars done: " + IntegerToString(ok) + " exported, " + IntegerToString(failed)
         + " failed. Files are in MQL5\\Files\\BarsExport (see _export_info.txt).");
  }
//+------------------------------------------------------------------+
