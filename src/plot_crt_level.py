import sys, os, pickle, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crt_core as K
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B = K.load('data/USTEC_PERIOD_M1.csv', 0.01); LV = K.build_levels(B)
keep = pickle.load(open('out/crt_levels_trades.pkl', 'rb'))
idx = {K.from_min(m): i for i, m in enumerate(B['t'])}
H, L, O, C = B['h'], B['l'], B['o'], B['c']
def ist(t):
    s = dt.datetime.combine(K._nth_sunday(t.year, 3, 2), dt.time(2)); e = dt.datetime.combine(K._nth_sunday(t.year, 11, 1), dt.time(2))
    return t + dt.timedelta(hours=9, minutes=30) if s <= t < e else t + dt.timedelta(hours=10, minutes=30)
NAME = {'PDH': 'Prev DAY high', 'PDL': 'Prev DAY low', 'PWH': 'Prev WEEK high', 'PWL': 'Prev WEEK low', 'PMH': 'Prev MONTH high', 'PML': 'Prev MONTH low'}
COL = {'D': '#c92a2a', 'W': '#5f3dc4', 'M': '#087f5b'}
BOX = dict(boxstyle='round,pad=0.35', fc='white', ec='#444', lw=0.8)
def draw(t, fname):
    sd = t['side']; short = sd == -1
    kf = idx[dt.datetime.fromisoformat(t['et'])]; kx = idx[dt.datetime.fromisoformat(t['exit_et'])]
    iA = idx[dt.datetime.fromisoformat(t['A'])]; j = idx[dt.datetime.fromisoformat(t['sweep_t'])]
    i8 = idx[K.from_min(B['t'][kf]).replace(hour=8, minute=0)]
    i0, i1 = i8, min(kx + 10, kf + 160)
    lv = LV[K.session_key(B['t'][kf])]
    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=120)
    for k in range(i0, i1 + 1):
        col = '#1a9e77' if C[k] >= O[k] else '#e5484d'
        ax.plot([k, k], [L[k], H[k]], color=col, lw=0.6, zorder=2)
        ax.add_patch(Rectangle((k - 0.32, min(O[k], C[k])), 0.64, max(abs(C[k] - O[k]), 0.25), color=col, zorder=3))
    lo_ = min(min(L[i0:i1 + 1]), t['stop'], t['target']); hi_ = max(max(H[i0:i1 + 1]), t['stop'], t['target'])
    span = hi_ - lo_
    for k_, v in lv.items():
        if lo_ - 0.15 * span <= v <= hi_ + 0.15 * span:
            ax.hlines(v, i0, i1, colors=COL[k_[1]], lw=2.2, zorder=1)
            ax.text(i0 + 1, v, f" {NAME[k_]} {v:.1f}" + ('  ← swept' if k_ in t['levels'] else ''), color=COL[k_[1]], fontsize=10, fontweight='bold', va='bottom')
    ax.set_ylim(lo_ - 0.18 * span, hi_ + 0.22 * span)
    ax.add_patch(Rectangle((i8 - 0.5, t['rlo']), 60, t['rhi'] - t['rlo'], alpha=0.10, color='#3b5bdb'))
    ax.text(i8, t['rhi'], f" ① 8am NY candle ({ist(K.from_min(B['t'][i8])):%H:%M} IST)", color='#3b5bdb', fontsize=9, va='bottom')
    ax.hlines([t['rhi'], t['rlo']], i8, i1, colors='#3b5bdb', lw=0.8, linestyles=':')
    ax.add_patch(Rectangle((iA - 0.5, t['A_lo']), 15, t['A_hi'] - t['A_lo'], alpha=0.16, color='#f08c00'))
    ax.hlines(t['A_hi'] if short else t['A_lo'], iA, i1, colors='#f08c00', lw=1, linestyles=':')
    def note(x, y, txt, dx, dy):
        ax.annotate(txt, xy=(x, y), xytext=(x + dx, y + dy * span), fontsize=9.5, bbox=BOX, arrowprops=dict(arrowstyle='->', color='#333'), zorder=10)
    up = 1 if short else -1
    note(iA + 7, t['A_hi'] if short else t['A_lo'], f"② Candle A ({ist(K.from_min(B['t'][iA])):%H:%M} IST) takes the 8am\n{'high' if short else 'low'} and closes back inside", -40, 0.10 * up)
    ke = max(range(j, kf), key=lambda k: H[k] if short else -L[k])
    note(ke, H[ke] if short else L[ke], f"③ Second sweep takes candle A's {'high' if short else 'low'}\nAND trades into the {', '.join(NAME[x] for x in t['levels'])}", 5, 0.08 * up)
    for y, n, c in ((t['stop'], '⑥ STOP beyond sweep', '#e03131'), (t['entry'], f"④⑤ ENTRY iFVG ({ist(K.from_min(B['t'][kf])):%H:%M})", '#1c3faa'), (t['target'], f"TARGET {t['rr'] if 'rr' in t else '3'}R", '#f59f00')):
        ax.hlines(y, kf, i1, colors=c, lw=1.6, zorder=5); ax.text(i1 + 0.6, y, f"{n}  {y:.1f}", fontsize=9.5, va='center', color=c, fontweight='bold')
    ax.scatter([kf], [t['entry']], marker='v' if short else '^', s=140, color='#1c3faa', zorder=11)
    if kx <= i1: ax.scatter([kx], [t['target'] if t['exit'] == 'target' else t['stop']], marker='X', s=140, color='k', zorder=11)
    ticks = list(range(i0, i1 + 1, 15)); ax.set_xticks(ticks); ax.set_xticklabels([ist(K.from_min(B['t'][k])).strftime('%H:%M') for k in ticks], fontsize=8.5)
    ax.set_xlim(i0 - 1, i1 + 42)
    d = K.from_min(B['t'][kf])
    ax.set_title(f"NASDAQ 1m, {d:%d %b %Y} — CRT {'SHORT' if short else 'LONG'} formed at a key level: {t['exit']} {t['R']:+.1f}R  (times IST)", fontsize=12, pad=10)
    ax.grid(alpha=0.15); fig.tight_layout(); fig.savefig('out/charts/' + fname); plt.close(fig)
    print(fname, t['et'], t['levels'], t['exit'], round(t['R'], 2))
Tr = keep[('ifvg', '3R')]
for t in Tr: t['rr'] = 3
wk = [t for t in Tr if any(x[1] in 'WM' for x in t['levels'])]
wins = [t for t in wk if t['exit'] == 'target']; losses = [t for t in Tr if t['exit'] == 'stop']
draw(wins[-1], 'crtlvl_win.png'); draw(losses[-1], 'crtlvl_loss.png')
