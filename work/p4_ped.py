import pdfplumber, json, math
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
K=40/72
OFF={'24':(1,0,0),'25':(2,594.7,0)}
poles={'A':('24',-161.63,43.59),'B':('24',-242.6,42.7),'D':('24',-175.5,-83.5),'C':('24',-210.95,-10.3),'E':('24',-99.5,-67.0),
'F':('25',194.47,-51.59),'G':('25',277.5,-49.5),'J':('25',208.8,91.6),'K':('25',145.1,65.6),'H':('25',252.45,7.15)}
objs={}
for s,(idx,dx,dy) in OFF.items():
    L=[]
    for o in pdf.pages[idx].curves:
        P=[((x+dx-836.9)*K,-(y+dy-305.5)*K) for x,y in o['pts']]
        L.append((o,P))
    objs[s]=L
out={}
for k,(s,x,y) in poles.items():
    res=[]; circ=None
    for o,P in objs[s]:
        cx=sum(p[0] for p in P)/len(P); cy=sum(p[1] for p in P)/len(P)
        d=math.hypot(cx-x,cy-y)
        if d>10: continue
        fc=str(o.get('non_stroking_color'))
        if o.get('fill') and fc.startswith('(0.0') and len(P)==4:
            U=P[:3]; ux=sum(p[0] for p in U)/3; uy=sum(p[1] for p in U)/3
            sides=[(math.hypot(U[(i+1)%3][0]-U[(i+2)%3][0],U[(i+1)%3][1]-U[(i+2)%3][1]),i) for i in range(3)]
            tip=U[max(sides)[1]]
            res.append(dict(c=(round(ux,2),round(uy,2)),dir=round(math.degrees(math.atan2(tip[1]-uy,tip[0]-ux))),d=round(d,1)))
        if k=='D' and not o.get('fill') and len(P)==5 and 1.8<max(p[0] for p in P)-min(p[0] for p in P)<2.8:
            circ=(round(cx,2),round(cy,2))
    out[k]=dict(heads=res,circ=circ); print(k,circ,res)
json.dump(out,open('ped.json','w'))
