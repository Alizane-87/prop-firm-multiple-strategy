import pickle, numpy as np, pandas as pd
d=pickle.load(open('out/crt_levels_trades.pkl','rb'))
rng=np.random.default_rng(1)
acc={'10k 2-Step Std':dict(t=[8,5],ml=10,dl=5),'5k 2-Step Pro':dict(t=[6,6],ml=6,dl=3)}
def phase(R,risk,tgt,ml,dl):
    eq=0.0
    for i,r in enumerate(R):
        pnl=risk*r
        if -pnl>=dl: return 'fail',i+1
        eq+=pnl
        if eq<=-ml: return 'fail',i+1
        if eq>=tgt: return 'pass',i+1
    return 'open',len(R)
for key in [('ifvg','2R'),('ifvg','3R')]:
    tr=d[key]; R=np.array([t['R'] for t in tr]); R=R-R.mean()+{'2R':0.167,'3R':0.130}[key[1]]
    et=pd.to_datetime([t['et'] for t in tr]); months=(et[-1]-et[0]).days/30.44-4  # minus skipped period
    tpm=len(R)/months
    print(f'\n== CRT key-level iFVG {key[1]}  {len(R)} trades, avg {R.mean():+.3f}R (CFD costs, shifted from futures R), {tpm:.1f} trades/month')
    for name,a in acc.items():
        for risk in [0.5,1.0,1.5,2.0]:
            res=[];tim=[]
            for s in range(4000):
                seq=rng.choice(R,size=2000,replace=True)
                o1,n1=phase(seq,risk,a['t'][0],a['ml'],a['dl'])
                if o1!='pass': res.append('fail P1'); continue
                o2,n2=phase(seq[n1:],risk,a['t'][1],a['ml'],a['dl'])
                res.append('pass both' if o2=='pass' else 'fail P2'); 
                if o2=='pass': tim.append((n1+n2)/tpm)
            res=pd.Series(res).value_counts(normalize=True)
            print(f'  {name:15s} risk {risk:.1f}%: pass both {res.get("pass both",0):5.0%} | fail P1 {res.get("fail P1",0):5.0%} | fail P2 {res.get("fail P2",0):5.0%} | median months to pass {np.median(tim) if tim else float("nan"):5.1f}')
