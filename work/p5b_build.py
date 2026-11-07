"""Phase 5b: proposed pavement markings, curb ramps and S6 R1-5BL (sheets 40-41) -> p5b_proposed_mk_ramps.json (Blender metres).
Markings come from p5b_mk.py (p5b_mk.json); ramp pads from p5b_pads.py (pads.json)."""
import json, math, numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
import mapbox_earcut as earcut
FT = 0.3048; ZB = 0.5
Z_MK = 0.015 / FT          # proposed markings 1.5 cm above pavement (existing are at 1 cm)
Z_FLOOR = 0.02; Z_DW = 0.04
CUT_Z0 = 0.045             # cutters start above pavement and both marking layers
MATS = ['MAT_Paint_White', 'MAT_Paint_Yellow', 'MAT_Concrete', 'MAT_DetectWarn', 'MAT_Sign_White', 'MAT_Sign_Black',
        'MAT_Sign_Red', 'MAT_SigPole_Galv', 'MAT_RPM_White', 'MAT_RPM_Amber']
MI = {m: i for i, m in enumerate(MATS)}
D = json.load(open('p5b_mk.json')); PADS = json.load(open('pads.json'))
F = np.load('work/p3_rd_masks.npz')['final']
RES = 0.25; X0, Y1 = -400, 210
def cls(X, Y):
    r, c = int((Y1 - Y)/RES), int((X - X0)/RES)
    return int(F[r, c]) if 0 <= r < F.shape[0] and 0 <= c < F.shape[1] else 0

class Mesh:
    def __init__(s): s.v = []; s.f = []; s.m = []
    def add(s, V, Fc, mat):
        o = len(s.v); s.v += [list(map(float, p)) for p in V]
        for f in Fc: s.f.append([i + o for i in f]); s.m.append(MI[mat])
    def quad(s, a, b, w, z, mat):
        L = math.dist(a, b)
        if L < 0.05: return
        nx, ny = -(b[1]-a[1])/L*w/2, (b[0]-a[0])/L*w/2
        s.add([(a[0]+nx, a[1]+ny, z), (b[0]+nx, b[1]+ny, z), (b[0]-nx, b[1]-ny, z), (a[0]-nx, a[1]-ny, z)], [(0, 1, 2), (0, 2, 3)], mat)
    def poly(s, G, z, mat):
        for g in getattr(G, 'geoms', [G]):
            if g.area < 0.02: continue
            rings = [list(g.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in g.interiors]
            pts = [p for r in rings for p in r]; ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
            tri = earcut.triangulate_float64(np.array(pts, np.float64), ends).reshape(-1, 3)
            s.add([(x, y, z) for x, y in pts], [tuple(t) for t in tri.tolist()], mat)
    def box(s, c, size, yaw, mat):
        sx, sy, sz = [a/2 for a in size]; a = math.radians(yaw); ca, sa = math.cos(a), math.sin(a)
        V = [(c[0]+dx*ca-dy*sa, c[1]+dx*sa+dy*ca, c[2]+dz) for dz in (-sz, sz) for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy))]
        s.add(V, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)
    def wall(s, a, b, z0a, z1a, z0b, z1b, mat):
        s.add([(a[0], a[1], z0a), (b[0], b[1], z0b), (b[0], b[1], z1b), (a[0], a[1], z1a)], [(0, 1, 2, 3), (0, 3, 2, 1)], mat)

objs = []
def emit(name, m, origin, coll, props):
    o = np.array(origin, float); V = (np.array(m.v) - o) * FT
    objs.append(dict(name=name, coll=coll, loc=list(o * FT), v=V.round(4).tolist(), f=m.f, mi=m.m, props=props))
BASE = dict(sh249_status='new', sh249_phase='proposed')

# ------------------------------------------------------------------ markings
mw, my = Mesh(), Mesh()
for a, b, c in D['lines']: (my if c == 'yellow' else mw).quad(a, b, 0.5, Z_MK, 'MAT_Paint_Yellow' if c == 'yellow' else 'MAT_Paint_White')
for a, b, c in D['hatch']: (my if c == 'yellow' else mw).quad(a, b, 1.0, Z_MK, 'MAT_Paint_Yellow' if c == 'yellow' else 'MAT_Paint_White')
ON, OFF = 2.67, 2.67
for P in D['dotted']:
    acc = 0.0
    for a, b in zip(P, P[1:]):
        L = math.dist(a, b)
        if L < 1e-6: continue
        n = max(1, int(L / 0.25))
        for k in range(n):
            t0, t1 = k/n, (k+1)/n; mid = acc + (t0+t1)/2*L
            if mid % (ON+OFF) < ON:
                mw.quad((a[0]+(b[0]-a[0])*t0, a[1]+(b[1]-a[1])*t0), (a[0]+(b[0]-a[0])*t1, a[1]+(b[1]-a[1])*t1), 0.5, Z_MK, 'MAT_Paint_White')
        acc += L
