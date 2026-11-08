import sys, os, json, collections, statistics as st, datetime as dt, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crt_core as K
B = K.load('data/USTEC_PERIOD_M1.csv', 0.01)
bad = K.frozen_days(B)
SKIP = bad | {dt.date(2024,10,4) + dt.timedelta(days=i) for i in range((dt.date(2025,1,31) - dt.date(2024,10,4)).days + 1)}
LV = K.build_levels(B)
F = dict(B); F['sp'] = [0.25] * len(B['t'])
print(f"bars {len(B['t']):,}; frozen days found {len(bad)} ({min(bad)} -> {max(bad)}); skipping {len(SKIP)} calendar days")
rows = []
def show(lab, Tr):
    s = K.stats(Tr)
    if not s: print(f"  {lab:46s} | 0 trades"); return
    y = collections.defaultdict(list); sd = collections.defaultdict(list)
    for t in Tr: y[t['et'][:4]].append(t['R']); sd['L' if t['side'] == 1 else 'S'].append(t['R'])
    ok = all(st.mean(v) > 0 for v in y.values())
    print(f"{'✔' if ok else ' '} {lab:46s} | n{s['n']:4d} win {s['win']:.0%} avg {s['avg']:+.3f}R PF {s['pf']:.2f} DD {s['dd']:5.1f}R streak {s['streak']:2d} | "
          + ' '.join(f"{k}:{st.mean(v):+.2f}({len(v)})" for k, v in sorted(y.items())) + ' | ' + ' '.join(f"{k}:{st.mean(v):+.2f}({len(v)})" for k, v in sorted(sd.items())))
    rows.append(dict(lab=lab, stats=s, years={k: (len(v), st.mean(v)) for k, v in y.items()}))
    return Tr
keep = {}
for conf in ('ifvg', 'choch', 'ob'):
    for tg in ('2R', '3R', 'opp'):
        print(f"\n== CRT {conf} {tg} (stop beyond second-sweep extreme) ==")
        for lab, lv, which in (('pure CRT (no level)', None, None), ('2nd sweep into any key level D/W/M', LV, ('D','W','M')),
                               ('2nd sweep into prev DAY level', LV, ('D',)), ('2nd sweep into prev WEEK/MONTH', LV, ('W','M'))):
            for cl, data, comm in (('CFD', B, 0.0), ('FUT', F, 0.25)):
                Tr = K.run(data, comm, conf, tg, 'sweep', 0.3, lv, which or ('D','W','M'), SKIP)
                r = show(f"{cl} {lab}", Tr)
                if cl == 'FUT' and lv is not None and which == ('D','W','M'): keep[(conf, tg)] = Tr
json.dump(rows, open('out/crt_levels_location.json', 'w'), indent=1, default=str)
pickle.dump(keep, open('out/crt_levels_trades.pkl', 'wb'))
