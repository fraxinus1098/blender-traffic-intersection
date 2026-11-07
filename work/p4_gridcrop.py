import sys
from PIL import Image, ImageDraw
S=300/72; K=40/72
IM={24:('plans/sheet24_SC_signal_existing_1.png',0),25:('plans/sheet25_SC_signal_existing_2.png',594.7)}
def pt(X,Y,dx): return ((X/K+836.9-dx)*S, (-Y/K+305.5)*S)
def crop(sheet,X0,X1,Y0,Y1,name,step=10,scale=1.0):
    f,dx=IM[sheet]; im=Image.open(f).convert('RGB')
    a=pt(X0,Y1,dx); b=pt(X1,Y0,dx)
    c=im.crop((int(a[0]),int(a[1]),int(b[0]),int(b[1])))
    d=ImageDraw.Draw(c)
    import math
    for X in range(int(math.ceil(X0/step)*step), int(X1)+1, step):
        x=pt(X,0,dx)[0]-a[0]; d.line([(x,0),(x,c.height)],fill=(255,0,0) if X%50==0 else (255,170,170),width=1); d.text((x+2,2),str(X),fill=(200,0,0))
    for Y in range(int(math.ceil(Y0/step)*step), int(Y1)+1, step):
        y=pt(0,Y,dx)[1]-a[1]; d.line([(0,y),(c.width,y)],fill=(0,0,255) if Y%50==0 else (170,170,255),width=1); d.text((2,y+2),str(Y),fill=(0,0,200))
    c=c.resize((int(c.width*scale),int(c.height*scale)),Image.LANCZOS); c.save(name)
if __name__=='__main__':
    a=sys.argv; crop(int(a[1]),*map(float,a[2:6]),a[6],int(a[7]) if len(a)>7 else 10, float(a[8]) if len(a)>8 else 1.0)