for P in D['fills']:
    G = Polygon(P).buffer(0)
    if not G.is_empty: mw.poly(G, Z_MK, 'MAT_Paint_White')
note_mk = ('Proposed pavement markings, sheets 40-41 legend: A 24-in. white stop bars and crosswalk bars; B 6-in. broken white; '
           'D 6-in. solid; E 8-in. solid; H 12-in. gore hatching; K 6-in. dotted guide lines; F/G/L/M prefab words and arrows; '
           'C 6-in. black shadow (shown white). Sheet 23 note 37.')
emit('P_MK_White', mw, (0, 0, 0), 'P_Markings', dict(BASE, sh249_callout='A-H, K-M', sh249_sheet='40, 41', sh249_type='pavement markings (white)', sh249_note=note_mk))
emit('P_MK_Yellow', my, (0, 0, 0), 'P_Markings', dict(BASE, sh249_callout='D, H', sh249_sheet='40, 41', sh249_type='pavement markings (yellow, median edges)',
     sh249_note='Proposed yellow lines and gore hatching along median noses (colour inferred: within 3 ft of a median island).'))
mr = Mesh()
for x, y, med in D['rpm']:
    mr.box((x, y, 0.035), (0.33, 0.33, 0.07), 0, 'MAT_RPM_Amber' if med else 'MAT_RPM_White')
emit('P_MK_RPM', mr, (0, 0, 0), 'P_Markings', dict(BASE, sh249_callout='J', sh249_sheet='40, 41', sh249_type='raised pavement markers',
     sh249_note='J: Refl pav mrkr Ty I-C (sheets 40-41), at the plan symbol positions; amber next to medians.'))

# ------------------------------------------------------------------ curb ramps
TYPE = {0: 1, 1: 22, 2: 1, 3: 1, 4: 22, 5: 22, 6: 21, 7: 21, 8: 5, 9: 5,
        10: 22, 11: 1, 12: 1, 13: 1, 14: 22, 15: 22, 16: 21, 17: 5, 18: 21}
CORNER = {0: 'SE corner, SB int.', 1: 'NW channel island, SB int.', 2: 'NW corner across the SB right-turn channel', 3: 'NE corner, SB int.',
          4: 'NW channel island, SB int.', 5: 'NW channel island, SB int.', 6: 'west median, SB int.', 7: 'west median, SB int.',
          8: 'SW corner, SB int.', 9: 'SW corner, SB int.', 10: 'SE channel island, NB int.', 11: 'SE corner across the NB right-turn channel',
          12: 'SW corner, NB int.', 13: 'NW corner, NB int.', 14: 'SE channel island, NB int.', 15: 'SE channel island, NB int.',
          16: 'east median, NB int.', 17: 'NE corner, NB int.', 18: 'east median, NB int.'}
pad = {p['id']: p for p in PADS}
def pad_frame(p):
    ax = math.radians(p['axis']); u = np.array([math.cos(ax), math.sin(ax)]); n = np.array([-u[1], u[0]])
    c = np.array([p['x'], p['y']])
    # n points away from pavement (towards the raised side)
    fwd = sum(cls(*(c + n*d)) == 1 for d in (1, 2, 3, 4, 5, 6, 7)); back = sum(cls(*(c - n*d)) == 1 for d in (1, 2, 3, 4, 5, 6, 7))
    if fwd > back: n = -n
    if p['id'] == 2: n = -np.array([math.cos(math.radians(154)), math.sin(math.radians(154))])   # Phase 3 surface is all pavement here; ramp runs up away from the crosswalk
    return c, u, n
def rect(c, u, n, L, d0, d1):
    return Polygon([tuple(c + u*L/2 + n*d0), tuple(c - u*L/2 + n*d0), tuple(c - u*L/2 + n*d1), tuple(c + u*L/2 + n*d1)])
def raised_out(a, b, G):
    m = (np.array(a) + np.array(b))/2; e = np.array(b) - np.array(a); L = np.linalg.norm(e)
    if L < 1e-6: return False
    nn = np.array([-e[1], e[0]])/L
    q = m + nn*0.6
    if G.contains(Point(*q)): q = m - nn*0.6
    return cls(*q) != 1
