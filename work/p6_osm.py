"""Phase 6: OSM building footprints -> scene plan feet, with heights -> p6_osm_buildings.json
Source: p6_osm_raw.json (Overpass, fetched 2026-11-06). Heights from height / building:levels if tagged,
otherwise assumed by type (see ASSUME)."""
import json, sys, math
import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon, box
sys.path.insert(0, '.')
from p6_common import *
d = json.load(open('p6_osm_raw.json'))
nodes = {e['id']: (e['lon'], e['lat']) for e in d['elements'] if e['type'] == 'node'}
tr = Transformer.from_crs(4326, 32615, always_xy=True)
ctx = box(CX0, CY0, CX1, CY1)

def assume(tags, area_ft2):
    """Return (height_ft, kind, basis). Single-storey commercial defaults."""
    b = tags.get('building', 'yes')
    if b == 'roof':                                   # fuel canopy
        return 17.0, 'canopy', 'assumed: fuel canopy, deck 15-17 ft'
    shop = tags.get('shop'); am = tags.get('amenity')
    if shop in ('department_store', 'supermarket') or area_ft2 > 25000:
        return 26.0, 'big_box', 'assumed: big-box retail 26 ft'
    if am == 'bank':
        return 20.0, 'bank', 'assumed: bank 20 ft'
    if am in ('restaurant', 'fast_food'):
        return 18.0, 'restaurant', 'assumed: restaurant 18 ft'
    if shop == 'convenience':
        return 16.0, 'convenience', 'assumed: convenience store 16 ft'
    if area_ft2 < 600:
        return 10.0, 'outbuilding', 'assumed: small outbuilding 10 ft'
    return 18.0, 'commercial', 'assumed: 1-storey commercial 18 ft'

out = []
for e in d['elements']:
    if e['type'] != 'way' or 'building' not in e.get('tags', {}): continue
    ll = [nodes[n] for n in e['nodes']]
    E, N = tr.transform([p[0] for p in ll], [p[1] for p in ll])
    X, Y = utm_to_scene_ft(np.array(E), np.array(N))
    poly = Polygon(list(zip(X, Y))).buffer(0)
    if not poly.intersects(ctx): continue
    t = e['tags']
    if 'height' in t:
        v = t['height'].strip()
        h = float(v.replace('ft', '').replace("'", '')) if ('ft' in v or "'" in v) else float(v.replace('m', '')) / FT
        kind = 'tagged'; basis = f"OSM height={v}"
    elif 'building:levels' in t:
        h = 4 + 14 * float(t['building:levels']); kind = 'levels'; basis = f"OSM building:levels={t['building:levels']} x 14 ft + 4 ft parapet"
    else:
        h, kind, basis = assume(t, poly.area)
    name = t.get('name') or t.get('brand') or (t.get('addr:housenumber', '') + ' ' + t.get('addr:street', '')).strip() or None
    out.append(dict(osm_id=e['id'], tags=t, name=name, kind=kind, height_ft=h, basis=basis,
                    ring=[list(map(float, p)) for p in poly.exterior.coords[:-1]], area_ft2=poly.area,
                    inside_model=poly.intersects(box(X0, Y0, X1, Y1))))
json.dump(out, open('p6_osm_buildings.json', 'w'), indent=1)
for b in out: print(b['osm_id'], b['name'], b['kind'], b['height_ft'], round(b['area_ft2']), b['inside_model'])
print(len(out))
