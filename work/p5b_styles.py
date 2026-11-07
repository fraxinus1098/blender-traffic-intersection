import pdfplumber, json, collections
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
K=40/72
OFF={40:(14,-51.6,-142.1),41:(15,724.2,-53.9)}
FR={40:(-493.4,186.2,-191.2,248.6),41:(-62.1,617.5,-240.2,199.6)}
res={}
for s,(idx,dx,dy) in OFF.items():
    p=pdf.pages[idx]; L=[]
    for o in p.lines+p.curves+p.rects:
        pts=o.get('pts') or []
        if not pts: continue
        P=[((x+dx-836.9)*K,-(y+dy-305.5)*K) for x,y in pts]
        cx=sum(a for a,b in P)/len(P); cy=sum(b for a,b in P)/len(P)
        x0,x1,y0,y1=FR[s]
        if not (x0+3<cx<x1-3 and y0+3<cy<y1-3): continue
        if not (-420<cx<580 and -250<cy<220): continue
        L.append(dict(t=o['object_type'],fill=bool(o.get('fill')),fc=str(o.get('non_stroking_color'))[:14],sc=str(o.get('stroking_color'))[:14],
             lw=round(o.get('linewidth') or 0,2),dash=str(o.get('dash'))[:16],pts=[(round(a,3),round(b,3)) for a,b in P]))
    res[s]=L
    c=collections.Counter((o['t'],o['fill'],o['fc'],o['sc'],o['lw'],o['dash']) for o in L)
    print(s,len(L)); [print('  ',v,k) for k,v in c.most_common(30)]
json.dump(res,open('objs40.json','w'))
