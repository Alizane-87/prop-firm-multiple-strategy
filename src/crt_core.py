"""CRT backtest core (rebuilt 8 Nov 2026 after a workspace reset; same rules as the earlier crt8.py).

Data: MT5 bars (Symbols -> Bars -> Export Bars, tab-separated '<DATE> <TIME> ...', or ExportBars CSV).
Broker server clock = EET with EU daylight saving -> converted to New York time (US daylight saving).

CRT (owner's rules), short shown, long = mirror, times New York:
  1. 8am 1H candle = range.
  2. Candle A: a 15m candle 09:00-11:00 trades above the 8am high and closes back inside the 8am range.
  3. Second sweep: price trades above candle A's high (no limit on how far).
  4. 1-minute entry right after the second sweep (no waiting for a close back): ifvg / choch / ob.
  5. Stop beyond the second-sweep extreme (or beyond the 1m pattern), target 2R / 3R / other side / 50%.
  6. Entry before 11:00; one trade per day; exit 15:55.
Key levels (owner, 8 Nov): 'location' — the SECOND SWEEP must trade into a previous day/week/month HIGH (shorts) or
LOW (longs): some candle between the start of the second sweep and the entry trades through the level.
"""
import csv, datetime as dt, collections, statistics

T = dt.time
EPOCH = dt.datetime(2000, 1, 1)
def to_min(t): return int((t - EPOCH).total_seconds() // 60)
def from_min(m): return EPOCH + dt.timedelta(minutes=m)

# ---------------------------------------------------------------- time conversion
def _nth_sunday(y, m, n):
    d = dt.date(y, m, 1); d += dt.timedelta(days=(6 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)

def _last_sunday(y, m):
    d = (dt.date(y, m + 1, 1) - dt.timedelta(days=1)) if m < 12 else dt.date(y, 12, 31)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)

def utc_to_et(t):
    s = dt.datetime.combine(_nth_sunday(t.year, 3, 2), T(7, 0)); e = dt.datetime.combine(_nth_sunday(t.year, 11, 1), T(6, 0))
    return t - dt.timedelta(hours=4 if s <= t < e else 5)

def server_to_et(t):
    s = dt.datetime.combine(_last_sunday(t.year, 3), T(3, 0)); e = dt.datetime.combine(_last_sunday(t.year, 10), T(4, 0))
    return utc_to_et(t - dt.timedelta(hours=3 if s <= t < e else 2))

# ---------------------------------------------------------------- data
def load(path, point):
    t, o, h, l, c, sp = [], [], [], [], [], []
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        first = f.readline(); f.seek(0)
        if '<DATE>' in first:
            rd = csv.reader(f, delimiter='\t'); next(rd)
            for r in rd:
                if len(r) < 9: continue
                et = server_to_et(dt.datetime.strptime(r[0] + ' ' + r[1][:5], '%Y.%m.%d %H:%M'))
                t.append(to_min(et)); o.append(float(r[2])); h.append(float(r[3])); l.append(float(r[4]))
                c.append(float(r[5])); sp.append(int(r[8]) * point)
        else:
            for r in csv.DictReader(f):
                et = server_to_et(dt.datetime.strptime(r['time_server'], '%Y.%m.%d %H:%M'))
                t.append(to_min(et)); o.append(float(r['open'])); h.append(float(r['high']))
                l.append(float(r['low'])); c.append(float(r['close'])); sp.append(int(r['spread_points']) * point)
    return dict(t=t, o=o, h=h, l=l, c=c, sp=sp)

def frozen_days(B, share=0.2):
    """days where >20% of candles repeat the previous candle exactly (broker data gaps filled with copies)."""
    d = collections.defaultdict(lambda: [0, 0])
    for i in range(1, len(B['t'])):
        k = from_min(B['t'][i]).date()
        same = B['o'][i] == B['o'][i-1] and B['h'][i] == B['h'][i-1] and B['l'][i] == B['l'][i-1] and B['c'][i] == B['c'][i-1]
        d[k][0] += same; d[k][1] += 1
    return {k for k, (s, n) in d.items() if n > 100 and s / n > share}

# ---------------------------------------------------------------- structure (owner's close-based structure)
def structure(B):
    n = len(B['t']); H, L, C = B['h'], B['l'], B['c']
    D, LO, HI, FL = [0] * n, [0.0] * n, [0.0] * n, [0] * n
    d, lo, hi = 1, L[0], H[0]; ext, pulled, opp = H[0], False, L[0]
    for i in range(1, n):
        h, l, c = H[i], L[i], C[i]
        if d == 1:
            if c < lo: hi = max(ext, h); d = -1; FL[i] = -1; ext, pulled, opp = l, False, h
            elif pulled and c > ext: lo, hi = min(opp, l), ext; ext, pulled, opp = h, False, l
            elif h > ext: ext, pulled, opp = h, False, l
            else: pulled = pulled or h < ext; opp = min(opp, l)
        else:
            if c > hi: lo = min(ext, l); d = 1; FL[i] = 1; ext, pulled, opp = h, False, l
            elif pulled and c < ext: lo, hi = ext, max(opp, h); ext, pulled, opp = l, False, h
            elif l < ext: ext, pulled, opp = l, False, h
            else: pulled = pulled or l > ext; opp = max(opp, h)
        D[i], LO[i], HI[i] = d, lo, hi
    return dict(d=D, lo=LO, hi=HI, flip=FL)

# ---------------------------------------------------------------- key levels
def session_key(m): return (from_min(m) + dt.timedelta(hours=6)).date()

def build_levels(B):
    day = collections.OrderedDict()
    for i, m in enumerate(B['t']):
        k = session_key(m)
        if k not in day: day[k] = [B['h'][i], B['l'][i]]
        else: day[k] = [max(day[k][0], B['h'][i]), min(day[k][1], B['l'][i])]
    week, month = collections.OrderedDict(), collections.OrderedDict()
    for k, (h, l) in day.items():
        for d, key in ((week, k.isocalendar()[:2]), (month, (k.year, k.month))):
            d[key] = [max(d[key][0], h), min(d[key][1], l)] if key in d else [h, l]
    wk, mk = list(week), list(month); out, prev = {}, None
    for k in day:
        lv = {}; wi = wk.index(k.isocalendar()[:2]); mi = mk.index((k.year, k.month))
        if prev is not None: lv['PDH'], lv['PDL'] = day[prev]
        if wi > 0: lv['PWH'], lv['PWL'] = week[wk[wi - 1]]
        if mi > 0: lv['PMH'], lv['PML'] = month[mk[mi - 1]]
        out[k] = lv; prev = k
    return out

def touched(B, lv, sd, i0, i1, which=('D', 'W', 'M')):
    hit = []
    for x in which:
        key = f'P{x}H' if sd == -1 else f'P{x}L'
        if key in lv and any(B['l'][i] <= lv[key] <= B['h'][i] for i in range(i0, i1 + 1)): hit.append(key)
    return hit

# ---------------------------------------------------------------- CRT
def by_day(B, start=T(4, 0)):
    d = collections.OrderedDict()
    for i, m in enumerate(B['t']):
        e = from_min(m)
        if start <= e.time() < T(16, 0): d.setdefault(e.date(), []).append(i)
    return d

def day_setups(B, idx, rh=8, p0=9, p1=11):
    H, L, C, Tm = B['h'], B['l'], B['c'], B['t']
    r = [i for i in idx if T(rh, 0) <= from_min(Tm[i]).time() < T(rh + 1, 0)]
    if len(r) < 48: return []
    rhi, rlo = max(H[i] for i in r), min(L[i] for i in r)
    q = collections.OrderedDict()
    for i in idx:
        e = from_min(Tm[i])
        if T(p0, 0) <= e.time() < T(p1, 0): q.setdefault(e.replace(minute=e.minute - e.minute % 15), []).append(i)
    out = []
    for k, ii in q.items():
        if len(ii) < 15: continue
        h, l, c = max(H[i] for i in ii), min(L[i] for i in ii), C[ii[-1]]
        inside = rlo < c < rhi
        for sd, ok in ((-1, h > rhi and inside), (1, l < rlo and inside)):
            if ok: out.append(dict(side=sd, rhi=rhi, rlo=rlo, A_hi=h, A_lo=l, A_end=ii[-1], A_t=k))
    return out

def run(B, comm, conf, target, stop_mode='sweep', ob_body=0.3, levels=None, which=('D', 'W', 'M'), skip=None, rh=8, p0=9, p1=11):
    H, L, O, C, SP, Tm = B['h'], B['l'], B['o'], B['c'], B['sp'], B['t']
    trades = []
    for day, idx in by_day(B, T(max(0, rh - 4), 0)).items():
        if skip and day in skip: continue
        setups = day_setups(B, idx, rh, p0, p1)
        if not setups: continue
        a0, a1 = idx[0], idx[-1] + 1
        sub = {k: B[k][a0:a1] for k in ('t', 'o', 'h', 'l', 'c')}
        S1 = structure(sub)
        win = [i for i in idx if from_min(Tm[i]).time() < T(p1, 0)]
        eod = [i for i in idx if from_min(Tm[i]).time() <= T(15, 55)]
        if not win or not eod: continue
        stop_i, last_i = win[-1], eod[-1]
        best = None
        for s in setups:
            sd = s['side']
            j = next((i for i in range(s['A_end'] + 1, stop_i + 1)
                      if (sd == -1 and H[i] > s['A_hi']) or (sd == 1 and L[i] < s['A_lo'])), None)
            if j is None: continue
            sig, ext_i = None, j
            for f in range(j, stop_i + 1):
                if (sd == -1 and H[f] > H[ext_i]) or (sd == 1 and L[f] < L[ext_i]): ext_i = f
                if conf == 'choch':
                    if S1['flip'][f - a0] == sd:
                        edge = S1['hi'][f - a0] if sd == -1 else S1['lo'][f - a0]
                        sig = (f + 1, None, edge + SP[f] if sd == -1 else edge - SP[f], ext_i); break
                elif conf == 'ifvg':
                    gap = None
                    for i in range(s['A_end'] + 2, ext_i + 1):
                        if sd == -1 and L[i] > H[i - 2]: gap = (H[i - 2], L[i])
                        if sd == 1 and H[i] < L[i - 2]: gap = (L[i - 2], H[i])
                    if gap and f > ext_i and ((sd == -1 and C[f] < gap[0]) or (sd == 1 and C[f] > gap[0])):
                        sig = (f + 1, None, gap[1] + SP[f] if sd == -1 else gap[1] - SP[f], ext_i); break
                elif conf == 'ob':
                    if f <= ext_i: continue
                    obi = next((i for i in range(ext_i, s['A_end'], -1)
                                if ((sd == -1 and C[i] > O[i]) or (sd == 1 and C[i] < O[i]))
                                and (ob_body is None or abs(C[i] - O[i]) >= ob_body * (H[i] - L[i]))), None)
                    if obi is None: break
                    if (sd == -1 and C[f] < L[obi]) or (sd == 1 and C[f] > H[obi]):
                        sig = (f + 1, O[obi], H[obi] + SP[f] if sd == -1 else L[obi] - SP[f], ext_i); break
            if not sig or sig[0] > stop_i: continue
            if levels is not None:
                lv = levels.get(session_key(Tm[sig[0]]), {})
                hit = touched(B, lv, sd, j, sig[0] - 1, which)          # the SECOND SWEEP trades into a key level
                if not hit: continue
            else:
                hit = []
            if best is None or sig[0] < best[1][0]: best = (s, sig, j, hit)
        if not best: continue
        s, (i0, lim, stop, ext_i), j, hit = best
        sd = s['side']
        if stop_mode == 'sweep': stop = H[ext_i] + SP[ext_i] if sd == -1 else L[ext_i] - SP[ext_i]
        fixed = {'opp': s['rlo'] if sd == -1 else s['rhi'], 'half': (s['rhi'] + s['rlo']) / 2}.get(target)
        fill = None
        if lim is None: fill = (i0, O[i0] if sd == -1 else O[i0] + SP[i0])
        else:
            for k in range(i0, stop_i + 1):
                if sd == -1 and H[k] >= lim: fill = (k, max(lim, O[k])); break
                if sd == 1 and L[k] + SP[k] <= lim: fill = (k, min(lim, O[k] + SP[k])); break
        if not fill: continue
        k0, entry = fill
        risk = sd * (entry - stop)
        if risk <= 0: continue
        tgt = fixed if fixed is not None else entry + sd * float(target[0]) * risk
        if sd * (tgt - entry) <= 0: continue
        res = None
        for k in range(k0, last_i + 1):
            sp = SP[k]
            if (sd == 1 and L[k] <= stop) or (sd == -1 and H[k] + sp >= stop): res = (k, stop, 'stop'); break
            if k > k0 and ((sd == 1 and H[k] >= tgt) or (sd == -1 and L[k] + sp <= tgt)): res = (k, tgt, 'target'); break
        if not res: res = (last_i, C[last_i] if sd == 1 else C[last_i] + SP[last_i], '15:55 close')
        k1, px, why = res
        trades.append(dict(et=str(from_min(Tm[k0])), side=sd, entry=entry, stop=stop, target=tgt, risk=risk, exit=why,
                           exit_et=str(from_min(Tm[k1])), R=(sd * (px - entry) - comm) / risk, A=str(s['A_t']),
                           rhi=s['rhi'], rlo=s['rlo'], A_hi=s['A_hi'], A_lo=s['A_lo'], sweep_t=str(from_min(Tm[j])),
                           ext=H[ext_i] if sd == -1 else L[ext_i], levels=hit))
    return trades

def stats(Tr):
    if not Tr: return None
    R = [t['R'] for t in Tr]; w = sum(1 for x in R if x > 0)
    gw = sum(x for x in R if x > 0); gl = -sum(x for x in R if x < 0)
    eq = pk = dd = 0.0; s = best = 0
    for x in R:
        eq += x; pk = max(pk, eq); dd = max(dd, pk - eq); s = s + 1 if x < 0 else 0; best = max(best, s)
    return dict(n=len(R), win=w / len(R), avg=statistics.mean(R), pf=gw / gl if gl else 99, dd=dd, streak=best)
