import pdfplumber, json, collections
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
K=40/72
OFF={26:(3,-9.8,-25.8),27:(4,453.9,-33.2)}
BOX={26:(-280,-40,-120,80),27:(-10,330,-80,130)}
res={}
for s,(idx,dx,dy) in OFF.items():
    p=pdf.pages[idx]; L=[]
    for o in p.curves+p.lines+p.rects:
        pts=o.get('pts') or []
        if not pts: continue
        P=[((x+dx-836.9)*K,-(y+dy-305.5)*K) for x,y in pts]
        xs=[a for a,b in P]; ys=[b for a,b in P]
        cx=sum(xs)/len(xs); cy=sum(ys)/len(ys)
        a,b,c,d=BOX[s]
        if not (a<cx<b and c<cy<d): continue
        sc=str(o.get('stroking_color')); fc=str(o.get('non_stroking_color'))
        L.append(dict(t=o['object_type'],fill=bool(o.get('fill')),fc=fc[:14],sc=sc[:14],lw=round(o.get('linewidth') or 0,2),
              dash=str(o.get('dash'))[:20],cx=round(cx,2),cy=round(cy,2),w=round(max(xs)-min(xs),2),h=round(max(ys)-min(ys),2),n=len(P),
              pts=[(round(a,2),round(b,2)) for a,b in P]))
    res[s]=L
    c=collections.Counter((o['t'],o['fill'],o['fc'],o['sc'],o['lw']) for o in L); print(s,len(L)); [print('  ',k,v) for k,v in c.most_common(25)]
json.dump(res,open('objs.json','w'))
