import sys, os, pickle, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crt_core as K
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B = K.load('data/USTEC_PERIOD_M1.csv', 0.01)
Tr = pickle.load(open('out/level_sweep_trades.pkl', 'rb'))['2R']
idx = {K.from_min(m): i for i, m in enumerate(B['t'])}
H, L, O, C = B['h'], B['l'], B['o'], B['c']
def ist(t):
    s = dt.datetime.combine(K._nth_sunday(t.year, 3, 2), dt.time(2)); e = dt.datetime.combine(K._nth_sunday(t.year, 11, 1), dt.time(2))
    return t + dt.timedelta(hours=9, minutes=30) if s <= t < e else t + dt.timedelta(hours=10, minutes=30)
NAME = {'PDH': 'Prev DAY high', 'PDL': 'Prev DAY low', 'PWH': 'Prev WEEK high', 'PWL': 'Prev WEEK low', 'PMH': 'Prev MONTH high', 'PML': 'Prev MONTH low'}
BOX = dict(boxstyle='round,pad=0.35', fc='white', ec='#444', lw=0.8)
def draw(t, fname):
    sd = t['side']; short = sd == -1
    kf = idx[dt.datetime.fromisoformat(t['et'])]; kx = idx[dt.datetime.fromisoformat(t['exit_et'])]; kc = idx[dt.datetime.fromisoformat(t['cross_t'])]
    i0, i1 = kc - 40, min(kx + 10, kf + 120)
    fig, ax = plt.subplots(figsize=(14, 8), dpi=120)
    for k in range(i0, i1 + 1):
        col = '#1a9e77' if C[k] >= O[k] else '#e5484d'
        ax.plot([k, k], [L[k], H[k]], color=col, lw=0.7); ax.add_patch(Rectangle((k - 0.32, min(O[k], C[k])), 0.64, max(abs(C[k] - O[k]), 0.25), color=col))
    ax.hlines(t['lvl'], i0, i1, colors='#5f3dc4', lw=2.2); ax.text(i0 + 1, t['lvl'], f" {NAME[t['level']]} {t['lvl']:.1f}", color='#5f3dc4', fontsize=10, fontweight='bold', va='bottom')
    lo_ = min(min(L[i0:i1 + 1]), t['stop'], t['target']); hi_ = max(max(H[i0:i1 + 1]), t['stop'], t['target']); span = hi_ - lo_
    ax.set_ylim(lo_ - 0.15 * span, hi_ + 0.2 * span)
    ax.annotate(f"① Price sweeps the {NAME[t['level']]} ({ist(K.from_min(B['t'][kc])):%H:%M} IST)", xy=(kc, H[kc] if short else L[kc]),
                xytext=(kc - 35, (H[kc] if short else L[kc]) + (0.12 if short else -0.12) * span), fontsize=9.5, bbox=BOX, arrowprops=dict(arrowstyle='->'))
    for y, n, c in ((t['stop'], '③ STOP beyond sweep', '#e03131'), (t['entry'], f"② ENTRY iFVG ({ist(K.from_min(B['t'][kf])):%H:%M})", '#1c3faa'), (t['target'], 'TARGET 2R', '#f59f00')):
        ax.hlines(y, kf, i1, colors=c, lw=1.6); ax.text(i1 + 0.6, y, f"{n}  {y:.1f}", fontsize=9.5, va='center', color=c, fontweight='bold')
    ax.scatter([kf], [t['entry']], marker='v' if short else '^', s=140, color='#1c3faa', zorder=11)
    if kx <= i1: ax.scatter([kx], [t['target'] if t['exit'] == 'target' else t['stop']], marker='X', s=140, color='k', zorder=11)
    ticks = list(range(i0, i1 + 1, 10)); ax.set_xticks(ticks); ax.set_xticklabels([ist(K.from_min(B['t'][k])).strftime('%H:%M') for k in ticks], fontsize=8.5)
    ax.set_xlim(i0 - 1, i1 + 35)
    d = K.from_min(B['t'][kf])
    ax.set_title(f"NASDAQ 1m, {d:%d %b %Y} — key-level sweep + iFVG {'SHORT' if short else 'LONG'} (no CRT): {t['exit']} {t['R']:+.1f}R  (IST)", fontsize=12, pad=10)
    ax.grid(alpha=0.15); fig.tight_layout(); fig.savefig('out/charts/' + fname); plt.close(fig)
    print(fname, t['et'], t['level'], t['exit'], round(t['R'], 2))
draw([t for t in Tr if t['exit'] == 'target'][-1], 'ls_win.png'); draw([t for t in Tr if t['exit'] == 'stop'][-1], 'ls_loss.png')
