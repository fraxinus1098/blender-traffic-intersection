import pdfplumber, math, sys
idx={24:1,25:2,26:3,27:4,38:12,39:13,40:14,41:15}
s=int(sys.argv[1]); minlen=float(sys.argv[2])
with pdfplumber.open('plans/SH249_Select_Sheets.pdf') as pdf:
    p=pdf.pages[idx[s]]
    segs=[]
    for o in p.lines+p.curves:
        pts=o['pts']
        for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
            L=math.hypot(x1-x0,y1-y0)
            if L>=minlen and x0<1080 and x1<1080: segs.append((L,x0,y0,x1,y1,o.get('stroking_color'),o.get('linewidth'),o.get('dash')))
    segs.sort(reverse=True)
    for L,x0,y0,x1,y1,c,w,d in segs[:60]:
        ang=math.degrees(math.atan2(y1-y0,x1-x0))%180
        print(f'L={L:6.1f} ang={ang:6.1f} ({x0:7.1f},{y0:6.1f})-({x1:7.1f},{y1:6.1f}) w={w} c={c} dash={d}')
