"""Phase 6: tree positions + canopy sizes from NAIP 2022 (ExG + darkness), clear of paved surfaces.
Inputs: p6_aerial_scene.npz (scene-frame NAIP at 1 ft/px), p3_rd_masks.npz, p5b_pads.json,
p6_osm_buildings.json. Output: p6_trees.json (plan feet) + p6_trees_overlay.png."""
import json, sys, math, numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, binary_opening, binary_closing, distance_transform_edt, label
from shapely.geometry import Polygon, Point, box
from shapely.prepared import prep
sys.path.insert(0, '.')
from p6_common import *
W = 'work/'
d = np.load('p6_aerial_scene.npz'); R = float(d['res'])
rgb = gaussian_filter(d['rgb'].astype(np.float32), (1.2, 1.2, 0))
exg = 2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]; L = rgb.mean(-1)
EXG_MIN, L_MAX = 14, 127            # canopy = green and darker than mown grass
canopy = (exg > EXG_MIN) & (L < L_MAX)
yy, xx = np.mgrid[0:canopy.shape[0], 0:canopy.shape[1]]
disk = lambda r: (np.hypot(*np.mgrid[-r:r+1, -r:r+1]) <= r)
canopy = binary_opening(canopy, disk(4))           # drop thin wall/pole shadows (< ~8 ft wide)
canopy = binary_closing(canopy, disk(2))
lab, n = label(canopy)
sizes = np.bincount(lab.ravel()); keep = sizes >= 40; keep[0] = False   # >= 40 ft^2 blobs
# drop long thin blobs (cast shadows of poles/walls on grass): minor-axis sd < 4 ft and aspect > 3
from scipy.ndimage import find_objects
for k, sl in enumerate(find_objects(lab), 1):
    if not keep[k]: continue
    py, px_ = np.nonzero(lab[sl] == k)
    if len(py) < 5: continue
    ev = np.sort(np.linalg.eigvalsh(np.cov(np.vstack([px_, py]).astype(float))))
    if ev[0] > 0 and math.sqrt(ev[0]) * R < 4 and math.sqrt(ev[1] / ev[0]) > 3: keep[k] = False
canopy = keep[lab]

GX = CX0 + (xx + .5) * R; GY = CY1 - (yy + .5) * R
F = np.load(W + 'p3_rd_masks.npz')['final']
cls = mask_class(F, GX.ravel(), GY.ravel()).reshape(GX.shape)
hard = np.isin(cls, (1, 4, 5))                      # pavement, curb band, sidewalk
# deck / embankment footprint (Phase 3 deck-edge lines, extended through the margin)
Wl = ((-22.8, -103.6), (-165.7, 143.2)); El = ((41.3, 71.8), (172.2, -154.3))
at_y = lambda l, y: (l[0][0] + (l[1][0] - l[0][0]) * (y - l[0][1]) / (l[1][1] - l[0][1]), y)
deck = Polygon([at_y(Wl, CY0), at_y(Wl, CY1), at_y(El, CY1), at_y(El, CY0)])
bl = [Polygon(b['ring']) for b in json.load(open('p6_osm_buildings.json'))]
pads = json.load(open(W + 'p5b_pads.json'))
block = deck.buffer(8)
for b in bl: block = block.union(b.buffer(4))
for p in pads: block = block.union(Point(p['x'], p['y']).buffer(12))
pb = prep(block)
blocked = np.zeros_like(hard)
# rasterise the blocked polygon on the 1-ft grid
from PIL import ImageDraw as _D
im = Image.new('1', (canopy.shape[1], canopy.shape[0]), 0); dr = _D.Draw(im)
for g in getattr(block, 'geoms', [block]):
    dr.polygon([(x - CX0, CY1 - y) for x, y in g.exterior.coords], fill=1)
    for h in g.interiors: dr.polygon([(x - CX0, CY1 - y) for x, y in h.coords], fill=0)
blocked = np.array(im, bool)
# trunk must be >= 3 ft from any hard surface or blocked area
clear = distance_transform_edt(~(hard | blocked)) * R >= 3.0
ok = canopy & clear

# greedy packing: largest inscribed canopy first, radius 5-16 ft
dt = distance_transform_edt(canopy) * R
avail = ok.copy(); trees = []
rng = np.random.default_rng(6)
RMIN, RMAX = 5.0, 16.0
score = np.where(avail, np.minimum(dt, RMAX), 0)
while True:
    i = np.argmax(score); r0 = score.flat[i]
    if r0 < 4.0: break                               # needs an 8-ft inscribed disk (drops shadow slivers)
    yv, xv = divmod(i, score.shape[1])
    r = float(np.clip(r0 * 1.15 + 1.0, RMIN, RMAX))   # canopy edge overhangs the mask boundary a little
    X, Y = float(GX[yv, xv]), float(GY[yv, xv])
    trees.append(dict(x=round(X, 2), y=round(Y, 2), r=round(r, 2)))
    rr = int(math.ceil(1.6 * r / R))
    y0, y1_, x0, x1_ = max(0, yv - rr), yv + rr + 1, max(0, xv - rr), xv + rr + 1
    sub = (np.hypot(yy[y0:y1_, x0:x1_] - yv, xx[y0:y1_, x0:x1_] - xv) * R) < 1.5 * r
    score[y0:y1_, x0:x1_][sub] = 0
# heights and variants
VAR = [('S', 7.0), ('M', 10.0), ('L', 13.0), ('XL', 16.0)]
for t in trees:
    r = t['r']
    t['h'] = round(float(np.clip(2.1 * r + 8 + rng.normal(0, 2), 16, 45)), 1)
    t['var'] = min(VAR, key=lambda v: abs(v[1] - r))[0]
    t['rot'] = round(float(rng.uniform(0, 360)), 1)
    t['cls'] = int(mask_class(F, np.array([t['x']]), np.array([t['y']]))[0])
json.dump(dict(params=dict(EXG_MIN=EXG_MIN, L_MAX=L_MAX, RMIN=RMIN, RMAX=RMAX, clear_ft=3.0,
          source='NAIP 2022 60 cm, ExG=2G-R-B > 14 and mean RGB < 127, opened 4 ft'), trees=trees),
          open('p6_trees.json', 'w'), indent=0)
ov = Image.fromarray(d['rgb']).convert('RGB'); dr = ImageDraw.Draw(ov)
for t in trees:
    cx, cy = t['x'] - CX0, CY1 - t['y']
    dr.ellipse([cx - t['r'], cy - t['r'], cx + t['r'], cy + t['r']], outline=(255, 0, 255))
    dr.point((cx, cy), fill=(255, 0, 0))
for g in getattr(block, 'geoms', [block]):
    dr.line([(x - CX0, CY1 - y) for x, y in g.exterior.coords], fill=(0, 140, 255))
ov.save('p6_trees_overlay.png')
from collections import Counter
print(len(trees), Counter(t['var'] for t in trees), Counter(t['cls'] for t in trees))
