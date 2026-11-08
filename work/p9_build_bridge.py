"""Phase 9A.2: SH 249 mainlane bridge rebuild (illustrative context) -> work/p9_bridge.json (Blender metres).

Run from the repo root with the venv:  .venv/bin/python work/p9_build_bridge.py
Inputs: work/p9_lidar.json (profile, axis, alignment), lidar/p9_grids.npz (ground grid, from p9_lidar.py),
        work/p3_rd_masks.npz (pavement classes). Output objects (all context):
  CTX_SH249_Deck        deck slab between the measured abutments (lidar class-17 extent), top = lidar profile
  CTX_SH249_Girders     17 Tx46-type girders per span (rectangular fascia beams outside)
  CTX_SH249_Bents       bent caps + square columns (N/C/S medians as Phase 3, plus one bent at each header-bank toe),
                        abutment caps
  CTX_SH249_Rails       safety-shape barriers (outside + median) along the whole corridor, red stripe over the span
  CTX_SH249_Embankment  mainline fill beyond the abutments (top = profile), header-bank slope paving under the deck
                        ends, side slopes from the lidar ground
  CTX_SH249_Markings    mainlane lane lines (3 lanes per direction)
Coordinates: s along the SH 249 axis (north +), q across (east +), v = Y - 0.045 X (perpendicular to Spring Cypress;
the bents and abutments are lines of constant v). All plan feet until the output (x 0.3048)."""
import json, math, sys
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point
sys.path.insert(0, 'work')
from p6_common import FT, X0, X1, Y0, Y1, mask_class

J = json.load(open('work/p9_lidar.json'))
B = J['bridge']
AX = np.array(B['axis_unit']); NR = np.array(B['normal_unit']); C0 = np.array(B['centre_on_Y0']); W = B['deck_width_ft']
HW = W / 2
Fm = np.load('work/p3_rd_masks.npz')['final']
g = np.load('lidar/p9_grids.npz'); G = ndi.gaussian_filter(g['G'].astype(float), 3.0)      # ~5 ft: smooth slopes, no facet noise
GX0, GY1, GC = float(g['x0']), float(g['y1']), float(g['cell_ft'])

# ------------------------------------------------------------------ frames
def xy(s, q):
    s, q = np.asarray(s, float), np.asarray(q, float)
    return C0[0] + s * AX[0] + q * NR[0], C0[1] + s * AX[1] + q * NR[1]
def vof(x, y): return np.asarray(y) - 0.045 * np.asarray(x)
def s_at_v(v, q):
    """s on the line of constant q where v(x, y) = v"""
    x0, y0 = xy(0, q); dv = AX[1] - 0.045 * AX[0]
    return (v - vof(x0, y0)) / dv

# lidar mainlane profile (smoothed), heights ft above the Spring Cypress pavement
ps = np.array([p['s'] for p in B['profile']]); pt = np.array([p['top'] for p in B['profile']])
pt = np.convolve(np.pad(pt, 2, mode='edge'), np.ones(5) / 5, mode='valid')
def top(s): return np.interp(s, ps, pt)

def ground(x, y):
    """lidar ground (ft above the pavement reference); NaN outside the crop"""
    c = (np.asarray(x) - GX0) / GC - .5; r = (GY1 - np.asarray(y)) / GC - .5
    out = ndi.map_coordinates(G, [np.ravel(r), np.ravel(c)], order=1, mode='constant', cval=np.nan)
    ok = (np.ravel(c) >= 0) & (np.ravel(c) <= G.shape[1] - 1) & (np.ravel(r) >= 0) & (np.ravel(r) <= G.shape[0] - 1)
    out[~ok] = np.nan
    return out.reshape(np.shape(x))

