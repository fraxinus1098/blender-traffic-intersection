from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS=None
S=300/72; K=40/72
IM={26:('plans/sheet26_SC_signal_proposed_1.png',-9.8,-25.8),
    27:('plans/sheet27_SC_signal_proposed_2.png',453.9,-33.2)}
def pt(X,Y,dx,dy): return ((X/K+836.9-dx)*S, (-Y/K+305.5-dy)*S)
def comp(sheet,cx,cy,render,out):
    f,dx,dy=IM[sheet]; im=Image.open(f).convert('RGB')
    X0,X1,Y0,Y1=cx-90,cx+90,cy-70,cy+70
    a=pt(X0,Y1,dx,dy); b=pt(X1,Y0,dx,dy)
    c=im.crop((int(round(a[0])),int(round(a[1])),int(round(b[0])),int(round(b[1])))).resize((1800,1400),Image.LANCZOS)
    c=Image.blend(c,Image.new('RGB',c.size,(255,255,255)),0.25)
    r=Image.open(render).convert('RGBA')
    A=np.array(r).astype(float); A[...,3]*=0.7
    A[...,0]=np.clip(A[...,0]*0.4+150,0,255); A[...,1]*=0.3; A[...,2]=np.clip(A[...,2]*0.4+120,0,255)
    r=Image.fromarray(A.astype('uint8'))
    c=c.convert('RGBA'); c.alpha_composite(r); c=c.convert('RGB'); c.save(out.replace('.png','_full.png')); c.resize((1200,933),Image.LANCZOS).save(out)
comp(26,-170,-20,'work/p5_plancheck_SB.png','comp_SB.png')
comp(27,215,20,'work/p5_plancheck_NB.png','comp_NB.png')
