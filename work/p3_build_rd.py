"""Phase 3: build existing-roadway surface classes from sheet 38/39 curb linework.
Classes: 1 pavement, 2 island, 3 roadside, 4 curb band (1 ft), 5 sidewalk (assumed).
Outputs rd_masks.npz and rd_mesh.json (Blender metres, plan origin, with aerial UVs)."""
import json, math, numpy as np, cv2
from PIL import Image, ImageDraw
from scipy.ndimage import label, distance_transform_edt, binary_fill_holes
from shapely.geometry import Polygon
import mapbox_earcut as earcut

RES = 0.25; X0, X1, Y0, Y1 = -400, 560, -240, 210
NX, NY = int((X1 - X0) / RES), int((Y1 - Y0) / RES)
FT = 0.3048
g = lambda X, Y: ((X - X0) / RES, (Y1 - Y) / RES)

D = json.load(open('ext.json'))
BL = [((-22.8, -103.6), (-165.7, 143.2)), ((41.3, 71.8), (172.2, -154.3))]
def near_bridge(a, b):
    L = math.dist(a, b)
    if L < 1: return False
    for p, q in BL:
        Lq = math.dist(p, q); ux, uy = (q[0]-p[0])/Lq, (q[1]-p[1])/Lq
        if abs((b[0]-a[0])/L*uy - (b[1]-a[1])/L*ux) > 0.03: continue
        dist = lambda r: abs((r[0]-p[0])*uy - (r[1]-p[1])*ux)
        if dist(a) < 3.5 and dist(b) < 3.5: return True
    return False

im = Image.new('L', (NX, NY), 0); d = ImageDraw.Draw(im)
for o in D['gray']:
    pts = o['pts']
    for a, b in zip(pts, pts[1:]):
        if not near_bridge(a, b): d.line([g(*a), g(*b)], fill=255, width=3)
for seg in json.load(open('closures_all.json')):
    d.line([g(*p) for p in seg], fill=255, width=3)
d.rectangle([0, 0, NX-1, NY-1], outline=255, width=2)
B = np.array(im) > 0
lab, n = label(~B)
area = np.bincount(lab.ravel()) * RES * RES
def L_at(X, Y): return lab[int((Y1 - Y) / RES), int((X - X0) / RES)]
pave = L_at(0, 30)
assert pave == L_at(-300, 10) == L_at(400, 35) == L_at(300, -150) == L_at(-250, 120), 'pavement not connected'

big = (area >= 40); big[0] = False; big[pave] = False
border = set(np.unique(np.concatenate([lab[2, :], lab[-3, :], lab[:, 2], lab[:, -3]])))
cls = np.zeros((NY, NX), np.uint8)
cls[lab == pave] = 1
isl_ids, rs_ids = [], []
for i in np.nonzero(big)[0]:
    m = lab == i
    if i in border: cls[m] = 3; rs_ids.append(int(i))
    else: cls[m] = 2; isl_ids.append(int(i))
# fill holes inside islands/roadside (trees, signs), small enclosed bits in pavement -> pavement
for c in (2, 3):
    f = binary_fill_holes(cls == c) & (cls != 3 - c + 0 if c == 2 else True)
    cls[f & ((cls == 0) | ((cls == 1) & ~(lab == pave)))] = c
# unassigned (line pixels, tiny regions) -> nearest class
idx = distance_transform_edt(cls == 0, return_distances=False, return_indices=True)
cls = cls[idx[0], idx[1]]
# per-island label map (after fill) for naming
isl_lab, nisl = label(cls == 2)
# curb band: non-pavement within 1.0 ft of pavement
dpave = distance_transform_edt(cls != 1) * RES
curb = (cls != 1) & (dpave <= 1.0)
# assumed sidewalk: roadside 1-6 ft behind curb, within 120 ft of each intersection centre, not under bridge
gx = X0 + (np.arange(NX) + .5) * RES; gy = Y1 - (np.arange(NY) + .5) * RES
GX, GY = np.meshgrid(gx, gy)
near_int = (np.hypot(GX + 235, GY - 5) < 120) | (np.hypot(GX - 245, GY + 10) < 120)
def sdist(p, q):
    Lq = math.dist(p, q); ux, uy = (q[0]-p[0])/Lq, (q[1]-p[1])/Lq
    return (GX - p[0]) * uy - (GY - p[1]) * ux
s1 = sdist(*BL[0]); s2 = sdist(*BL[1])
ub = (np.sign(s1) == np.sign(s2))
sidewalk = (cls == 3) & ~curb & (dpave > 1.0) & (dpave <= 6.0) & near_int & ~ub
final = cls.copy(); final[curb] = 4; final[sidewalk] = 5
for i in range(1, nisl + 1):
    m = isl_lab == i
    if m.sum() * RES * RES < 300: final[m & (final == 2)] = 3