# supports: measured abutment lines (class-17 ends, v = a + b q), bents at constant v
V_ABUT_N = lambda q: 171.9 + 0.055 * q
V_ABUT_S = lambda q: -177.2 - 0.0175 * q
V_TOE_N, V_TOE_S = 96.0, -104.0          # header-bank toe: ~4 ft behind the U-turn curb lines under the deck
BENTS = {'S2': -112.0, 'S': -58.4, 'C': -1.1, 'N': 56.9, 'N2': 104.0}   # N/C/S = Phase 3 median bents
SLAB, GIRDER_D = 0.75, 3.83              # 9-in. slab, Tx46 girder (46 in.)
STRUCT = SLAB + GIRDER_D                 # deck top -> girder bottom
CAP_W, CAP_D, COL = 3.5, 3.0, 3.0
S_END = 450.0                            # corridor modelled to |s| <= 450 ft (inside the lidar crop)
Q_SIDE = 75.0                            # side slopes modelled up to 75 ft outside the deck edges

OBJ = {}
class Mesh:
    def __init__(s, mats): s.V, s.F, s.M, s.mats = [], [], [], mats
    def add(s, V, F, mi):
        o = len(s.V); s.V += [tuple(map(float, v)) for v in V]
        for f in F: s.F.append([i + o for i in f]); s.M.append(mi)
    def out(s, uv=False):
        d = dict(v=[[round(a * FT, 4) for a in v] for v in s.V], f=s.F, m=s.M, mats=s.mats)
        if uv:   # rastUVmap: aerial affine on world metres
            d['uv'] = [[0.00080944 * v[0] * FT + 0.00004195 * v[1] * FT + 0.49524,
                        -0.00006261 * v[0] * FT + 0.00120811 * v[1] * FT + 0.49744] for v in s.V]
        return d

def grid_surface(m, P, mi, flip=False):
    """P: array (nu, nq, 3) of points -> quads"""
    nu, nq = P.shape[:2]; V = P.reshape(-1, 3); F = []
    for i in range(nu - 1):
        for j in range(nq - 1):
            a, b, c, d = i * nq + j, (i + 1) * nq + j, (i + 1) * nq + j + 1, i * nq + j + 1
            F.append([a, d, c, b] if not flip else [a, b, c, d])
    m.add(V, F, mi)

def sweep(m, pts, prof, mi, caps=True):
    """pts: (n, 3) path (horizontal tangent); prof: [(dq, dz)] CCW seen from the path start -> tube"""
    pts = np.asarray(pts, float); n, k = len(pts), len(prof)
    V = []
    for i in range(n):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]; t = t[:2] / np.hypot(*t[:2])
        nn = np.array([t[1], -t[0]])                      # right of the path
        for dq, dz in prof: V.append((pts[i, 0] + dq * nn[0], pts[i, 1] + dq * nn[1], pts[i, 2] + dz))
    F = []
    for i in range(n - 1):
        for j in range(k):
            a, b = i * k + j, i * k + (j + 1) % k
            F.append([a, b, b + k, a + k])
    if caps:
        F.append(list(range(k))[::-1]); F.append([(n - 1) * k + j for j in range(k)])
    m.add(V, F, mi)

def box(m, cx, cy, ux, uy, hw_u, hw_w, z0, z1, mi):
    """box centred (cx, cy), half-sizes along unit u and its normal, z0..z1"""
    wx, wy = -uy, ux; V = []
    for z in (z0, z1):
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            V.append((cx + a * hw_u * ux + b * hw_w * wx, cy + a * hw_u * uy + b * hw_w * wy, z))
    m.add(V, [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], mi)

def stations(a, b, step):
    n = max(1, int(math.ceil(abs(b - a) / step))); return np.linspace(a, b, n + 1)

# ------------------------------------------------------------------ deck slab
deck = Mesh(['MAT_P9_Mainlane', 'MAT_Bridge_Concrete'])
qs = stations(-HW, HW, 6.0); us = np.linspace(0, 1, 61)
def deck_pts(dz):
    P = np.zeros((len(us), len(qs), 3))
    for j, q in enumerate(qs):
        sa, sb = s_at_v(V_ABUT_S(q), q), s_at_v(V_ABUT_N(q), q)
        s = sa + us * (sb - sa); x, y = xy(s, q)
        P[:, j] = np.stack([x, y, top(s) + dz], 1)
    return P
