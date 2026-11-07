import sys, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
P='plans/'
names={24:'sheet24_SC_signal_existing_1',25:'sheet25_SC_signal_existing_2',26:'sheet26_SC_signal_proposed_1',27:'sheet27_SC_signal_proposed_2',38:'sheet38_SC_markings_existing_1',39:'sheet39_SC_markings_existing_2',40:'sheet40_SC_markings_proposed_1',41:'sheet41_SC_markings_proposed_2'}
F=4  # downsample factor -> 1275x825
def load(s):
    im=Image.open(P+names[s]+'.png').convert('L').resize((5100//F,3300//F),Image.BOX)
    a=1.0-np.asarray(im,dtype=np.float32)/255.0
    m=np.zeros_like(a)
    # drawing frame in full px: x 300..3870, y 90..2460 ; exclude callout block lower-left & legend
    k=lambda v:int(v/F)
    m[k(90):k(2460),k(300):k(3870)]=1
    m[k(1900):,:k(1700)]=0   # callouts / head table
    m[:k(330),k(3850):]=0
    return a*m
def xcorr(a,b):
    A=np.fft.rfft2(a); B=np.fft.rfft2(b)
    R=A*np.conj(B); R/=np.abs(R)+1e-3
    r=np.fft.irfft2(R,s=a.shape)
    i=np.unravel_index(np.argmax(r),r.shape)
    dy,dx=[(v if v<n//2 else v-n) for v,n in zip(i,r.shape)]
    srt=np.sort(r.ravel())[::-1]
    return dx*F,dy*F,float(srt[0]),float(srt[1])
for p in sys.argv[1:]:
    s1,s2=map(int,p.split(','))
    dx,dy,pk,p2=xcorr(load(s1),load(s2))
    print(f'{s2}->{s1}: shift(px full) dx={dx} dy={dy}  peak={pk:.4f} 2nd={p2:.4f}')
