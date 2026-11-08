"""Turn Databento OHLCV-1m files (CME futures, e.g. NQ, ES, GC, 6E) into the same CSV format as the MT5
ExportBars script, so every backtest in this repo can read them unchanged.

Runs on your PC (or here, if you attach the downloaded files).
One-time setup:  pip install databento
Use:             python databento_bars.py "C:\\path\\to\\unzipped\\download" NQ
  -> writes NQ_PERIOD_M1.csv and NQ_PERIOD_M5.csv next to this script

Per trading session (18:00 -> 17:00 New York) only the most-traded outright contract is kept, so quarterly
rolls never mix two contracts inside a session. Spreads (calendar spreads like NQH5-NQM5) are dropped.
Output columns (same as ExportBars): time_server, time_utc_approx, open, high, low, close, spread_points
  time_server = New York time + 7h  (so the repo's "ET = server - 7h" rule works)
  spread_points = 25 with point 0.01, i.e. a 0.25 spread = one NQ/ES tick (use --point 0.01 in the backtests;
                  for other products pass a tick size with --tick)
"""
import sys, glob, os, argparse
from pathlib import Path
import pandas as pd

def read(path):
    import databento as db
    store = db.DBNStore.from_file(path)
    try:
        df = store.to_df(price_type='float', pretty_ts=True, map_symbols=True)
    except Exception:
        df = store.to_df(price_type='float', pretty_ts=True, map_symbols=False)
    df = df.reset_index()
    if 'symbol' not in df.columns or df['symbol'].isna().all():
        df['symbol'] = df['instrument_id'].astype(str)
    ts = 'ts_event' if 'ts_event' in df.columns else df.columns[0]
    df = df.rename(columns={ts: 'ts'})[['ts', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
    return df[~df['symbol'].astype(str).str.contains('-')]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder'); ap.add_argument('name', help='output name, e.g. NQ')
    ap.add_argument('--tick', type=float, default=0.25, help='one tick in price (NQ/ES 0.25, GC 0.1, 6E 0.00005)')
    ap.add_argument('--point', type=float, default=0.01, help='point size the backtests will use')
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.folder, '**', '*.dbn*'), recursive=True))
    if not files:
        sys.exit(f'No .dbn files under {a.folder} - unzip the download first')
    df = pd.concat([read(f) for f in files], ignore_index=True)
    df['ts'] = pd.to_datetime(df['ts'], utc=True)
    et = df['ts'].dt.tz_convert('America/New_York').dt.tz_localize(None)
    df['et'] = et.dt.floor('min')
    df['session'] = (df['et'] + pd.Timedelta(hours=6)).dt.date
    top = df.groupby(['session', 'symbol'])['volume'].sum().reset_index()
    top = top.loc[top.groupby('session')['volume'].idxmax(), ['session', 'symbol']]
    df = df.merge(top, on=['session', 'symbol']).sort_values('et').drop_duplicates('et')
    sp = int(round(a.tick / a.point))
    out_dir = Path(__file__).parent
    for m in (1, 5):
        if m == 1:
            b = df[['et', 'open', 'high', 'low', 'close']].copy()
        else:
            g = df.set_index('et').resample('5min', label='left', closed='left')
            b = pd.DataFrame({'open': g['open'].first(), 'high': g['high'].max(), 'low': g['low'].min(),
                              'close': g['close'].last()}).dropna().reset_index()
        srv = b['et'] + pd.Timedelta(hours=7)
        out = pd.DataFrame({'time_server': srv.dt.strftime('%Y.%m.%d %H:%M'), 'time_utc_approx': '',
                            'open': b['open'], 'high': b['high'], 'low': b['low'], 'close': b['close'],
                            'spread_points': sp})
        p = out_dir / f'{a.name}_PERIOD_M{m}.csv'
        out.to_csv(p, index=False)
        print(f'{p.name}: {len(out):,} bars, {b["et"].iloc[0]} -> {b["et"].iloc[-1]} (New York time)')
    print('Contracts used:', ', '.join(f'{s} ({n} sessions)' for s, n in top['symbol'].value_counts().items()))

if __name__ == '__main__':
    main()
