"""Phase 3: existing pavement markings from sheets 38/39 -> mk_mesh.json (Blender metres)."""
import json, math, numpy as np
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Polygon
import mapbox_earcut as earcut

FT = 0.3048; RES = 0.25; X0, Y1 = -400, 210
D = json.load(open('ext.json'))
F = np.load('rd_masks.npz')['final']
d_isl = distance_transform_edt(F != 2) * RES          # ft to nearest island
d_np = distance_transform_edt(F == 1) * RES           # ft inside pavement (to nearest non-pavement)
def rc(X, Y):
    r, c = int((Y1 - Y) / RES), int((X - X0) / RES)
    return (r, c) if 0 <= r < F.shape[0] and 0 <= c < F.shape[1] else None
def on_pave(X, Y, inset=0.4):
    p = rc(X, Y); return p is not None and F[p] == 1 and d_np[p] >= inset
def near_median(X, Y):
    p = rc(X, Y); return p is not None and d_isl[p] < 3.0

EXCL = [(-268,-243,92,132),(155,182,92,132),(-378,-338,-44,-26),(-34,-8,-102,-62),(-168,-157,-64,-53),(-136,-124,-58,-47),(-386,-364,44,57),(72,81,77,85)]
def excluded(X, Y): return any(a <= X <= b and c <= Y <= d for a, b, c, d in EXCL)
Z = 0.01 / FT   # 1 cm above pavement, in ft
W_LINE = 0.5    # 6-inch lines (assumed)
out = {'white': {'v': [], 'f': []}, 'yellow': {'v': [], 'f': []}}
def quad(m, a, b, w):
    L = math.dist(a, b)
    if L < 0.05: return
    nx, ny = -(b[1]-a[1])/L*w/2, (b[0]-a[0])/L*w/2
    o = len(m['v'])
    for x, y in ((a[0]+nx, a[1]+ny), (b[0]+nx, b[1]+ny), (b[0]-nx, b[1]-ny), (a[0]-nx, a[1]-ny)):
        m['v'].append((x*FT, y*FT, Z*FT))
    m['f'] += [[o, o+1, o+2], [o, o+2, o+3]]
def poly(m, pts):
    P = Polygon(pts).buffer(0)
    for G in getattr(P, 'geoms', [P]):
        if G.area < 0.05: continue
        r = list(G.exterior.coords)[:-1]
        f = earcut.triangulate_float64(np.array(r, np.float64), np.array([len(r)], np.uint32)).reshape(-1, 3)
        o = len(m['v']); m['v'] += [(x*FT, y*FT, Z*FT) for x, y in r]; m['f'] += [[a+o, b+o, c+o] for a, b, c in f.tolist()]

stats = {'line_seg': 0, 'dash_seg': 0, 'fill': 0, 'fill_drop_small': 0, 'fill_drop_leader': 0, 'xwalk': 0}
# solid 0.72 black lines: lane lines, hatching, edge lines
for o in D['mark']:
    p = o['pts']
    if o['closed'] and len(p) > 2:
        cx = sum(a for a, b in p)/len(p); cy = sum(b for a, b in p)/len(p)
        if on_pave(cx, cy) and not excluded(cx, cy): poly(out['white'], p); stats['fill'] += 1
        continue
    for a, b in zip(p, p[1:]):
        mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
        if not on_pave(mx, my) or excluded(mx, my): continue
        quad(out['yellow' if near_median(mx, my) else 'white'], a, b, W_LINE); stats['line_seg'] += 1
# dotted turn-guide lines (2.67 ft on / off as plotted)
for o in D['markdash']:
    p = o['pts']; on, off = 2.67, 2.67
    # resample polyline at 0.1 ft, then keep points in "on" phase and emit short quads
    acc = 0.0
    for a, b in zip(p, p[1:]):
        L = math.dist(a, b)
        if L < 1e-6: continue
        n = max(1, int(L / 0.25))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            mid = acc + (t0 + t1) / 2 * L
            if (mid % (on + off)) < on:
                A = (a[0]+(b[0]-a[0])*t0, a[1]+(b[1]-a[1])*t0); B = (a[0]+(b[0]-a[0])*t1, a[1]+(b[1]-a[1])*t1)
                if on_pave((A[0]+B[0])/2, (A[1]+B[1])/2): quad(out['white'], A, B, W_LINE); stats['dash_seg'] += 1
        acc += L
# filled shapes: arrows, words, stop bars. drop annotation glyphs (<3 ft) and leader wedges (thin & long)
for o in D['fill']:
    p = o['pts']
    if len(p) < 3: continue
    xs = [a for a, b in p]; ys = [b for a, b in p]
    ext = max(max(xs)-min(xs), max(ys)-min(ys))
    cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
    if not on_pave(cx, cy, 0.0) or excluded(cx, cy): continue
    if (141 <= cx <= 149 and 10 <= cy <= 72) or (-105 <= cx <= -97 and -72 <= cy <= -18): stats['fill_drop_leader'] += 1; continue
    if ext < 3.0: stats['fill_drop_small'] += 1; continue
    P = Polygon(p).buffer(0)
    mr = P.minimum_rotated_rectangle
    if P.area / max(ext, 1e-6) < 0.45 or (len(p) <= 5 and P.area / max(mr.area, 1e-6) < 0.7 and ext / max(P.area / ext, 1e-6) > 6):
        stats['fill_drop_leader'] += 1; continue
    poly(out['yellow' if near_median(cx, cy) and ext > 8 and P.area/ext < 2.5 else 'white'], p); stats['fill'] += 1
# gray closed boxes on pavement: existing crosswalk blocks
for o in D['gray']:
    p = o['pts']
    if len(p) < 4 or math.dist(p[0], p[-1]) > 0.3: continue
    xs = [a for a, b in p]; ys = [b for a, b in p]
    ext = max(max(xs)-min(xs), max(ys)-min(ys))
    if not (3 <= ext <= 14): continue
    if on_pave(sum(xs)/len(xs), sum(ys)/len(ys), 0.0): poly(out['white'], p); stats['xwalk'] += 1
json.dump(out, open('mk_mesh.json', 'w'))
print(stats, {k: (len(v['v']), len(v['f'])) for k, v in out.items()})