cutters = []
PL = 5.6; PD = 2.0; RUN = 6.0
done = set()
groups = [(6, 7), (16, 18), (1, 4, 5), (10, 14, 15)]
for g in groups:                       # cut-through walkways (Types 21 and 22)
    ts = TYPE[g[0]]; m = Mesh(); rects = []
    for i in g:
        c, u, n = pad_frame(pad[i]); rects.append(rect(c, u, n, PL, -PD/2, PD/2)); done.add(i)
    if ts == 21:
        G = unary_union(rects).convex_hull
    else:
        a, b, c3 = g; hub = unary_union([rects[1], rects[2]]).convex_hull
        G = unary_union([hub, LineString([(pad[a]['x'], pad[a]['y']), tuple(hub.centroid.coords[0])]).buffer(PL/2, cap_style=2), rects[0]])
    G = G.buffer(0)
    m.poly(G, Z_FLOOR, 'MAT_Concrete')
    for r in rects: m.poly(r.buffer(-0.05), Z_DW, 'MAT_DetectWarn')
    ext = G if G.geom_type == 'Polygon' else max(G.geoms, key=lambda q: q.area)
    co = list(ext.exterior.coords)
    for a, b in zip(co, co[1:]):
        if raised_out(a, b, G): m.wall(a, b, Z_FLOOR, ZB, Z_FLOOR, ZB, 'MAT_Concrete')
    cutters.append(G.buffer(-0.1))
    nm = 'P_RAMP_T%d_%s' % (ts, '_'.join(str(i) for i in g))
    desc = ('Type 21 median cut-through' if ts == 21 else 'Type 22 island walkway') + ' with detectable warnings at each end'
    emit(nm, m, tuple(G.centroid.coords[0]) + (0,), 'P_Ramps', dict(BASE, sh249_callout='Curb ramp Type %d' % ts, sh249_sheet=40 if pad[g[0]]['s'] == '40' else 41,
         sh249_type='curb ramp Type %d' % ts, sh249_note='Prop. curb ramp (Type %d), %s: modeled as a %s at pavement level.' % (ts, CORNER[g[0]], desc)))
for i, p in pad.items():               # perpendicular ramps (Types 1 and 5)
    if i in done: continue
    ts = TYPE[i]; c, u, n = pad_frame(p); m = Mesh()
    P0 = rect(c, u, n, PL, -PD/2, PD/2)
    m.poly(P0, Z_FLOOR, 'MAT_Concrete'); m.poly(P0.buffer(-0.05), Z_DW, 'MAT_DetectWarn')
    a0, b0 = c + n*PD/2 + u*PL/2, c + n*PD/2 - u*PL/2           # bottom of ramp run
    a1, b1 = a0 + n*RUN, b0 + n*RUN                               # top
    m.add([(*a0, Z_FLOOR), (*b0, Z_FLOOR), (*b1, ZB), (*a1, ZB)], [(0, 1, 2), (0, 2, 3)], 'MAT_Concrete')
    for s_ in (1, -1) if not all(cls(*(c + n*d)) == 1 for d in (2, 4, 6, 8)) else ():   # side walls of the cut (flares simplified)
        e0 = c + n*(-PD/2) + u*s_*PL/2; e1 = c + n*PD/2 + u*s_*PL/2; e2 = e1 + n*RUN
        m.wall(e0, e1, Z_FLOOR, ZB, Z_FLOOR, ZB, 'MAT_Concrete'); m.wall(e1, e2, Z_FLOOR, ZB, ZB, ZB, 'MAT_Concrete')
    G = rect(c, u, n, PL - 0.1, -PD/2 + 0.05, PD/2 + RUN - 0.05)
    free = all(cls(*(c + n*d)) == 1 for d in (2, 4, 6, 8))
    if free:   # no raised ground modeled here: freestanding ramp + 4-ft landing, closed down to the pavement
        a2, b2 = a1 + n*4.0, b1 + n*4.0
        m.add([(*a1, ZB), (*b1, ZB), (*b2, ZB), (*a2, ZB)], [(0, 1, 2), (0, 2, 3)], 'MAT_Concrete')
        for e0, e1 in ((a0, a1), (b0, b1)): m.wall(e0, e1, 0, Z_FLOOR, 0, ZB, 'MAT_Concrete')
        for e0, e1 in ((a1, a2), (b1, b2), (a2, b2)): m.wall(e0, e1, 0, ZB, 0, ZB, 'MAT_Concrete')
    else:
        cutters.append(G)
    kind = 'Type 5 with mountable curb' if ts == 5 else 'Type 1'
    emit('P_RAMP_T%d_%d' % (ts, i), m, (c[0], c[1], 0), 'P_Ramps', dict(BASE, sh249_callout='Curb ramp Type %d' % ts, sh249_sheet=int(p['s']),
         sh249_type='curb ramp Type %d' % ts, sh249_note='Prop. curb ramp (%s), %s: 5.6-ft ramp, 1:12 run of 6 ft from gutter to the 6-in. curb level, 2-ft detectable warning at the bottom.' % (kind, CORNER[i])))
