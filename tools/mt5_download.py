"""Download bars straight from your running MetaTrader 5 terminal to CSV (no scrolling, no Export dialog).
Uses MetaQuotes' official Python package. It only READS prices - it has no trading code and needs no password:
it attaches to the MT5 terminal that is already open and logged in on this PC.

One-time setup (Windows, Command Prompt):
    pip install MetaTrader5

Use (MT5 must be open and logged in):
    python mt5_download.py USTEC M1 2023-01-01
    python mt5_download.py XAUUSD,EURUSD,GBPUSD M1 2023-01-01
    python mt5_download.py USTEC M5 2023-01-01 2026-11-07
-> writes <SYMBOL>_PERIOD_<TF>.csv next to this script, in the same format as the ExportBars script.

If you get far fewer bars than expected: MT5 -> Tools -> Options -> Charts -> "Max bars in chart" = Unlimited,
restart MT5, and run again (the terminal caps what it hands out at that number).
"""
import sys, datetime as dt
from pathlib import Path
import MetaTrader5 as mt5

TF = {'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5, 'M15': mt5.TIMEFRAME_M15, 'H1': mt5.TIMEFRAME_H1}

def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    symbols = [s.strip() for s in sys.argv[1].split(',') if s.strip()]
    tf_name = sys.argv[2].upper()
    start = dt.datetime.fromisoformat(sys.argv[3])
    end = dt.datetime.fromisoformat(sys.argv[4]) if len(sys.argv) > 4 else dt.datetime.now() + dt.timedelta(days=1)
    if not mt5.initialize():
        sys.exit(f'Could not attach to MetaTrader 5 (is it open and logged in?): {mt5.last_error()}')
    try:
        for sym in symbols:
            if not mt5.symbol_select(sym, True):
                print(f'{sym}: NOT FOUND in this broker - check the name in Market Watch'); continue
            point = mt5.symbol_info(sym).point
            rows, cur = [], start
            while cur < end:                                  # 30-day chunks keep each request small
                nxt = min(cur + dt.timedelta(days=30), end)
                r = mt5.copy_rates_range(sym, TF[tf_name], cur, nxt)
                if r is not None and len(r): rows.extend(r)
                cur = nxt
            seen, out = set(), []
            for b in rows:
                if b['time'] in seen: continue
                seen.add(b['time']); out.append(b)
            out.sort(key=lambda b: b['time'])
            p = Path(__file__).with_name(f'{sym}_PERIOD_{tf_name}.csv')
            with open(p, 'w') as f:
                f.write('time_server,time_utc_approx,open,high,low,close,spread_points\n')
                for b in out:
                    t = dt.datetime.utcfromtimestamp(int(b['time']))      # MT5 bar times are server time
                    f.write(f"{t:%Y.%m.%d %H:%M},,{b['open']},{b['high']},{b['low']},{b['close']},{int(b['spread'])}\n")
            first = dt.datetime.utcfromtimestamp(int(out[0]['time'])) if out else None
            print(f'{sym} {tf_name}: {len(out):,} bars from {first} -> {p.name}  (point {point})')
    finally:
        mt5.shutdown()

if __name__ == '__main__':
    main()
