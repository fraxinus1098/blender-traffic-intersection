"""Phase 3: SH 249 mainlane bridge as context -> br_mesh.json (Blender metres). Elevations assumed."""
import json, math, numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import split
import mapbox_earcut as earcut
FT = 0.3048
X0, X1, Y0, Y1 = -400, 560, -240, 210
F = np.load('rd_masks.npz')['final']; RES = 0.25
def cls(X, Y):
    r, c = int((Y1 - Y) / RES), int((X - X0) / RES)
    return int(F[r, c]) if 0 <= r < F.shape[0] and 0 <= c < F.shape[1] else -1

W = ((-22.8, -103.6), (-165.7, 143.2)); E = ((41.3, 71.8), (172.2, -154.3))
def at_y(l, y):
    (x1, y1), (x2, y2) = l; return (x1 + (x2 - x1) * (y - y1) / (y2 - y1), y)
deck = Polygon([at_y(W, Y0), at_y(W, Y1), at_y(E, Y1), at_y(E, Y0)]).intersection(box(X0, Y0, X1, Y1))
L = math.dist(*W); ax = ((W[1][0]-W[0][0])/L, (W[1][1]-W[0][1])/L)   # axis unit (north)
nrm = (ax[1], -ax[0])                                                   # points east
width = abs((E[0][0]-W[0][0])*nrm[0] + (E[0][1]-W[0][1])*nrm[1])

Z_SOFFIT, Z_DECK, RAIL_H, RAIL_W = 18.0, 24.0, 2.67, 1.25   # assumed (ft)
# abutment lines (parallel to Spring Cypress), from the under-bridge curb lines
NAB = lambda x: 88.9 + 0.045 * (x + 42.3) + 1.0
SAB = lambda x: -100.0 + 0.077 * (x + 25.0) - 1.0
north = Polygon([(X0, NAB(X0)), (X1, NAB(X1)), (X1, Y1), (X0, Y1)])
south = Polygon([(X0, SAB(X0)), (X1, SAB(X1)), (X1, Y0), (X0, Y0)])

out = {}
def prism(G, z0, z1, uv=False):
    V, Fc = [], []
    geoms = getattr(G, 'geoms', [G])
    for g in geoms:
        if g.is_empty or g.area < 0.5: continue
        r = list(g.exterior.coords)[:-1]
        if Polygon(r).exterior.is_ccw is False: r = r[::-1]
        n = len(r)
        f = earcut.triangulate_float64(np.array(r, np.float64), np.array([n], np.uint32)).reshape(-1, 3).tolist()
        o = len(V)
        V += [(x*FT, y*FT, z1*FT) for x, y in r] + [(x*FT, y*FT, z0*FT) for x, y in r]
        Fc += [[a+o, b+o, c+o] for a, b, c in f] + [[c+o+n, b+o+n, a+o+n] for a, b, c in f]
        for i in range(n):
            j = (i + 1) % n
            Fc += [[o+i, o+i+n, o+j+n], [o+i, o+j+n, o+j]]
    return {'v': V, 'f': Fc}
def merge(ms):
    V, Fc = [], []
    for m in ms:
        o = len(V); V += m['v']; Fc += [[a+o, b+o, c+o] for a, b, c in m['f']]
    return {'v': V, 'f': Fc}

out['CTX_SH249_Deck'] = prism(deck, Z_SOFFIT, Z_DECK)
rails = []
for (p, q), sgn in ((W, 1), (E, -1)):
    a, b = at_y((p, q), Y0), at_y((p, q), Y1)
    ln = LineString([a, b]); off = ln.parallel_offset(RAIL_W, 'left' if sgn * (b[1]-a[1]) > 0 else 'right')
    rp = Polygon(list(ln.coords) + list(off.coords)[::-1] if off.coords[0] != b else list(ln.coords) + list(off.coords)).buffer(0)
    if rp.area < 10: rp = ln.buffer(RAIL_W / 2, cap_style=2)
    rails.append(prism(rp.intersection(deck.buffer(0.01)), Z_DECK, Z_DECK + RAIL_H))
out['CTX_SH249_Rails'] = merge(rails)
out['CTX_SH249_Embankment'] = merge([prism(deck.intersection(north), 0.5, Z_SOFFIT), prism(deck.intersection(south), 0.5, Z_SOFFIT)])

# bents in the three medians that run under the deck: columns only where they land on an island
bents, cols_report = [], []
for name, (cx, cy) in {'N': (3, 57), 'C': (24, 0), 'S': (31, -57)}.items():
    slope = 0.045
    line = LineString([(X0, cy + slope*(X0-cx)), (X1, cy + slope*(X1-cx))]).intersection(deck)
    if line.is_empty: continue
    pts = []
    Lb = line.length; n = int(Lb // 22)
    for k in range(n + 1):
        t = 4 + k * (Lb - 8) / max(n, 1)
        p = line.interpolate(t)
        # nudge across the median to its centreline: search +-6 ft perpendicular for island pixels
        best = None
        for dy in np.arange(-6, 6.01, 0.25):
            if cls(p.x, p.y + dy) == 2:
                ok = all(cls(p.x + 1.4*math.cos(a), p.y + dy + 1.4*math.sin(a)) in (2, 4) for a in np.linspace(0, 2*math.pi, 8, endpoint=False))
                if ok and (best is None or abs(dy) < abs(best)): best = dy
        if best is not None: pts.append((p.x, p.y + best))
    for x, y in pts: bents.append(prism(Point(x, y).buffer(1.5, 12), 0.5, Z_SOFFIT - 3))
    if pts:
        cap = LineString([(line.coords[0][0], line.coords[0][1] + np.mean([y - (cy + slope*(x-cx)) for x, y in pts])),
                          (line.coords[-1][0], line.coords[-1][1] + np.mean([y - (cy + slope*(x-cx)) for x, y in pts]))]).buffer(2.0, cap_style=2).intersection(deck)
        bents.append(prism(cap, Z_SOFFIT - 3, Z_SOFFIT))
    cols_report.append((name, len(pts)))
out['CTX_SH249_Bents'] = merge(bents)
json.dump(out, open('br_mesh.json', 'w'))
print('deck width ft', round(width, 1), 'area', round(deck.area), {k: (len(v['v']), len(v['f'])) for k, v in out.items()}, cols_report)
