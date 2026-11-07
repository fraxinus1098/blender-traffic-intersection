import pdfplumber, math, sys
from collections import Counter
idx={24:1,25:2,26:3,27:4,38:12,39:13,40:14,41:15}
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
def segs(s,minlen=25):
    p=pdf.pages[idx[s]]; out=[]
    for o in p.lines+p.curves:
        pts=o['pts']
        for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
            L=math.hypot(x1-x0,y1-y0)
            if L<minlen: continue
            if max(x0,x1)>1075 or (min(y0,y1)>560 and max(x0,x1)<420): continue  # legend/title/callouts
            if (x1,y1)<(x0,y0): x0,y0,x1,y1=x1,y1,x0,y0
            out.append((round(L,1),round(math.degrees(math.atan2(y1-y0,x1-x0))%180,1),x0,y0))
    return out
cache={}
for pair in sys.argv[1:]:
    a,b=map(int,pair.split(','))
    A=cache.setdefault(a,segs(a)); B=cache.setdefault(b,segs(b))
    from collections import defaultdict
    bk=defaultdict(list)
    for L,an,x,y in B: bk[(L,an)].append((x,y))
    votes=Counter()
    for L,an,x,y in A:
        for xb,yb in bk.get((L,an),[]):
            d=(round(x-xb,1),round(y-yb,1))
            if d!=(0.0,0.0): votes[d]+=1
    print(f'{b} -> {a} (add to {b} coords, pt):', votes.most_common(4))
