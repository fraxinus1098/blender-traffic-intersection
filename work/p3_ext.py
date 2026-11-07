import pdfplumber, math, json
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
K=40/72
OFF={38:(12,-51.6,-142.1),39:(13,724.8,-53.9)}
A=(-44.8,93.3); B=(64.6,-94.0)
def side(X,Y): return (B[0]-A[0])*(Y-A[1])-(B[1]-A[1])*(X-A[0])   # >0 = west side (left of A->B going south)
FR={38:(-493.4,186.2,-191.2,248.6),39:(-62.1,617.5,-240.2,199.6)}
def key(o):
    lw=round(o.get('linewidth') or 0,2); c=str(o.get('stroking_color')); d=o.get('dash')
    if o.get('fill') and lw==0: return 'fill'
    if lw==0.24 and c.startswith('(0.608') and not d: return 'gray'
    if lw==0.24 and c.startswith('(0.608') and d and d[0][0]==4.8: return 'graydash'
    if lw==1.2 and c.startswith('(0.725'): return 'row'
    if lw==0.72 and c=='(0.0, 0.0, 0.0)' and not d: return 'mark'
    if lw==0.72 and c=='(0.0, 0.0, 0.0)' and d: return 'markdash'
    return None
out={k:[] for k in ['fill','gray','graydash','row','mark','markdash']}
for s,(idx,dx,dy) in OFF.items():
    p=pdf.pages[idx]; x0,x1,y0,y1=FR[s]
    for o in p.lines+p.curves:
        k=key(o)
        if not k: continue
        pts=[((x+dx-836.9)*K,-(y+dy-305.5)*K) for x,y in o['pts']]
        cx=sum(p_[0] for p_ in pts)/len(pts); cy=sum(p_[1] for p_ in pts)/len(pts)
        if not (x0+3<cx<x1-3 and y0+3<cy<y1-3): continue
        sd=side(cx,cy)
        if (s==38 and sd>0) or (s==39 and sd<0): continue
        out[k].append({'s':s,'pts':[(round(a,3),round(b,3)) for a,b in pts],'closed':bool(o.get('fill'))})
json.dump(out,open('ext.json','w'))
print({k:len(v) for k,v in out.items()})
