"""Key-level sweep + 1m inverse FVG (owner, 8 Nov 2026). NO CRT: no 8am candle, no candle A.

Short (long = mirror), times New York:
  1. Key levels: previous day / week / month HIGH (shorts) or LOW (longs). Day = 18:00->17:00 session.
  2. Sweep: a 1m candle trades above the level inside the trading window. Each level is used once per day.
  3. Inverse FVG: the last up fair value gap (3 candles, candle 3's low above candle 1's high) made in the push into
     the sweep high (from 30 min before the level was crossed up to the highest point) is closed below by a 1m
     candle -> sell at the next 1m open. Must happen within 60 min of the level being crossed, inside the window.
  4. Stop just above the sweep high (+spread). Target 2R or 3R. Exit 15:55 if still open.
  5. One position at a time, max 2 trades a day.
"""
import sys, os, datetime as dt, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crt_core as K
T = dt.time

def signals(B, LV, idx, w0, w1, which, lookback=30, expiry=60):
    H, L, O, C, SP, Tm = B['h'], B['l'], B['o'], B['c'], B['sp'], B['t']
    win = [i for i in idx if w0 <= K.from_min(Tm[i]).time() < w1]
    if not win: return []
    lv = LV.get(K.session_key(Tm[win[0]]), {})
    out = []
    for x in which:
        for sd, key in ((-1, f'P{x}H'), (1, f'P{x}L')):
            if key not in lv: continue
            v = lv[key]
            # first cross inside the window (price must come from the other side: previous candle not already beyond)
            j = next((i for i in win if i > idx[0] and ((sd == -1 and H[i] > v and H[i - 1] <= v) or (sd == 1 and L[i] < v and L[i - 1] >= v))), None)
            if j is None: continue
            ext_i = j
            last = min(j + expiry, win[-1])
            for f in range(j, last + 1):
                if (sd == -1 and H[f] > H[ext_i]) or (sd == 1 and L[f] < L[ext_i]): ext_i = f
                if f <= ext_i: continue
                gap = None
                for i in range(max(idx[0] + 2, j - lookback), ext_i + 1):
                    if sd == -1 and L[i] > H[i - 2]: gap = H[i - 2]
                    if sd == 1 and H[i] < L[i - 2]: gap = L[i - 2]
                if gap is not None and ((sd == -1 and C[f] < gap) or (sd == 1 and C[f] > gap)):
                    if f + 1 <= win[-1]:
                        out.append(dict(i=f + 1, side=sd, level=key, lvl=v, ext_i=ext_i, cross_i=j))
                    break
    return sorted(out, key=lambda s: s['i'])

def run(B, LV, comm, target, w0=T(8, 0), w1=T(12, 0), which=('D', 'W', 'M'), skip=None, max_day=2):
    H, L, O, C, SP, Tm = B['h'], B['l'], B['o'], B['c'], B['sp'], B['t']
    trades = []
    for day, idx in K.by_day(B).items():
        if skip and day in skip: continue
        eod = [i for i in idx if K.from_min(Tm[i]).time() <= T(15, 55)]
        if not eod: continue
        last_i, busy, n = eod[-1], -1, 0
        for s in signals(B, LV, idx, w0, w1, which):
            if n >= max_day or s['i'] <= busy: continue
            sd, k0 = s['side'], s['i']
            entry = O[k0] if sd == -1 else O[k0] + SP[k0]
            stop = H[s['ext_i']] + SP[s['ext_i']] if sd == -1 else L[s['ext_i']] - SP[s['ext_i']]
            risk = sd * (entry - stop)
            if risk <= 0: continue
            tgt = entry + sd * float(target[0]) * risk
            res = None
            for k in range(k0, last_i + 1):
                sp = SP[k]
                if (sd == 1 and L[k] <= stop) or (sd == -1 and H[k] + sp >= stop): res = (k, stop, 'stop'); break
                if k > k0 and ((sd == 1 and H[k] >= tgt) or (sd == -1 and L[k] + sp <= tgt)): res = (k, tgt, 'target'); break
            if not res: res = (last_i, C[last_i] if sd == 1 else C[last_i] + SP[last_i], '15:55 close')
            k1, px, why = res
            trades.append(dict(et=str(K.from_min(Tm[k0])), side=sd, entry=entry, stop=stop, target=tgt, risk=risk, exit=why,
                               exit_et=str(K.from_min(Tm[k1])), R=(sd * (px - entry) - comm) / risk, level=s['level'],
                               lvl=s['lvl'], cross_t=str(K.from_min(Tm[s['cross_i']])), ext=H[s['ext_i']] if sd == -1 else L[s['ext_i']]))
            busy, n = k1, n + 1
    return trades
