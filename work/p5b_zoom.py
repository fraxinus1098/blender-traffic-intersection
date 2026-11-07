import json, sys, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
R=json.load(open('objs40.json'))
A=(-44.8,93.3); B=(64.6,-94.0)
def side(X,Y): return (B[0]-A[0])*(Y-A[1])-(B[1]-A[1])*(X-A[0])
def keep(s,P):
    cx=sum(a for a,b in P)/len(P); cy=sum(b for a,b in P)/len(P); sd=side(cx,cy)
    return not ((s=='40' and sd>0) or (s=='41' and sd<0))
x0,x1,y0,y1=map(float,sys.argv[1:5]); out=sys.argv[5]
fig,ax=plt.subplots(figsize=(18,18*(y1-y0)/(x1-x0)))
for s in ('40','41'):
    for o in R[s]:
        P=o['pts']
        if not keep(s,P): continue
        xs=[a for a,b in P]; ys=[b for a,b in P]
        if max(xs)<x0 or min(xs)>x1 or max(ys)<y0 or min(ys)>y1: continue
        if o['fill'] and o['fc'].startswith('(0.0'): ax.add_patch(MP(P,closed=True,fc='k',ec='none'))
        elif o['fill']: ax.add_patch(MP(P,closed=True,fc='orange',ec='none'))
        elif o['sc'].startswith('(0.0') and o['lw']==0.24: ax.plot(xs,ys,'-',color='blue',lw=0.8)
        elif o['sc'].startswith('(0.0') and o['lw']==0.72: ax.plot(xs,ys,'-',color='red',lw=0.8)
        elif o['sc'].startswith('(0.0'): ax.plot(xs,ys,'-',color='m',lw=0.8)
        else: ax.plot(xs,ys,'-',color='0.7',lw=0.6)
ax.set_aspect('equal'); ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig(out,dpi=60)