cut = []
for k, G in enumerate(cutters):
    co = list(G.exterior.coords)[:-1]
    cut.append(dict(name='P_CUT_%02d' % k, ring=[(x*FT, y*FT) for x, y in co]))

# ------------------------------------------------------------------ S6 R1-5BL (36x36), ground-mounted
def U(d): a = math.radians(d); return np.array([math.cos(a), math.sin(a), 0.0])
text = []
for tag, (x, y), face in (('SB', (-282.2, 95.3), 68.0), ('NB', (316.8, -98.1), -118.5)):
    m = Mesh(); f = U(face); r = U(face + 90)
    m.box((x, y, ZB + 4.4), (0.2, 0.2, 8.8), face, 'MAT_SigPole_Galv')
    c = np.array([x, y, ZB + 7.0 + 1.5]) + f*0.15
    m.box(c, (0.06, 3.0, 3.0), face, 'MAT_Sign_Black'); m.box(c + f*0.035, (0.01, 2.85, 2.85), face, 'MAT_Sign_White')
    o = c + f*0.045 + r*0.55 + np.array([0, 0, 0.75])                  # red octagon (driver's view: upper right)
    rr = 0.48; V = [o + (r*math.cos(math.radians(22.5+45*k)) + np.array([0, 0, 1])*math.sin(math.radians(22.5+45*k)))*rr for k in range(8)]
    m.add(V, [tuple(range(8))], 'MAT_Sign_Red'); m.add(V, [tuple(range(7, -1, -1))], 'MAT_Sign_Red')
    p = c + f*0.045 + r*0.75 + np.array([0, 0, -0.55])                 # pedestrian symbol (simplified)
    m.box(p + np.array([0, 0, 0.42]), (0.01, 0.16, 0.16), face, 'MAT_Sign_Black')
    m.box(p + np.array([0, 0, 0.05]), (0.01, 0.16, 0.5), face, 'MAT_Sign_Black')
    m.box(p + np.array([0, 0, -0.38]) + r*0.07, (0.01, 0.09, 0.42), face, 'MAT_Sign_Black'); m.box(p + np.array([0, 0, -0.38]) - r*0.07, (0.01, 0.09, 0.42), face, 'MAT_Sign_Black')
    a = c + f*0.045 - r*0.45 + np.array([0, 0, -0.35])                 # left-down arrow (simplified)
    m.box(a + r*0.25, (0.01, 0.6, 0.1), face, 'MAT_Sign_Black')
    t = a - r*0.25; m.add([t - r*0.2, t + np.array([0, 0, 0.18]), t - np.array([0, 0, 0.18])], [(0, 1, 2), (0, 2, 1)], 'MAT_Sign_Black')
    emit('P_SIGN_S6_R1-5BL_%s' % tag, m, (x, y, ZB), 'P_Signs', dict(BASE, sh249_callout='S6', sh249_sheet=40 if tag == 'SB' else 41,
         sh249_type='ground-mounted regulatory sign R1-5BL', sh249_note='Prop. S6 R1-5BL "Stop here for pedestrians", 36 x 36 in. (sheets 40-41), at the plan symbol by the %s right-turn channel stop bar, facing approaching traffic.' % ('SB feeder' if tag == 'SB' else 'NB feeder')))
    text.append(dict(name='P_SIGN_S6_R1-5BL_%s' % tag, face=face, items=[
        ('STOP', list((o + f*0.006)*FT), 0.62, 0.2, 'MAT_Sign_White'),
        ('HERE', list((c + f*0.042 - r*0.45 + np.array([0, 0, 0.75]))*FT), 1.1, 0.42, 'MAT_Sign_Black'),
        ('FOR', list((c + f*0.042 + r*0.05 + np.array([0, 0, -0.95]))*FT), 0.8, 0.38, 'MAT_Sign_Black')]))
json.dump(dict(mats=MATS, objs=objs, cutters=cut, text=text), open('work/p5b_proposed_mk_ramps.json', 'w'))
for o in objs: print(o['name'], len(o['f']))
print('cutters', len(cut))
