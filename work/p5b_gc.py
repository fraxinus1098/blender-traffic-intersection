import sys, math, json
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS=None
S=300/72; K=40/72
IM={40:('plans/sheet40_SC_markings_proposed_1.png',-51.6,-142.1),
    41:('plans/sheet41_SC_markings_proposed_2.png',724.2,-53.9)}
def pt(X,Y,dx,dy): return ((X/K+836.9-dx)*S, (-Y/K+305.5-dy)*S)
def crop(sheet,X0,X1,Y0,Y1,name,scale=1.0,marks=()):
    f,dx,dy=IM[sheet]; im=Image.open(f).convert('RGB')
    a=pt(X0,Y1,dx,dy); b=pt(X1,Y0,dx,dy)
    c=im.crop((int(a[0]),int(a[1]),int(b[0]),int(b[1]))); d=ImageDraw.Draw(c)
    for X in range(int(math.ceil(X0/10)*10), int(X1)+1, 10):
        x=pt(X,0,dx,dy)[0]-a[0]; d.line([(x,0),(x,c.height)],fill=(255,190,190)); d.text((x+2,2),str(X),fill=(200,0,0))
    for Y in range(int(math.ceil(Y0/10)*10), int(Y1)+1, 10):
        y=pt(0,Y,dx,dy)[1]-a[1]; d.line([(0,y),(c.width,y)],fill=(190,190,255)); d.text((2,y+2),str(Y),fill=(0,0,200))
    for lab,X,Y in marks:
        x,y=pt(X,Y,dx,dy); x-=a[0]; y-=a[1]; d.ellipse([x-12,y-12,x+12,y+12],outline=(255,0,255),width=3); d.text((x+14,y-6),str(lab),fill=(255,0,255))
    c=c.resize((int(c.width*scale),int(c.height*scale)),Image.LANCZOS); c.save(name)
if __name__=='__main__':
    pads=json.load(open('pads.json'))
    a=sys.argv; sh=int(a[1])
    crop(sh,*map(float,a[2:6]),a[6],float(a[7]),[(p['id'],p['x'],p['y']) for p in pads if p['s']==str(sh)])
