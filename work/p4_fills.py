import pdfplumber, json, math
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
K=40/72
OFF={24:(1,0,0),25:(2,594.7,0)}
AREAS={24:[(-215,-130,-60,30),(-135,-40,-75,-15),(-270,-130,-130,75),(-200,-90,-140,80)],
       25:[(110,260,-30,85),(-20,320,-80,120)]}
res={}
for s,(idx,dx,dy) in OFF.items():
    p=pdf.pages[idx]; L=[]
    for o in p.curves+p.lines+p.rects:
        pts=o.get('pts') or []
        if not pts: continue
        P=[((x+dx-836.9)*K,-(y+dy-305.5)*K) for x,y in pts]
        xs=[a for a,b in P]; ys=[b for a,b in P]
        cx=sum(xs)/len(xs); cy=sum(ys)/len(ys)
        if not any(a<cx<b and c<cy<d for a,b,c,d in [(-300,320,-80,120)]): continue
        sc=str(o.get('stroking_color')); fc=str(o.get('non_stroking_color'))
        fill=bool(o.get('fill')); lw=round(o.get('linewidth') or 0,2)
        black_fill = fill and fc.startswith('(0.0, 0.0, 0.0)') or (fill and fc in ('0','(0,)','[0]'))
        L.append(dict(t=o['object_type'],fill=fill,fc=fc[:12],sc=sc[:12],lw=lw,cx=round(cx,2),cy=round(cy,2),
                      w=round(max(xs)-min(xs),2),h=round(max(ys)-min(ys),2),n=len(P),pts=[(round(a,2),round(b,2)) for a,b in P]))
    res[s]=L
json.dump(res,open('objs.json','w'))
import collections
for s in res:
    c=collections.Counter((o['t'],o['fill'],o['fc'],o['sc'],o['lw']) for o in res[s]); print(s,c.most_common(15))
