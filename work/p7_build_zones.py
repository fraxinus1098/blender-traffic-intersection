"""Phase 7 (container): radar-zone meshes from p7_data.json -> p7_radar_zones.json (Blender metres).
Each zone -> fill mesh (z = Z_FILL) and outline ribbon (EDGE ft wide, inside the zone, z = Z_EDGE).
Run: python3 p7_build_zones.py <p7_data.json> <out.json>"""
import json, sys, numpy as np, mapbox_earcut as earcut
from shapely.geometry import Polygon
FT = 0.3048
Z_FILL, Z_EDGE, EDGE = 0.030, 0.033, 0.6        # m, m, ft (pavement z = 0, markings at 0.010-0.015 m)
D = json.load(open(sys.argv[1]))

def tri(poly):
    """earcut a shapely Polygon (with holes) -> verts (n,2) ft, faces (m,3)."""
    rings = [np.array(poly.exterior.coords)[:-1]] + [np.array(h.coords)[:-1] for h in poly.interiors]
    V = np.vstack(rings); ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    f = earcut.triangulate_float64(V, ends).reshape(-1, 3)
    return V, f

def mesh(polys, z):
    vs, fs, off = [], [], 0
    for p in polys:
        if p.is_empty or p.area < 0.05: continue
        for g in (p.geoms if hasattr(p, 'geoms') else [p]):
            if g.geom_type != 'Polygon' or g.area < 0.05: continue
            g = g.simplify(0.05)
            V, f = tri(g)
            # earcut keeps ring order; make faces point up
            for t in f:
                a, b, c = V[t]
                if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) < 0: t = t[[0, 2, 1]]
                fs.append((t + off).tolist())
            vs += [[x * FT, y * FT, z] for x, y in V]; off += len(V)
    return dict(v=[[round(c, 5) for c in v] for v in vs], f=fs)

out = []
for z in D['zones']:
    polys = [Polygon(p, h) for p, h in zip(z['polys'], z['holes'])]
    fill = mesh(polys, Z_FILL)
    ring = [p.difference(p.buffer(-EDGE, join_style=2)) for p in polys]
    edge = mesh(ring, Z_EDGE)
    out.append(dict(id=z['id'], kind=z['kind'], fill=fill, edge=edge, label_xy_m=[c * FT for c in z['label_xy']],
                    label_rot_deg=z['label_rot_deg'], meta={k: z[k] for k in ('approach', 'inter', 'dir', 'aim_deg', 'area_ft2',
                    'fov_cover', 'range_ft', 'outside_extent_frac', 'desc', 'radar_xy')}))
    print(z['id'], len(fill['f']), len(edge['f']))
json.dump(out, open(sys.argv[2], 'w'))
