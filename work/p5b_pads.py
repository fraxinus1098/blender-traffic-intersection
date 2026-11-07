import json, math
R=json.load(open('objs40.json'))
pts=[]
for s in R:
  for o in R[s]:
    P=o['pts']; xs=[a for a,b in P]; ys=[b for a,b in P]
    if o['fill'] and o['fc'].startswith('(0.0') and len(P)==5 and max(xs)-min(xs)<0.5 and max(ys)-min(ys)<0.5:
        pts.append((s,sum(xs)/5,sum(ys)/5))
cl=[]
for s,x,y in pts:
    for c in cl:
        if c['s']==s and math.hypot(c['x']-x,c['y']-y)<4: c['p'].append((x,y)); c['x']=sum(a for a,b in c['p'])/len(c['p']); c['y']=sum(b for a,b in c['p'])/len(c['p']); break
    else: cl.append(dict(s=s,x=x,y=y,p=[(x,y)]))
pads=[c for c in cl if len(c['p'])>=20 and -320<c['x']<340]
import numpy as np
for i,c in enumerate(pads):
    P=np.array(c['p']); m=P.mean(0); U,S,Vt=np.linalg.svd(P-m); ax=Vt[0]
    proj=(P-m)@Vt.T
    c['len']=float(proj[:,0].max()-proj[:,0].min())+0.5; c['dep']=float(proj[:,1].max()-proj[:,1].min())+0.5
    c['axis']=math.degrees(math.atan2(ax[1],ax[0])); c['id']=i; c['x']=float(m[0]); c['y']=float(m[1]); del c['p']
    print(i,c['s'],'(%.1f,%.1f)'%(c['x'],c['y']),'len %.1f dep %.1f axis %.0f'%(c['len'],c['dep'],c['axis']))
json.dump(pads,open('pads.json','w'))
