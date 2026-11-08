"""Phase 9D check: plot the KMZ's draped polygons, equipment points and plan-sheet quads over the NAIP aerial,
and compare the two placements used in the KMZ:
  - draped polygons / points / overlays: scene ft -> UTM (Phase 2 fit) -> WGS84 (pyproj), as written by p9_build_kmz.py
  - COLLADA models: Google Earth puts model metres in a local east-north frame at ORIGIN_SC, rotated by the heading.
usage (venv, repo root): .venv/bin/python work/p9_kmz_check.py <kmz> <out.jpg>"""
import sys, zipfile, re, math
import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer, Geod
sys.path.insert(0, 'work')
from p6_common import scene_ft_to_utm, UL_E, UL_N, PX, FT
KMZ, OUT = sys.argv[1], sys.argv[2]
kml = zipfile.ZipFile(KMZ).read('doc.kml').decode()
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32615', always_xy=True)
LAT0, LON0, HEADING = 30.0130799, -95.5906606, 1.670
img = Image.open('imagery/SH249_SpringCypress_NAIP2022_60cm.tif').convert('RGB')
def px(lon, lat):
    E, N = to_utm.transform(lon, lat); return (E - UL_E) / PX - .5, (UL_N - N) / PX - .5
dr = ImageDraw.Draw(img, 'RGBA')
def coords(s): return [tuple(map(float, c.split(',')[:2])) for c in s.split()]
for pm in re.findall(r'<Placemark>(.*?)</Placemark>', kml, re.S):
    style = re.search(r'#(\S+?)<', pm); style = style.group(1) if style else ''
    for ring in re.findall(r'<outerBoundaryIs><LinearRing><coordinates>(.*?)</coordinates>', pm):
        col = (255, 220, 0, 200) if 'Yellow' in style else (0, 230, 255, 120) if 'RZ' in style else (255, 255, 255, 220)
        dr.polygon([px(*c) for c in coords(ring)], fill=col)
    pt = re.search(r'<Point><coordinates>(.*?)</coordinates>', pm)
    if pt and 'eq_' in style:
        x, y = px(*coords(pt.group(1))[0]); c = {'eq_new': (30, 220, 40), 'eq_remove': (230, 20, 20)}.get(style, (150, 150, 150))
        dr.ellipse([x - 4, y - 4, x + 4, y + 4], outline=c + (255,), width=2)
for q in re.findall(r'<gx:LatLonQuad><coordinates>(.*?)</coordinates>', kml):
    dr.line([px(*c) for c in coords(q)] + [px(*coords(q)[0])], fill=(255, 0, 255, 200), width=2)
# crop to the model extent
E0, N0 = scene_ft_to_utm(-450, 260); E1, N1 = scene_ft_to_utm(620, -290)
box = [int((E0 - UL_E) / PX), int((UL_N - N0) / PX), int((E1 - UL_E) / PX), int((UL_N - N1) / PX)]
im = img.crop(box); im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS); im.save(OUT, quality=88)
# placement agreement: GE local frame (origin + heading, geodesic offsets) vs Phase 2 transform, over the model extent
geod = Geod(ellps='WGS84'); to_ll = Transformer.from_crs('EPSG:32615', 'EPSG:4326', always_xy=True)
h = math.radians(HEADING); d = []
for X in np.linspace(-400, 560, 9):
    for Y in np.linspace(-240, 210, 7):
        x, y = X * FT, Y * FT; e, n = x * math.cos(h) + y * math.sin(h), -x * math.sin(h) + y * math.cos(h)
        lon_g, lat_g, _ = geod.fwd(LON0, LAT0, math.degrees(math.atan2(e, n)), math.hypot(e, n))
        lon_p, lat_p = to_ll.transform(*scene_ft_to_utm(X, Y))
        d.append(geod.inv(lon_g, lat_g, lon_p, lat_p)[2])
print('wrote', OUT, im.size, '| COLLADA (origin+heading) vs draped (Phase 2 transform): max %.3f m, median %.3f m' % (max(d), float(np.median(d))))
