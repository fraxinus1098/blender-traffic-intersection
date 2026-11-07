import numpy as np, os
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS=None
B='plans/'
os.makedirs(B+'masked',exist_ok=True)
S=300/72.0  # px per pt
SL=0.584
# sheet: (file, side, match pt (x0,y0), xlim, ymax, excludes[(x0,y0,x1,y1)])
cfg={
 24:('sheet24_SC_signal_existing_1','L',(701.5,137.6),180,575,[(0,460,330,800)]),
 26:('sheet26_SC_signal_proposed_1','L',(711.3,163.4),235,585,[(0,485,330,800)]),
 38:('sheet38_SC_markings_existing_1','L',(807.9,279.7),180,765,[(880,560,1224,792)]),
 40:('sheet40_SC_markings_proposed_1','L',(807.9,279.7),180,765,[(880,560,1224,792)]),
 25:('sheet25_SC_signal_existing_2','R',(106.8,137.6),900,580,[(0,0,82,792),(0,455,330,800),(930,0,1224,330)]),
 27:('sheet27_SC_signal_proposed_2','R',(247.6,170.8),985,585,[(0,0,82,792),(0,440,330,800),(930,0,1224,330)]),
 39:('sheet39_SC_markings_existing_2','R',(78.1,271.2),1000,680,[(0,0,82,792),(0,0,82,792),(930,0,1224,330),(1040,0,1224,792),(880,560,1224,792)]),
 41:('sheet41_SC_markings_proposed_2','R',(75.9,266.5),1000,680,[(0,0,82,792),(0,0,82,792),(930,0,1224,330),(1040,0,1224,792),(880,560,1224,792)]),
}
for s,(f,side,(x0,y0),xl,ymax,exc) in cfg.items():
    im=Image.open(B+f+'.png').convert('RGB')
    xm=lambda y:x0+(y-y0)*SL
    if side=='L': poly=[(xl,30),(xm(30),30),(xm(ymax),ymax),(xl,ymax)]
    else:         poly=[(xm(30),30),(xl,30),(xl,ymax),(xm(ymax),ymax)]
    m=Image.new('L',im.size,0); d=ImageDraw.Draw(m)
    d.polygon([(x*S,y*S) for x,y in poly],fill=255)
    for a,b,c,e in exc: d.rectangle([a*S,b*S,c*S,e*S],fill=0)
    g=np.asarray(im.convert('L'),dtype=np.float32)
    alpha=np.clip((255-g)*1.6,0,255)*(np.asarray(m)/255.0)
    out=np.dstack([np.asarray(im),alpha.astype(np.uint8)])
    Image.fromarray(out,'RGBA').save(B+f'masked/{f}_mask.png',optimize=False,compress_level=3)
    Image.fromarray(out,'RGBA').resize((1275,825)).save(f'work/mask_{s}.png')
    print(s,'ok')
