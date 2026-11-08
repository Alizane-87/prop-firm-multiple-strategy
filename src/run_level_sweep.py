import sys, os, collections, statistics as st, datetime as dt, pickle, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crt_core as K, level_sweep as LS
T = dt.time
B = K.load('data/USTEC_PERIOD_M1.csv', 0.01)
SKIP = K.frozen_days(B) | {dt.date(2024,10,4) + dt.timedelta(days=i) for i in range((dt.date(2025,1,31) - dt.date(2024,10,4)).days + 1)}
LV = K.build_levels(B)
F = dict(B); F['sp'] = [0.25] * len(B['t'])
MONTHS = 42
keep, rows = {}, []
def show(lab, Tr):
    s = K.stats(Tr)
    if not s: print(f"  {lab:50s} | 0 trades"); return
    y = collections.defaultdict(list); sd = collections.defaultdict(list); lv = collections.defaultdict(list)
    for t in Tr: y[t['et'][:4]].append(t['R']); sd['L' if t['side'] == 1 else 'S'].append(t['R']); lv[t['level'][1]].append(t['R'])
    ok = all(st.mean(v) > 0 for v in y.values())
    print(f"{'✔' if ok else ' '} {lab:50s} | n{s['n']:4d} ({s['n']/MONTHS:.1f}/mo) win {s['win']:.0%} avg {s['avg']:+.3f}R PF {s['pf']:.2f} DD {s['dd']:5.1f}R streak {s['streak']:2d} | "
          + ' '.join(f"{k}:{st.mean(v):+.2f}({len(v)})" for k, v in sorted(y.items())) + ' | ' + ' '.join(f"{k}:{st.mean(v):+.2f}" for k, v in sorted(sd.items()))
          + ' | ' + ' '.join(f"{k}:{st.mean(v):+.2f}({len(v)})" for k, v in sorted(lv.items())))
    rows.append(dict(lab=lab, stats=s, years={k: (len(v), st.mean(v)) for k, v in y.items()}))
for wl, w0, w1 in (('08:00-12:00 NY', T(8,0), T(12,0)), ('03:00-12:00 NY (London+NY)', T(3,0), T(12,0)), ('00:00-16:00 NY (all day)', T(0,0), T(16,0))):
    for which, wlab in ((('D','W','M'), 'day/week/month'), (('D',), 'prev DAY'), (('W','M'), 'prev WEEK/MONTH')):
        for tg in ('2R', '3R'):
            for cl, data, comm in (('CFD', B, 0.0), ('FUT', F, 0.25)):
                Tr = LS.run(data, LV, comm, tg, w0, w1, which, SKIP)
                show(f"{cl} {wl} {wlab} {tg}", Tr)
                if cl == 'FUT' and wlab == 'day/week/month' and w0 == T(8,0): keep[tg] = Tr
        print()
pickle.dump(keep, open('out/level_sweep_trades.pkl', 'wb')); json.dump(rows, open('out/level_sweep.json', 'w'), indent=1, default=str)
