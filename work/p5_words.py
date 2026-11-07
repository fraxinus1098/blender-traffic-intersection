import pdfplumber, json
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
K=40/72
OFF={26:(3,-9.8,-25.8),27:(4,453.9,-33.2)}
def X(x,dx): return (x+dx-836.9)*K
def Y(y,dy): return -(y+dy-305.5)*K
out={}
for s,(idx,dx,dy) in OFF.items():
    p=pdf.pages[idx]
    ws=p.extract_words(keep_blank_chars=False, extra_attrs=['size','upright'])
    L=[]
    for w in ws:
        x=(w['x0']+w['x1'])/2; y=(w['top']+w['bottom'])/2
        if x>1000 or x<240 or y>640: continue
        L.append((w['text'],round(w['size'],1),round(x,1),round(y,1),round(X(x,dx),1),round(Y(y,dy),1)))
    out[s]=L
    for l in L:
        if len(l[0])<=5 or l[0][:3] in ('ADV','PR1','PR2','PR3','PR4','PR5','PR6'): print(s,l)
json.dump(out,open('words.json','w'))