Pt, Pb = deck_pts(0.0), deck_pts(-SLAB)
grid_surface(deck, Pt, 0)
grid_surface(deck, Pb, 1, flip=True)
# edges: walls along the four sides
for P_t, P_b in ((Pt[:, 0], Pb[:, 0]), (Pt[:, -1][::-1], Pb[:, -1][::-1]), (Pt[0][::-1], Pb[0][::-1]), (Pt[-1], Pb[-1])):
    n = len(P_t); V = list(P_t) + list(P_b)
    deck.add(V, [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)], 1)
OBJ['CTX_SH249_Deck'] = deck

# ------------------------------------------------------------------ girders (per span, between supports)
gird = Mesh(['MAT_Bridge_Concrete'])
supports = [('AS', V_ABUT_S), *[(k, (lambda v: (lambda q: v))(v)) for k, v in sorted(BENTS.items(), key=lambda kv: kv[1])], ('AN', V_ABUT_N)]
NG = 17
gq = np.linspace(-HW + 3.0, HW - 3.0, NG)
I_PROF = [(-1.33, 0), (1.33, 0), (1.33, 0.55), (0.29, 1.1), (0.29, 3.2), (1.75, 3.45), (1.75, 3.83), (-1.75, 3.83),
          (-1.75, 3.45), (-0.29, 3.2), (-0.29, 1.1), (-1.33, 0.55)]          # Tx46-like, z from girder bottom
FASCIA = [(-1.4, 0), (1.4, 0), (1.4, 3.83), (-1.4, 3.83)]
for (na, fa), (nb, fb) in zip(supports[:-1], supports[1:]):
    for j, q in enumerate(gq):
        sa = s_at_v(fa(q), q) + (2.0 if na.startswith('A') else 1.0)
        sb = s_at_v(fb(q), q) - (2.0 if nb.startswith('A') else 1.0)
        s = stations(sa, sb, 10.0); x, y = xy(s, q)
        path = np.stack([x, y, top(s) - STRUCT], 1)
        prof = FASCIA if j in (0, NG - 1) else I_PROF
        # sweep's dq is to the right of the path (path runs north, right = east = +q): keep as is
        sweep(gird, path, [(-dq, dz) for dq, dz in prof][::-1], 0)
OBJ['CTX_SH249_Girders'] = gird

# ------------------------------------------------------------------ bents, columns, abutment caps
bent = Mesh(['MAT_Bridge_Concrete'])
SC_DIR = np.array([1.0, 0.045]) / math.hypot(1, 0.045)
def hb(v):
    """header-bank surface (ft) under the deck ends, from the toe up to the abutment seat"""
    v = np.asarray(v, float); z = np.zeros_like(v)
    for toe, ab in ((V_TOE_N, V_ABUT_N(0)), (V_TOE_S, V_ABUT_S(0))):
        t = np.clip((v - toe) / (ab - 3 - toe), 0, 1); z = np.maximum(z, 0.5 + t * (top(s_at_v(ab, 0)) - STRUCT - 2.0 - 0.5))
    return z
# ground-level equipment (cabinets, pads, ground boxes, signs, ped poles) from v11: columns keep 2 ft clear
KO = [b for b in json.load(open('work/p9_keepout.json'))['boxes']
      if b['zmin'] < 3 and b['x1'] - b['x0'] < 15 and b['y1'] - b['y0'] < 15]
def keepout(px, py, clear=2.0 + COL * 0.71):
    for b in KO:
        dx = max(b['x0'] - px, 0, px - b['x1']); dy = max(b['y0'] - py, 0, py - b['y1'])
        if math.hypot(dx, dy) < clear: return b['name']
    return None
