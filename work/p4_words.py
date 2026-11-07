import pdfplumber, json
pdf=pdfplumber.open('plans/SH249_Select_Sheets.pdf')
K=40/72
OFF={24:(1,0,0),25:(2,594.7,0)}
def X(x,dx): return (x+dx-836.9)*K
def Y(y,dy): return -(y+dy-305.5)*K
out={}
for s,(idx,dx,dy) in OFF.items():
    p=pdf.pages[idx]
    ws=p.extract_words(keep_blank_chars=False, extra_attrs=['size'])
    L=[]
    for w in ws:
        x=(w['x0']+w['x1'])/2; y=(w['top']+w['bottom'])/2
        if x>1000 or (x<330 and y>460) or y>570: continue
        L.append((w['text'],round(w['size'],1),round(x,1),round(y,1),round(X(x,dx),1),round(Y(y,dy),1)))
    out[s]=L
    for l in L:
        if len(l[0])<=2: print(s,l)
json.dump(out,open('words.json','w'))