np.savez_compressed('rd_masks.npz', final=final, isl=isl_lab)
print('islands', nisl, 'areas sqft:', {c: round(float((final == c).sum() * RES * RES)) for c in range(1, 6)})

# ---------- vectorise ----------
OE, ON = 250132.603, 3323063.683; UL_E, UL_N = 249515.695, 3323477.014; PXS = 1233.771728515625 / 2000
t = math.radians(-2.9668); ct, st = math.cos(t), math.sin(t)
def uv(X, Y):
    x, y = X * FT, Y * FT; E = OE + ct * x - st * y - 5.9; N = ON + st * x + ct * y - 2.1
    return ((E - UL_E) / PXS / 2000, 1 - (UL_N - N) / PXS / 1340)
def px2ft(p): return (X0 + p[0] * RES, Y1 - p[1] * RES)

def polys(mask, simp=0.15, minarea=4):
    m = (mask.astype(np.uint8)) * 255
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    if hier is None: return out
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1: continue
        shell = [px2ft((p[0][0] + .5, p[0][1] + .5)) for p in c]
        holes = []; j = hier[i][2]
        while j != -1:
            holes.append([px2ft((p[0][0] + .5, p[0][1] + .5)) for p in cs[j]]); j = hier[j][0]
        if len(shell) < 3: continue
        P = Polygon(shell, [h for h in holes if len(h) >= 3]).buffer(0).simplify(simp)
        geoms = getattr(P, 'geoms', [P])
        for G in geoms:
            if G.area >= minarea: out.append(G)
    return out

def tri(G, z):
    rings = [list(G.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in G.interiors]
    verts = [p for r in rings for p in r]
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    f = earcut.triangulate_float64(np.array(verts, np.float64), ends).reshape(-1, 3)
    V = [(x * FT, y * FT, z * FT) for x, y in verts]
    UV = [uv(x, y) for x, y in verts]
    return V, f.tolist(), UV

def mesh_of(geoms, z, walls_to=None):
    V, F, UV = [], [], []
    for G in geoms:
        v, f, u = tri(G, z); o = len(V)
        V += v; UV += u; F += [[a + o, b + o, c + o] for a, b, c in f]
    return {'v': V, 'f': F, 'uv': UV}

Z = 0.5  # 6-inch curb
out = {}
out['E_RD_Pavement'] = mesh_of(polys(final == 1), 0.0)
cg = polys(final == 4, simp=0.2, minarea=0.5)
cm = mesh_of(cg, Z)
# curb face: walls along pavement boundary (skip domain border)
wv, wf = [], []
for G in polys(final == 1):
    for r in [G.exterior] + list(G.interiors):
        c = list(r.coords)
        for a, b in zip(c, c[1:]):
            on_border = any(abs(a[k] - lim) < 1 and abs(b[k] - lim) < 1 for k, lim in ((0, X0), (0, X1), (1, Y0), (1, Y1)))
            if on_border: continue
            o = len(cm['v']) + len(wv)
            wv += [(a[0]*FT, a[1]*FT, 0), (b[0]*FT, b[1]*FT, 0), (b[0]*FT, b[1]*FT, Z*FT), (a[0]*FT, a[1]*FT, Z*FT)]
            wf += [[o, o+1, o+2], [o, o+2, o+3]]
cm['v'] += wv; cm['f'] += wf; cm['uv'] += [(0, 0)] * len(wv)
out['E_RD_Curb'] = cm
out['E_RD_Sidewalk_assumed'] = mesh_of(polys(final == 5, minarea=2), Z)
out['E_RD_Roadside'] = mesh_of(polys(final == 3), Z)
# islands individually, named by centroid
names = []
for i in range(1, nisl + 1):
    m = (isl_lab == i) & (final == 2)
    if m.sum() * RES * RES < 300: continue
    gs = polys(m)
    if not gs: continue
    cx = sum(G.centroid.x for G in gs) / len(gs); cy = sum(G.centroid.y for G in gs) / len(gs)
    nm = f'E_ISL_{"N" if cy>=0 else "S"}{abs(round(cy)):03d}_{"W" if cx<0 else "E"}{abs(round(cx)):03d}'
    out[nm] = mesh_of(gs, Z); names.append((nm, round(sum(G.area for G in gs))))
json.dump(out, open('rd_mesh.json', 'w'))
print({k: (len(v['v']), len(v['f'])) for k, v in out.items()})
print(names)
