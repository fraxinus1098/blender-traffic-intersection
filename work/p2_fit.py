import numpy as np, math, sys
from PIL import Image
from scipy.ndimage import map_coordinates, gaussian_filter, sobel
U = ''
RES = 0.25; X0, Y1 = -170.0, 90.0
OE, ON = 250132.603, 3323063.683
UL_E, UL_N, PX = 249515.695, 3323477.014, 1233.771728515625 / 2000
g = np.array(Image.open(U + 'imagery/SH249_SpringCypress_NAIP2022_60cm.tif').convert('L')).astype(np.float32)
g = gaussian_filter(g, 1.0)
E = np.hypot(sobel(g, 0), sobel(g, 1)); E /= np.percentile(E, 99)
plan = np.load('plan_long.npy')
r, c = np.nonzero(plan > .3)
rng = np.random.default_rng(0); k = rng.choice(len(r), min(40000, len(r)), replace=False)
PXs = X0 + (c[k] + .5) * RES; PYs = Y1 - (r[k] + .5) * RES

def score(dx, dy, rot):
    t = math.radians(rot); cs, sn = math.cos(t), math.sin(t)
    WX = cs * PXs - sn * PYs + dx; WY = sn * PXs + cs * PYs + dy
    col = (OE + WX - UL_E) / PX - .5; row = (UL_N - (ON + WY)) / PX - .5
    return map_coordinates(E, [row, col], order=1).mean()

def search(cx, cy, cr, span, step, rspan, rstep):
    best = (-1, 0, 0, 0)
    for rot in np.arange(cr - rspan, cr + rspan + 1e-9, rstep):
        for dx in np.arange(cx - span, cx + span + 1e-9, step):
            for dy in np.arange(cy - span, cy + span + 1e-9, step):
                s = score(dx, dy, rot)
                if s > best[0]: best = (s, dx, dy, rot)
    return best

print('zero', score(0, 0, 0))
b = search(0, 0, 0, 15, 1, 3, .5); print('coarse', b)
b = search(b[1], b[2], b[3], 3, .5, 1, .25); print('mid', b)
b = search(b[1], b[2], b[3], .6, .1, .2, .05); print('fine', b)
# robustness: top local maxima on coarse grid
res=[]
for rot in np.arange(-3,3.01,.5):
    for dx in np.arange(-15,15.01,1):
        for dy in np.arange(-15,15.01,1):
            res.append((score(dx,dy,rot),dx,dy,rot))
res.sort(reverse=True)
seen=[]
for s,dx,dy,rot in res:
    if all(abs(dx-a)+abs(dy-b)>4 for _,a,b,_r in seen): seen.append((s,dx,dy,rot))
    if len(seen)==6: break
for x in seen: print('peak',x)
