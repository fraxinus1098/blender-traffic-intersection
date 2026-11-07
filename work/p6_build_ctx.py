"""Phase 6: OSM building massing -> p6_context.json (Blender metres; per-face material index 0 wall, 1 roof).
Fuel canopy (building=roof): 2-ft slab at 15-17 ft on three 1.5-ft square columns along its long axis."""
import json, sys, math, numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Polygon, box
sys.path.insert(0, '.')
from p6_common import *
ZG = -0.10                       # aerial ground plane (m)
def prism(ring, z0, z1, top_mat=1, side_mat=0, bottom=False):
    r = ring[:]
    if not Polygon(r).exterior.is_ccw: r = r[::-1]
    n = len(r); V, F, M = [], [], []
    tri = earcut.triangulate_float64(np.array(r, np.float64), np.array([n], np.uint32)).reshape(-1, 3).tolist()
    V += [(x * FT, y * FT, z1) for x, y in r] + [(x * FT, y * FT, z0) for x, y in r]
    for a, b, c in tri: F.append([a, b, c]); M.append(top_mat)
    if bottom:
        for a, b, c in tri: F.append([c + n, b + n, a + n]); M.append(side_mat)
    for i in range(n):
        j = (i + 1) % n
        F.append([i, i + n, j + n, j]); M.append(side_mat)     # quad wall
    return V, F, M
def merge(parts):
    V, F, M = [], [], []
    for v, f, m in parts:
        o = len(V); V += v; F += [[k + o for k in q] for q in f]; M += m
    return V, F, M
out = {}
for b in json.load(open('p6_osm_buildings.json')):
    ring = Polygon(b['ring']).simplify(0.3).exterior.coords[:-1]
    ring = [tuple(p) for p in ring]
    h = b['height_ft'] * FT
    if b['kind'] == 'canopy':
        poly = Polygon(ring); mrr = poly.minimum_rotated_rectangle
        c = list(mrr.exterior.coords)[:4]
        e1 = np.subtract(c[1], c[0]); e2 = np.subtract(c[2], c[1])
        long_, short = (e1, e2) if np.linalg.norm(e1) > np.linalg.norm(e2) else (e2, e1)
        ctr = np.mean(c, 0); u = long_ / np.linalg.norm(long_); w = short / np.linalg.norm(short)
        parts = [prism(ring, 15 * FT, 17 * FT, bottom=True)]
        for t in (-1 / 3, 0, 1 / 3):
            p = ctr + u * t * np.linalg.norm(long_)
            sq = [tuple(p + s1 * .75 * u + s2 * .75 * w) for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            parts.append(prism(sq, ZG, 15 * FT, top_mat=0))
        V, F, M = merge(parts)
        name = f"CTX_BLDG_Canopy_{(b['name'] or b['osm_id'])}".replace(' ', '_')
    else:
        V, F, M = prism(ring, ZG, h)
        nm = b['name'] or f"{b['kind']}_{b['osm_id']}"
        name = f"CTX_BLDG_{nm}".replace(' ', '_').replace("'", '').replace('&', 'and')
    while name in out: name += '_b'
    t = b['tags']
    note = (f"OSM way {b['osm_id']}" + (f" ({b['name']})" if b['name'] else '') +
            f"; building={t.get('building')}; height {b['height_ft']:.0f} ft, {b['basis']}")
    out[name] = dict(v=[[round(c, 4) for c in p] for p in V], f=F, m=M,
                     props=dict(sh249_status='context', sh249_phase='context',
                                sh249_type='building_canopy' if b['kind'] == 'canopy' else 'building_massing',
                                sh249_note=note, sh249_source=f"OSM way {b['osm_id']}",
                                sh249_osm_id=str(b['osm_id']), sh249_height_ft=round(b['height_ft'], 1)))
json.dump(out, open('p6_context.json', 'w'))
print(len(out), sum(len(o['v']) for o in out.values()), list(out)[:20])
