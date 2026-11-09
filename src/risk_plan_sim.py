import pickle, numpy as np, pandas as pd
d=pickle.load(open('out/crt_levels_trades.pkl','rb'))
R0=np.array([t['R'] for t in d[('ifvg','3R')]]); 
rng=np.random.default_rng(7)
def phase(seq,tgt,ml,trig,base=0.5):
    eq=0.0
    for i,r in enumerate(seq):
        risk = eq if eq>=trig-1e-9 else base
        eq+=risk*r
        if eq<=-ml: return 'fail',i+1
        if eq>=tgt-1e-9: return 'pass',i+1
    return 'open',len(seq)
def flat(seq,tgt,ml,risk=0.5): return phase(seq,tgt,ml,1e9,risk)
acc={'10k Standard':[(8,10,2.0),(5,10,1.5)],'5k Pro':[(6,6,1.5),(6,6,1.5)]}
print(f'{"edge per trade":>14} | {"account":12} | {"plan":14} | pass both | median trades | ~months @1/day')
for edge in [0.13,0.08,0.0]:
    R=R0-R0.mean()+edge
    for name,ph in acc.items():
        for plan in ['your plan','flat 0.5%']:
            out=[];n=[]
            for s in range(4000):
                seq=rng.choice(R,3000); used=0; ok=True
                for tgt,ml,trig in ph:
                    o,k = phase(seq[used:],tgt,ml,trig) if plan=='your plan' else flat(seq[used:],tgt,ml)
                    used+=k
                    if o!='pass': ok=False;break
                out.append(ok); 
                if ok: n.append(used)
            med=np.median(n) if n else np.nan
            print(f'{edge:+14.2f} | {name:12} | {plan:14} | {np.mean(out):8.0%} | {med:13.0f} | {med/21:6.1f}')
print('\nPassed both phases within 3 / 6 months (1 trade/day/account), edge +0.13 and +0.08')
for edge in [0.13,0.08]:
    R=R0-R0.mean()+edge
    for name,ph in acc.items():
        for plan in ['your plan','flat 0.5%']:
            n=[]
            for s in range(4000):
                seq=rng.choice(R,3000); used=0; ok=True
                for tgt,ml,trig in ph:
                    o,k = phase(seq[used:],tgt,ml,trig) if plan=='your plan' else flat(seq[used:],tgt,ml)
                    used+=k
                    if o!='pass': ok=False;break
                n.append(used if ok else 1e9)
            n=np.array(n); print(f'{edge:+.2f} {name:12} {plan:10}: 3 mo {np.mean(n<=63):4.0%}  6 mo {np.mean(n<=126):4.0%}')