report = {}
for name, v in BENTS.items():
    # cap line: from the west deck edge to the east deck edge at this v (+1 ft each side)
    sw, se = s_at_v(v, -HW - 1), s_at_v(v, HW + 1)
    xw, yw = xy(sw, -HW - 1); xe, ye = xy(se, HW + 1)
    L = math.hypot(xe - xw, ye - yw); ux, uy = (xe - xw) / L, (ye - yw) / L
    n = int(L // 3.0)
    cap_pts = []
    for t in np.linspace(0, L, n + 1):
        x, y = xw + ux * t, yw + uy * t
        s = (x - C0[0]) * AX[0] + (y - C0[1]) * AX[1]
        cap_pts.append((x, y, top(s) - STRUCT - CAP_D))
    sweep(bent, cap_pts, [(-CAP_W / 2, 0), (CAP_W / 2, 0), (CAP_W / 2, CAP_D), (-CAP_W / 2, CAP_D)][::-1], 0)
    # columns about every 22 ft along the cap, only off pavement/curb (nudged up to 6 ft across the cap line)
    cols = []
    for t in np.arange(6.0, L - 5.9, (L - 12.0) / max(1, round((L - 12.0) / 22.0))):
        x, y = xw + ux * t, yw + uy * t
        best = None
        for d in sorted(np.arange(-6, 6.01, 0.5), key=abs) if name in ('N', 'C', 'S') else [0.0, 2.0, -2.0, 4.0, -4.0]:
            px, py = x - uy * d, y + ux * d
            ring = [(px + 1.7 * math.cos(a), py + 1.7 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)] + [(px, py)]
            cl = mask_class(Fm, np.array([p[0] for p in ring]), np.array([p[1] for p in ring]))
            if not np.isin(cl, (1, 4)).any() and not keepout(px, py): best = (px, py); break
        if best is None: continue
        px, py = best
        s = (px - C0[0]) * AX[0] + (py - C0[1]) * AX[1]
        zt = top(s) - STRUCT - CAP_D
        zb = (hb(vof(px, py)) - 0.5) if name.endswith('2') else 0.5
        box(bent, px, py, ux, uy, COL / 2, COL / 2, float(zb), float(zt), 0); cols.append((round(px, 1), round(py, 1)))
    report[name] = dict(v=v, columns=cols)
# abutment caps: v in [abut - 3, abut + 1.5], from 2 ft below the girder bottom to the slab bottom
for fa, sgn in ((V_ABUT_N, 1), (V_ABUT_S, -1)):
    qq = stations(-HW, HW, 6.0)
    for v_lo, v_hi, dz_lo, dz_hi in ((-3.0, 0.0, -STRUCT - 2.0, -STRUCT), (0.0, 1.5, -STRUCT - 2.0, -SLAB)):
        P = []
        for q in qq:
            row = []
            for dv in ((v_lo, v_hi) if sgn > 0 else (-v_hi, -v_lo)):
                s = s_at_v(fa(q) + dv, q); x, y = xy(s, q); row.append((x, y, top(s)))
            P.append(row)
        P = np.array(P)                      # (nq, 2, 3)
        lo = P.copy(); lo[..., 2] += dz_lo; hi = P.copy(); hi[..., 2] += dz_hi
        nq = len(qq); V = list(lo.reshape(-1, 3)) + list(hi.reshape(-1, 3)); o = nq * 2; F = []
        for i in range(nq - 1):
            a, b = i * 2, (i + 1) * 2
            F += [[o + a, o + a + 1, o + b + 1, o + b], [a, b, b + 1, a + 1],          # top, bottom
                  [a, a + o, b + o, b], [a + 1, b + 1, b + 1 + o, a + 1 + o]]          # the two long faces
        F += [[0, 1, 1 + o, o], [(nq - 1) * 2, (nq - 1) * 2 + o, (nq - 1) * 2 + 1 + o, (nq - 1) * 2 + 1]]
        bent.add(V, F, 0)
OBJ['CTX_SH249_Bents'] = bent

# ------------------------------------------------------------------ embankment: mainline fill, header banks, side slopes
emb = Mesh(['MAT_P9_Mainlane', 'MAT_P9_SlopePaving', 'MAT_Embankment'])
# (a) mainline top beyond each abutment, |q| <= HW, top = profile
for fa, s_far in ((V_ABUT_N, S_END), (V_ABUT_S, -S_END)):
    uu = np.linspace(0, 1, 46); rows = []
    for q in qs:
        sa = s_at_v(fa(q), q); s = sa + uu * (s_far - sa); x, y = xy(s, q)
        rows.append(np.stack([x, y, top(s)], 1))
    P = np.stack(rows, 1)
    grid_surface(emb, P, 0, flip=s_far < 0)
# (b) header banks under the deck ends, |q| <= HW, from the toe to 3 ft short of the abutment line
hb_rows = {}
for toe, fa, sgn in ((V_TOE_N, V_ABUT_N, 1), (V_TOE_S, V_ABUT_S, -1)):
    uu = np.linspace(0, 1, 21); rows = []
    for q in qs:
        v = toe + uu * (fa(q) - 3 * sgn - toe); s = s_at_v(v, q); x, y = xy(s, q)
        rows.append(np.stack([x, y, hb(v)], 1))
    P = np.stack(rows, 1); grid_surface(emb, P, 1, flip=sgn < 0)
    hb_rows[sgn] = P
# (c) side slopes outside the deck edges from the lidar ground; inner edge shares the deck-edge heights
def inner_z(s, side):
    q = side * HW; x, y = xy(s, q); v = vof(x, y)
    vN, vS = V_ABUT_N(q), V_ABUT_S(q)
    if v >= vN or v <= vS: return float(top(s))
    if V_TOE_N <= v < vN: return float(hb(v)) if v < vN - 3 else float(top(s) - STRUCT - 2.0)
    if vS < v <= V_TOE_S: return float(hb(v)) if v > vS + 3 else float(top(s) - STRUCT - 2.0)
    return None
SS = stations(-S_END, S_END, 3.0)
for side in (-1, 1):
    QQ = HW + np.arange(0, Q_SIDE + 0.1, 3.0)
    S2, Q2 = np.meshgrid(SS, QQ, indexing='ij')
    X2, Y2 = xy(S2, side * Q2)
    H = ground(X2, Y2)
    for i, s in enumerate(SS):
        z = inner_z(s, side); H[i, 0] = np.nan if z is None else z
    inside_model = (X2 >= X0) & (X2 <= X1) & (Y2 >= Y0) & (Y2 <= Y1)
    hard = np.isin(mask_class(Fm, X2.ravel(), Y2.ravel()).reshape(X2.shape), (1, 4, 5)) & inside_model
    V2 = vof(X2, Y2)
    # vertices on plan pavement/curb/sidewalk dip just below the pavement, so the slope runs into the pavement edge
    # instead of ending in 3-ft steps; elsewhere the lidar ground, floored just above the aerial plane (-0.33 ft)
    Z2 = np.where(np.isfinite(H), np.maximum(H, -0.25), 0.0)
    Z2[:, 1:] = np.where(hard[:, 1:], -0.25, Z2[:, 1:])
    nq = len(QQ); Vv = [(X2[i, j], Y2[i, j], Z2[i, j]) for i in range(len(SS)) for j in range(nq)]
    F, Mi = [], []
    for i in range(len(SS) - 1):
        for j in range(nq - 1):
            c = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            hv = [H[a, b] for a, b in c]
            if not all(np.isfinite(hv)) or max(Z2[a, b] for a, b in c) < 0.6: continue
            ids = [a * nq + b for a, b in c]
            F.append(ids[::-1] if side > 0 else ids)
            vm = np.mean([V2[a, b] for a, b in c])
            near = (V_TOE_S - 5 <= vm <= V_TOE_N + 5) or (V_ABUT_S(0) - 50 <= vm <= V_ABUT_N(0) + 50)
            Mi.append(1 if near else 2)
    o = len(emb.V); emb.V += [tuple(map(float, v)) for v in Vv]
    emb.F += [[k + o for k in f] for f in F]; emb.M += Mi
OBJ['CTX_SH249_Embankment'] = emb

# ------------------------------------------------------------------ barriers (outside + median) and red stripe
rail = Mesh(['MAT_Bridge_Concrete', 'MAT_P9_Bridge_RedStripe'])
H_B = 2.67
OUT_PROF = [(0.0, 0.0), (0.0, H_B), (0.75, H_B), (1.0, 0.9), (1.75, 0.25), (1.75, 0.0)]  # outer face vertical (dq inward)
MED_PROF = [(-1.0, 0), (-0.75, 0.25), (-0.25, 0.9), (-0.25, H_B), (0.25, H_B), (0.25, 0.9), (0.75, 0.25), (1.0, 0)]
SR = stations(-S_END, S_END, 10.0)
for side in (-1, 1):
    x, y = xy(SR, side * HW); path = np.stack([x, y, top(SR)], 1)
    # path runs north; sweep's right = east (+q). Inward for the west barrier is +q, for the east barrier -q.
    prof = [(dq if side < 0 else -dq, dz) for dq, dz in OUT_PROF]
    if side > 0: prof = prof[::-1]
    sweep(rail, path, prof, 0)
    # red stripe on the outer face over the bridge span
    sa, sb = s_at_v(V_ABUT_S(side * HW), side * HW), s_at_v(V_ABUT_N(side * HW), side * HW)
    s = stations(sa, sb, 10.0); x, y = xy(s, side * (HW + 0.03))
    V = [(x[i], y[i], top(s[i]) + z) for i in range(len(s)) for z in (0.55, 1.25)]
    F = [[2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1] if side > 0 else [2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2] for i in range(len(s) - 1)]
    rail.add(V, F, 1)
x, y = xy(SR, 0.0); sweep(rail, np.stack([x, y, top(SR)], 1), MED_PROF[::-1], 0)
OBJ['CTX_SH249_Rails'] = rail

# ------------------------------------------------------------------ lane markings (3 lanes per direction)
mk = Mesh(['MAT_Paint_White', 'MAT_Paint_Yellow'])
LW = 0.5; DZ = 0.035
def ribbon(q, s0, s1, mi):
    s = stations(s0, s1, 10.0)
    xl, yl = xy(s, q - LW / 2); xr, yr = xy(s, q + LW / 2); z = top(s) + DZ
    V = [p for i in range(len(s)) for p in ((xl[i], yl[i], z[i]), (xr[i], yr[i], z[i]))]
    mk.add(V, [[2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2] for i in range(len(s) - 1)], mi)
for side in (-1, 1):
    ribbon(side * 13.0, -S_END, S_END, 1)            # inside edge line (yellow), 12-ft inside shoulder
    ribbon(side * 49.0, -S_END, S_END, 0)            # outside edge line (white)
    for q in (25.0, 37.0):                           # lane lines, 10 ft line / 30 ft gap
        for s0 in np.arange(-S_END, S_END - 10, 40.0): ribbon(side * q, s0, s0 + 10.0, 0)
OBJ['CTX_SH249_Markings'] = mk

# ------------------------------------------------------------------ trees standing on the new side slopes
trees = J['trees']['trees']; tree_z = {}
for i, t in enumerate(trees):
    s = (t['x'] - C0[0]) * AX[0] + (t['y'] - C0[1]) * AX[1]; q = (t['x'] - C0[0]) * NR[0] + (t['y'] - C0[1]) * NR[1]
    if abs(s) <= S_END and HW <= abs(q) <= HW + Q_SIDE:
        h = float(ground(np.array([t['x']]), np.array([t['y']]))[0])
        if np.isfinite(h) and h > 0.6: tree_z[f"CTX_TREE_{i:03d}_{t['var']}"] = round(h * FT - 0.10, 3)

out = {k: m.out(uv=(k == 'CTX_SH249_Markings')) for k, m in OBJ.items()}
meta = dict(abutments=dict(N='v = 171.9 + 0.055 q', S='v = -177.2 - 0.0175 q', source='lidar class-17 extent'),
            toes=dict(N=V_TOE_N, S=V_TOE_S), bents=report, slab_ft=SLAB, girder_depth_ft=GIRDER_D,
            n_girders=NG, deck_top_crest_ft=round(float(top(0)), 2),
            deck_top_ends_ft=[round(float(top(s_at_v(V_ABUT_S(0), 0))), 2), round(float(top(s_at_v(V_ABUT_N(0), 0))), 2)],
            min_soffit_over_spring_cypress_ft=round(float(min(top(s) for s in np.arange(-70, 71, 5)) - STRUCT), 2),
            corridor_s_ft=[-S_END, S_END], tree_z_m=tree_z)
json.dump(dict(objects=out, meta=meta), open('work/p9_bridge.json', 'w'))
print({k: (len(m.V), len(m.F)) for k, m in OBJ.items()})
print(json.dumps({k: v for k, v in meta.items() if k != 'bents'}, indent=0)[:900])
print({k: len(v['columns']) for k, v in report.items()})
