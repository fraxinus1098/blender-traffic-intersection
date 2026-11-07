"""Phase 7 (container): approach / lane / crosswalk / radar-zone geometry in plan feet -> p7_data.json.
Inputs (work/): p5b_mk.json (classified sheet 40/41 markings), p5b_pads.json, p3_rd_masks.npz,
p5_proposed_signals.json is not needed; radar positions/aims are passed in RADARS below (read from the
P_RADAR_* objects' sh249_aim_deg in v08). Run: python3 p7_geom.py <work_dir> <out_json>
"""
import json, sys, math, numpy as np, cv2
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union

W = sys.argv[1] if len(sys.argv) > 1 else 'work/'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'work/p7_data.json'
X0, X1, Y0, Y1, RES = -400, 560, -240, 210, 0.25
mk = json.load(open(W + 'p5b_mk.json'))
pads = {p['id']: (p['x'], p['y']) for p in json.load(open(W + 'p5b_pads.json'))}
F = np.load(W + 'p3_rd_masks.npz')['final']

# ---------------- pavement polygon (class 1) ----------------
cnts, hier = cv2.findContours((F == 1).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
def px2ft(c): c = c.reshape(-1, 2).astype(float); return np.c_[X0 + (c[:, 0] + .5) * RES, Y1 - (c[:, 1] + .5) * RES]
polys = []
for i, c in enumerate(cnts):
    if hier[0][i][3] != -1 or len(c) < 4: continue
    holes = [px2ft(cnts[j]) for j in range(len(cnts)) if hier[0][j][3] == i and len(cnts[j]) >= 4]
    polys.append(Polygon(px2ft(c), holes).buffer(0))
PAVE = unary_union(polys).buffer(0.3).buffer(-0.3)
EXTENT = box(X0, Y0, X1, Y1)

# ---------------- approaches ----------------
# stop-bar fill indices in p5b_mk.json 'fills' (checked against sheet 40/41 plots, work/p7_geom_*.png)
SPEED = {'SB': 50, 'NB': 45, 'EB': 45, 'WB': 45}            # build doc: SB feeder 50, NB feeder 45, Spring Cypress 45
APPROACHES = [  # key, intersection, direction, stop-bar fills, upstream axis guess (deg), radars
    ('SB_SB', 'SB', 'SB', [10], 121, ['PR1', 'ADV1'], ['O', 'P', 'Q']),
    ('SB_EB', 'SB', 'EB', [24], 184, ['PR2', 'ADV2'], ['K', 'L', 'M', 'N']),
    ('SB_WB', 'SB', 'WB', [31, 32, 33], 4, ['PR3'], ['R', 'S', 'T']),
    ('NB_NB', 'NB', 'NB', [89], 301, ['PR6', 'ADV4'], ['E', 'F', 'G']),
    ('NB_EB', 'NB', 'EB', [106], 184, ['PR4'], ['H', 'I', 'J']),
    ('NB_WB', 'NB', 'WB', [98], 4, ['PR5', 'ADV3'], ['A', 'B', 'C', 'D']),
]
EXPECT = {10: (-208.8, 54.4), 24: (-207.7, -40.9), 31: (-150.1, 22.3), 32: (-135.4, 11.1), 33: (-121.7, 0.2),
          89: (241.1, -56.4), 98: (250.7, 40.7), 106: (173.3, -11.9)}
for i, (ex, ey) in EXPECT.items():
    c = Polygon(mk['fills'][i]).centroid
    assert abs(c.x - ex) < .2 and abs(c.y - ey) < .2, ('stop bar index moved', i)

def unit(a): return np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
def axis_from_lines(pt, guess, rad=150):
    """length-weighted mean direction (deg, near guess) of lane lines on the upstream side of pt."""
    u0 = unit(guess); acc = np.zeros(2)
    for l in mk['lines']:
        a, b = np.array(l[0]), np.array(l[1]); v = b - a; L = np.linalg.norm(v)
        if L < 8: continue
        m = (a + b) / 2 - pt
        if np.linalg.norm(m) > rad or m @ u0 < 0: continue
        v = v / L
        if abs(v @ u0) < math.cos(math.radians(12)): continue
        acc += (v if v @ u0 > 0 else -v) * L
    return math.degrees(math.atan2(acc[1], acc[0]))

LANE_EYE_BACK = 8.0    # ft: driver's eye behind the upstream edge of the stop bar (front bumper at the bar)
app_out = []
for key, inter, dirn, bars, guess, radars, heads in APPROACHES:
    bar = unary_union([Polygon(mk['fills'][i]) for i in bars])
    c = np.array(bar.centroid.coords[0])
    ang = axis_from_lines(c, guess); u = unit(ang); n = np.array([-u[1], u[0]])
    # road coords: s along u (upstream), t along n
    def st(p): p = np.asarray(p) - c; return np.array([p @ u, p @ n])
    def xy(s, t): return c + s * u + t * n
    bpts = np.array([st(p) for p in np.vstack([np.array(g.exterior.coords) for g in getattr(bar, 'geoms', [bar])])])
    tmin, tmax = bpts[:, 1].min(), bpts[:, 1].max()
    def s_edge(t):  # upstream edge of the bar at t
        ln = LineString([xy(-200, t), xy(200, t)]); g = ln.intersection(bar)
        if g.is_empty: return None
        return max(st(q)[0] for q in (g.coords if g.geom_type == 'LineString' else [q for gg in g.geoms for q in gg.coords]))
    # lane boundaries: bar ends + lane lines crossing the s-window just upstream of the bar
    tb = [tmin, tmax]
    segs = [l[:2] for l in mk['lines']] + [[p, q] for l in mk['dotted'] for p, q in zip(l[:-1], l[1:])]
    for l in segs:
        a, b = st(l[0]), st(l[1])
        if abs((b - a)[0]) < 4 or abs((b - a)[1]) / abs((b - a)[0]) > .25: continue
        # t of the line where it overlaps the first 60 ft upstream of the bar centre
        lo, hi = sorted([a[0], b[0]])
        lo2, hi2 = max(lo, -10), min(hi, 70)
        if hi2 - lo2 < 3: continue
        sm = (lo2 + hi2) / 2; tm = a[1] + (b[1] - a[1]) * (sm - a[0]) / (b[0] - a[0])
        if tmin + 3 < tm < tmax - 3: tb.append(tm)
    tb = sorted(tb); ded = [tb[0]]
    for t in tb[1:]:
        if t - ded[-1] > 4: ded.append(t)
    lanes = []
    for t0, t1 in zip(ded[:-1], ded[1:]):
        tc = (t0 + t1) / 2; se = s_edge(tc)
        if se is None: continue
        # hatched gore (not a travel lane)? any 12-in. hatch segment inside this lane within 80 ft of the bar
        gore = sum(1 for h in mk['hatch'] if all(t0 - 1 < st(p)[1] < t1 + 1 and -5 < st(p)[0] < 80 for p in h[:2]))
        if gore >= 2: continue
        e = xy(se + LANE_EYE_BACK, tc)
        lanes.append(dict(t=round(tc, 2), width=round(t1 - t0, 2), eye=[round(e[0], 2), round(e[1], 2)],
                          bar_edge=[round(v, 2) for v in xy(se, tc)],
                          on_pavement=bool(PAVE.contains(Point(e)))))
    # corridor: bar upstream edge extruded upstream (used for radar zones)
    e1, e2 = xy(s_edge(tmin + .3), tmin + .3), xy(s_edge(tmax - .3), tmax - .3)
    app_out.append(dict(key=key, inter=inter, dir=dirn, bars=bars, axis_up_deg=round(ang, 2),
                        travel_deg=round((ang + 360) % 360 - 180, 2), bar_centre=c.round(2).tolist(),
                        bar_ends=[e1.round(2).tolist(), e2.round(2).tolist()], lanes=lanes, radars=radars,
                        heads=heads, speed_mph=SPEED[dirn], width_ft=round(tmax - tmin, 1)))

# ---------------- crosswalks ----------------
BARS = []
for f in mk['fills']:
    p = Polygon(f); r = p.minimum_rotated_rectangle; a = np.array(r.exterior.coords)[:4]
    e = sorted(np.linalg.norm(a[(k + 1) % 4] - a[k]) for k in range(4))
    if 1.1 < e[0] < 2.2 and 6.5 < e[3] < 8.6: BARS.append(np.array(p.centroid.coords[0]))
BARS = np.array(BARS)
CROSSWALKS = [  # key, from (pad id or xy), to, ped poles, ramps note
    ('SB_N', 4, 3, 'E -> D', 'north leg, across the SB feeder (departure)'),
    ('SB_W', 5, 9, 'F -> G -> H', 'west leg, across Spring Cypress via the west-median cut-through (Type 21, pads 6-7)'),
    ('SB_S', 8, 0, 'I -> J', 'south leg, across the SB feeder (approach)'),
    ('SB_CH', 2, 1, '(no ped signal; S6 R1-5BL)', 'SB right-turn channel, NW island (Type 22 walkway 1-4-5)'),
    ('NB_N', 13, 17, 'T -> S', 'north leg, across the NB feeder (approach side north)'),
    ('NB_E', (231.3, 76.5), 15, 'R -> Q -> P', 'east leg, across Spring Cypress via the east-median cut-through (Type 21, pads 16-18)'),
    ('NB_S', 12, 14, 'N -> O', 'south leg, across the NB feeder'),
    ('NB_CH', 11, 10, '(no ped signal; S6 R1-5BL)', 'NB right-turn channel, SE island (Type 22 walkway 10-14-15)'),
]
cw_out = []
for key, a, b, peds, note in CROSSWALKS:
    A = np.array(pads[a] if isinstance(a, int) else a); B = np.array(pads[b] if isinstance(b, int) else b)
    d = (B - A) / np.linalg.norm(B - A); nrm = np.array([-d[1], d[0]])
    rel = BARS - A; s = rel @ d; t = rel @ nrm
    sel = (s > -6) & (s < np.linalg.norm(B - A) + 6) & (np.abs(t) < 7)
    pts = BARS[sel]
    first = pts[np.argmin((pts - A) @ d)]
    cam = first - 5.0 * d                                   # 5 ft behind the first bar: on the ramp / landing
    cw_out.append(dict(key=key, from_=a if isinstance(a, int) else list(a), to=b, peds=peds, note=note,
                       n_bars=int(sel.sum()), cam=cam.round(2).tolist(), dir_deg=round(math.degrees(math.atan2(d[1], d[0])), 2),
                       length_ft=round(float(np.linalg.norm(B - A)), 1), target=B.round(2).tolist()))

# ---------------- radar zones ----------------
RADARS = {  # from v08 P_RADAR_* (plan ft, sh249_aim_deg)
    'PR1': ((-247.02, 41.89), 18.5), 'PR2': ((-166.79, -89.88), 125.6), 'PR3': ((-106.97, -20.96), 57.0),
    'PR4': ((140.74, 21.21), -114.0), 'PR5': ((207.55, 86.01), -58.3), 'PR6': ((285.18, -44.64), -132.8),
    'ADV1': ((-135.07, -83.79), 122.1), 'ADV2': ((-102.61, -29.77), -175.2),
    'ADV3': ((138.78, 29.52), 5.5), 'ADV4': ((169.42, 74.76), -58.9)}
PR_LEN = 50.0                     # ft upstream of the stop bar
PR_FOV, PR_RANGE = 45.0, 140.0    # half-angle, range of a typical stop-bar presence radar (generic)
ADV_T = (2.5, 5.5)                # s of travel time upstream: Type-II dilemma zone
ADV_HALF = 6.0                    # beam half-angle (deg), generic long-range advance radar
def sector(o, aim, half, r0, r1, n=48):
    a0, a1 = math.radians(aim - half), math.radians(aim + half)
    arc = lambda r: [(o[0] + r * math.cos(a), o[1] + r * math.sin(a)) for a in np.linspace(a0, a1, n)]
    return Polygon(arc(r1) + arc(r0)[::-1] if r0 > 0 else [tuple(o)] + arc(r1))
def corridor(app, s0, s1):
    u = unit(app['axis_up_deg']); e1, e2 = np.array(app['bar_ends'])
    return Polygon([e1 + s0 * u, e2 + s0 * u, e2 + s1 * u, e1 + s1 * u])
def clip_road(g):  # inside the model extent keep pavement only; outside it keep the corridor as is
    return unary_union([g.intersection(PAVE), g.difference(EXTENT)]).buffer(0)
def polys_of(g):
    gs = [g] if g.geom_type == 'Polygon' else [x for x in getattr(g, 'geoms', []) if x.geom_type == 'Polygon']
    return [x for x in gs if x.area > 4]
zones = []
for app in app_out:
    for rid in app['radars']:
        o, aim = RADARS[rid]; o = np.array(o)
        if rid.startswith('PR'):
            g = clip_road(corridor(app, 0, PR_LEN))
            fov = sector(o, aim, PR_FOV, 0, PR_RANGE)
            cover = g.intersection(fov).area / g.area
            rng = None; desc = '%s stop-bar presence zone: full approach width, stop bar to %d ft upstream' % (app['dir'], PR_LEN)
        else:
            v = app['speed_mph'] * 5280 / 3600; d0, d1 = ADV_T[0] * v, ADV_T[1] * v
            u = unit(app['axis_up_deg']); s_r = float((np.array(app['bar_centre']) - o) @ u)  # radar -> bar along road
            g = clip_road(corridor(app, d0, d1).intersection(sector(o, aim, ADV_HALF, 0, s_r + d1 + 60)))
            cover = None; rng = [round(d0), round(d1)]
            desc = '%s advance (dilemma-zone) detection: %d-%d ft upstream of the stop bar (%.1f-%.1f s at %d mph), %g-deg beam on the radar aim' % (
                app['dir'], d0, d1, ADV_T[0], ADV_T[1], app['speed_mph'], 2 * ADV_HALF)
        ps = polys_of(g)
        # label anchor: inside the zone, readable for the approaching driver
        lab = g.representative_point() if not g.is_empty else Point(o)
        big = max(ps, key=lambda p: p.area)
        lab = big.centroid if big.contains(big.centroid) else big.representative_point()
        zones.append(dict(id=rid, approach=app['key'], inter=app['inter'], dir=app['dir'], kind='PR' if rid.startswith('PR') else 'ADV',
                          radar_xy=o.tolist(), aim_deg=aim, polys=[np.array(p.exterior.coords).round(2).tolist() for p in ps],
                          holes=[[np.array(h.coords).round(2).tolist() for h in p.interiors] for p in ps],
                          area_ft2=round(g.area), fov_cover=None if cover is None else round(cover, 3), range_ft=rng,
                          label_xy=[round(lab.x, 2), round(lab.y, 2)], label_rot_deg=round(app['travel_deg'] - 90, 2),
                          outside_extent_frac=round(g.difference(EXTENT).area / max(g.area, 1e-6), 3), desc=desc))

json.dump(dict(approaches=app_out, crosswalks=cw_out, zones=zones,
               params=dict(LANE_EYE_BACK=LANE_EYE_BACK, PR_LEN=PR_LEN, PR_FOV=PR_FOV, PR_RANGE=PR_RANGE, ADV_T=ADV_T, ADV_HALF=ADV_HALF)),
          open(OUT, 'w'), indent=1)
for a in app_out:
    print(a['key'], 'axis', a['axis_up_deg'], 'w', a['width_ft'], 'lanes', [(l['t'], l['width'], l['on_pavement']) for l in a['lanes']])
for c in cw_out: print(c['key'], c['n_bars'], c['cam'], c['dir_deg'], c['length_ft'])
for z in zones: print(z['id'], z['approach'], z['area_ft2'], z['fov_cover'], z['range_ft'], z['outside_extent_frac'], len(z['polys']))
