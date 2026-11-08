import sys, os, collections, statistics as st, datetime as dt, json, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crt_core as K
B = K.load('data/USTEC_PERIOD_M1.csv', 0.01)
SKIP = K.frozen_days(B) | {dt.date(2024,10,4) + dt.timedelta(days=i) for i in range((dt.date(2025,1,31) - dt.date(2024,10,4)).days + 1)}
LV = K.build_levels(B); F = dict(B); F['sp'] = [0.25] * len(B['t'])
rows, keep = [], {}
def show(lab, Tr):
    s = K.stats(Tr)
    if not s: print(f"  {lab:58s} | 0 trades"); return
    y = collections.defaultdict(list); sd = collections.defaultdict(list)
    for t in Tr: y[t['et'][:4]].append(t['R']); sd['L' if t['side'] == 1 else 'S'].append(t['R'])
    ok = all(st.mean(v) > 0 for v in y.values())
    print(f"{'✔' if ok else ' '} {lab:58s} | n{s['n']:4d} ({s['n']/42:.1f}/mo) win {s['win']:.0%} avg {s['avg']:+.3f}R PF {s['pf']:.2f} DD {s['dd']:5.1f}R streak {s['streak']:2d} | "
          + ' '.join(f"{k}:{st.mean(v):+.2f}({len(v)})" for k, v in sorted(y.items())) + ' | ' + ' '.join(f"{k}:{st.mean(v):+.2f}" for k, v in sorted(sd.items())))
    rows.append(dict(lab=lab, stats=s, years={k: (len(v), st.mean(v)) for k, v in y.items()}))
for name, rh, p0, p1 in (('3am purge (2am range, 03-05)', 2, 3, 5), ('6am purge (5am range, 06-08)', 5, 6, 8), ('9am purge (8am range, 09-11)', 8, 9, 11)):
    print(f"\n===== {name} — iFVG, stop beyond second-sweep extreme =====")
    for tg in ('2R', '3R'):
        for lab, lv, which in (('pure CRT', None, ('D','W','M')), ('2nd sweep into any key level', LV, ('D','W','M')), ('2nd sweep into prev WEEK/MONTH', LV, ('W','M'))):
            for cl, data, comm in (('CFD', B, 0.0), ('FUT', F, 0.25)):
                Tr = K.run(data, comm, 'ifvg', tg, 'sweep', 0.3, lv, which, SKIP, rh, p0, p1)
                show(f"{cl} {tg} {lab}", Tr)
                if cl == 'FUT' and lv is not None and which == ('D','W','M'): keep[(rh, tg)] = Tr
json.dump(rows, open('out/crt_times.json', 'w'), indent=1, default=str); pickle.dump(keep, open('out/crt_times_trades.pkl', 'wb'))
