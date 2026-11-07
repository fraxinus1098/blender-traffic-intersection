from PIL import Image
S=300/72; K=40/72
IM={24:('plans/sheet24_SC_signal_existing_1.png',0),25:('plans/sheet25_SC_signal_existing_2.png',594.7)}
def pt(X,Y,dx): return ((X/K+836.9-dx)*S, (-Y/K+305.5)*S)
def comp(sheet,cx,cy,render,out):
    f,dx=IM[sheet]; im=Image.open(f).convert('RGB')
    X0,X1,Y0,Y1=cx-90,cx+90,cy-70,cy+70
    a=pt(X0,Y1,dx); b=pt(X1,Y0,dx)
    c=im.crop((int(round(a[0])),int(round(a[1])),int(round(b[0])),int(round(b[1])))).resize((1800,1400),Image.LANCZOS)
    # fade the plan a bit
    c=Image.blend(c,Image.new('RGB',c.size,(255,255,255)),0.25)
    r=Image.open(render).convert('RGBA')
    # tint the render magenta-ish so it contrasts, keep alpha*0.75
    import numpy as np
    A=np.array(r).astype(float); A[...,3]*=0.7
    A[...,0]=np.clip(A[...,0]*0.4+150,0,255); A[...,1]*=0.3; A[...,2]=np.clip(A[...,2]*0.4+120,0,255)
    r=Image.fromarray(A.astype('uint8'))
    c=c.convert('RGBA'); c.alpha_composite(r); c.convert('RGB').resize((1200,933),Image.LANCZOS).save(out)
comp(24,-170,-20,'work/p4_plancheck_SB.png','comp_SB.png')
comp(25,215,20,'work/p4_plancheck_NB.png','comp_NB.png')
