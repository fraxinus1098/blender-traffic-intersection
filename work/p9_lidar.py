"""Phase 9A.1: heights from the USGS 3DEP lidar TX_Houston_B24 (2024 flight, published 2026-01-29).

Run from the repo root with the venv:  .venv/bin/python work/p9_lidar.py
Inputs:  lidar/USGS_LPC_TX_Houston_B24_15RTP*.laz (4 tiles, gitignored), work/p6_osm_buildings.json,
         work/p3_rd_masks.npz, imagery/SH249_SpringCypress_NAIP2022_60cm.tif
Outputs: work/p9_lidar.json (buildings, trees, bridge profiles, alignment and as-built checks),
         docs/images/p9_lidar_check.jpg, lidar/p9_crop.npz (cache of the cropped points; delete to re-read).

Frames: the tiles are UTM 15N metres (NAD83(2011), NAVD88 heights); they are converted to scene feet with
the p6_common helpers (the scene frame was fitted to NAIP in "UTM 15N", so no datum shift is applied; the
alignment check below measures the residual). Heights are normalised: height = surface - ground (class 2)."""
import json, math, os, sys, glob
import numpy as np
from scipy import ndimage as ndi
from matplotlib.path import Path
from shapely.geometry import Polygon, Point, LineString, box
from shapely.prepared import prep
sys.path.insert(0, 'work')
from p6_common import *          # FT, utm_to_scene_ft, scene_ft_to_aerial_px, mask_class, X0.. CY1

TILES = sorted(glob.glob(os.environ.get('P9_TILES', 'lidar/USGS_LPC_TX_Houston_B24_15RTP*.laz')))
CACHE = os.environ.get('P9_CACHE', 'lidar/p9_crop.npz')
TEST = 'P9_TILES' in os.environ           # debug run on partial data: tolerate truncated tiles
PAD_FT = 60 / FT                                  # model extent + 60 m
EX0, EX1, EY0, EY1 = X0 - PAD_FT, X1 + PAD_FT, Y0 - PAD_FT, Y1 + PAD_FT
CELL = 0.5 / FT                                   # 0.5 m grid, in feet
OUT = {}

# ---------------------------------------------------------------- 1. read + crop (cached)
def read_tiles():
    import laspy
    from pyproj import CRS
    cx, cy = np.meshgrid([EX0, EX1], [EY0, EY1])
    e, n = scene_ft_to_utm(cx.ravel(), cy.ravel())
    eb0, eb1, nb0, nb1 = e.min() - 5, e.max() + 5, n.min() - 5, n.max() + 5
    parts, crs = [], []
    for f in TILES:
        with laspy.open(f) as r:
            c = r.header.parse_crs()
            crs.append(c.to_string() if c else None)
            it = r.chunk_iterator(2_000_000)
            while True:
                try: pts = next(it)
                except StopIteration: break
                except Exception:
                    if TEST: break
                    raise
                x, y = pts.x, pts.y
                k = (x >= eb0) & (x <= eb1) & (y >= nb0) & (y <= nb1)
                if not k.any(): continue
                parts.append(np.stack([np.asarray(x[k]), np.asarray(y[k]), np.asarray(pts.z[k]),
                                       np.asarray(pts.classification[k]), np.asarray(pts.return_number[k]),
                                       np.asarray(pts.number_of_returns[k]), np.asarray(pts.intensity[k])], 1))
    P = np.concatenate(parts)
    X, Y = utm_to_scene_ft(P[:, 0], P[:, 1])
    keep = (X >= EX0) & (X <= EX1) & (Y >= EY0) & (Y <= EY1)
    np.savez_compressed(CACHE, X=X[keep].astype(np.float32), Y=Y[keep].astype(np.float32),
                        Z=(P[keep, 2] / FT).astype(np.float32), C=P[keep, 3].astype(np.uint8),
                        RN=P[keep, 4].astype(np.uint8), NR=P[keep, 5].astype(np.uint8),
                        I=P[keep, 6].astype(np.uint16), crs=np.array(json.dumps(crs)))

if not os.path.exists(CACHE):
    assert TEST or len(TILES) == 4, TILES
    read_tiles()
d = np.load(CACHE)
X, Y, Z, C, RN, NR = d['X'].astype(np.float64), d['Y'].astype(np.float64), d['Z'].astype(np.float64), d['C'], d['RN'], d['NR']
crs = json.loads(str(d['crs']))
ok = ~np.isin(C, (7, 18))                        # drop low / high noise
X, Y, Z, C, RN, NR = X[ok], Y[ok], Z[ok], C[ok], RN[ok], NR[ok]
# Empirical horizontal shift lidar -> scene (ft). pyproj has no usable NAD83(2011) -> WGS84 step here (returns
# ~0), but the lidar sat ~1.4 m east of the plan frame. Measured with SHIFT = 0 (first run, 2026-11-07):
# deck edges +4.0 ft across the SH 249 axis (west -3.6, east +4.4 outward = both 3.6-4.4 ft east), existing poles
# C/E/K (+4.61,+0.54) (+4.62,+1.68) (+4.72,-1.34) ft -> combined (4.6, 0.3) ft. The alignment section reports the
# residual after the shift.
SHIFT = globals().get('SHIFT', (4.6, 0.3))
X, Y = X - SHIFT[0], Y - SHIFT[1]
cls_count = {int(k): int(v) for k, v in zip(*np.unique(C, return_counts=True))}
area_m2 = (EX1 - EX0) * (EY1 - EY0) * FT * FT
OUT['source'] = dict(dataset='USGS 3DEP Lidar Point Cloud TX_Houston_B24 (TX_Houston_1_B24), published 2026-01-29',
                     tiles=[os.path.basename(t) for t in TILES], crs_from_header=crs,
                     crop_scene_ft=[EX0, EX1, EY0, EY1], points=int(len(X)),
                     density_pts_m2=round(len(X) / area_m2, 1), classes=cls_count,
                     units='feet; x/y scene plan feet (ORIGIN_SC), heights relative to local class-2 ground unless stated')
print('points', len(X), 'density/m2', OUT['source']['density_pts_m2'], 'classes', cls_count, 'crs', crs)

# ---------------------------------------------------------------- 2. grids (0.5 m)
NXg = int(math.ceil((EX1 - EX0) / CELL)); NYg = int(math.ceil((EY1 - EY0) / CELL))
ci = np.clip(((X - EX0) / CELL).astype(int), 0, NXg - 1)
ri = np.clip(((EY1 - Y) / CELL).astype(int), 0, NYg - 1)
lin = ri * NXg + ci
gnd = C == 2
# ground: mean of class-2 per cell, holes filled from the nearest ground cell, lightly smoothed
s = np.bincount(lin[gnd], Z[gnd], NXg * NYg); n = np.bincount(lin[gnd], None, NXg * NYg)
G = np.full(NXg * NYg, np.nan); G[n > 0] = s[n > 0] / n[n > 0]; G = G.reshape(NYg, NXg)
miss = np.isnan(G)
idx = ndi.distance_transform_edt(miss, return_distances=False, return_indices=True)
G = G[idx[0], idx[1]]
G = ndi.gaussian_filter(G, 1.0)
# highest surface per cell (all classes but noise)
D = np.full(NXg * NYg, -np.inf); np.maximum.at(D, lin, Z); D = D.reshape(NYg, NXg)
D = np.where(np.isfinite(D), D, G)
H = np.maximum(D - G, 0)                           # normalised height (ft)
Hp = Z - G[ri, ci]                                 # per-point normalised height
gx = EX0 + (np.arange(NXg) + .5) * CELL; gy = EY1 - (np.arange(NYg) + .5) * CELL
GX, GY = np.meshgrid(gx, gy)
# multi-return fraction per cell (vegetation lets the pulse through; roofs, vehicles and poles mostly don't)
up = Hp > 6.0
nm = np.bincount(lin[up & (NR > 1)], None, NXg * NYg); nu = np.bincount(lin[up], None, NXg * NYg)
MR = np.where(nu > 0, nm / np.maximum(nu, 1), 0).reshape(NYg, NXg)

def poly_mask(poly):
    """cells whose centre is inside a shapely polygon"""
    m = np.zeros(GX.shape, bool)
    for g in getattr(poly, 'geoms', [poly]):
        if g.is_empty: continue
        x0_, y0_, x1_, y1_ = g.bounds
        c0, c1 = max(0, int((x0_ - EX0) / CELL)), min(NXg, int((x1_ - EX0) / CELL) + 2)
        r0, r1 = max(0, int((EY1 - y1_) / CELL)), min(NYg, int((EY1 - y0_) / CELL) + 2)
        if c0 >= c1 or r0 >= r1: continue
        pts = np.stack([GX[r0:r1, c0:c1].ravel(), GY[r0:r1, c0:c1].ravel()], 1)
        inside = Path(np.array(g.exterior.coords)).contains_points(pts)
        for h in g.interiors: inside &= ~Path(np.array(h.coords)).contains_points(pts)
        m[r0:r1, c0:c1] |= inside.reshape(r1 - r0, c1 - c0)
    return m

def pts_in(poly):
    x0_, y0_, x1_, y1_ = poly.bounds
    k = np.nonzero((X >= x0_) & (X <= x1_) & (Y >= y0_) & (Y <= y1_))[0]
    if len(k) == 0: return k
    inside = np.zeros(len(k), bool)
    for g in getattr(poly, 'geoms', [poly]):
        inside |= Path(np.array(g.exterior.coords)).contains_points(np.stack([X[k], Y[k]], 1))
    return k[inside]

# ---------------------------------------------------------------- bridge geometry (Phase 3 deck-edge lines)
Wl = ((-22.8, -103.6), (-165.7, 143.2)); El = ((41.3, 71.8), (172.2, -154.3))
at_y = lambda l, y: (l[0][0] + (l[1][0] - l[0][0]) * (y - l[0][1]) / (l[1][1] - l[0][1]), y)
deck_full = Polygon([at_y(Wl, EY0), at_y(Wl, EY1), at_y(El, EY1), at_y(El, EY0)])
L = math.dist(*Wl); AX = np.array([(Wl[1][0] - Wl[0][0]) / L, (Wl[1][1] - Wl[0][1]) / L])  # axis unit, northward
NRM = np.array([AX[1], -AX[0]])                                                       # eastward normal
# centre line point on Y = 0
cW, cE = np.array(at_y(Wl, 0)), np.array(at_y(El, 0)); C0 = (cW + cE) / 2
deck_w = float(abs((cE - cW) @ NRM))

# ---------------------------------------------------------------- 3a. alignment check
# (i) deck edges: across-axis position of the big height step at the deck edges vs the plan lines
def across(xv, yv): return (np.asarray(xv) - C0[0]) * NRM[0] + (np.asarray(yv) - C0[1]) * NRM[1]
def along(xv, yv): return (np.asarray(xv) - C0[0]) * AX[0] + (np.asarray(yv) - C0[1]) * AX[1]
SA, SN = along(GX, GY), across(GX, GY)
edge_res = {}
for side, sgn in (('west', -1), ('east', 1)):
    offs = []
    for s0 in np.arange(-60, 61, 10):                 # across Spring Cypress, where the deck spans open road
        band = (np.abs(SA - s0) < 2.5)
        prof_n = np.arange(sgn * deck_w / 2 - 30, sgn * deck_w / 2 + 30, CELL / 2)
        hh = np.array([np.nanmedian(np.where(band & (np.abs(SN - q) < CELL), H, np.nan)) if (band & (np.abs(SN - q) < CELL)).any() else np.nan for q in prof_n])
        inside = hh > 12                              # deck top is > 12 ft above the road under it
        if inside.sum() < 5 or (~inside).sum() < 5: continue
        # outermost inside cell toward the edge
        k = np.nonzero(inside)[0]
        e = prof_n[k.max()] if sgn > 0 else prof_n[k.min()]
        offs.append(float(e - sgn * deck_w / 2) * sgn)   # + = lidar edge outside the plan line
    edge_res[side] = dict(n=len(offs), median_ft=round(float(np.median(offs)), 2) if offs else None,
                          values=[round(o, 1) for o in offs])
# (ii) existing poles: centroid of tall, thin returns near the plan pole position
EX_POLES = {'C': (-210.9, -10.3), 'E': (-99.5, -67.0), 'H': (252.4, 7.2), 'K': (145.1, 65.6),
            'M1': (203.1, 98.6), 'M2': (243.5, 75.8)}
PR_POLES = {'A': (-248.3, 41.5), 'B': (-166.0, -91.0), 'C': (-86.4, -62.6), 'K': (286.1, -43.7),
            'L': (206.8, 87.2), 'M': (131.0, 62.5)}
def pole_probe(x, y, r=6.0, zmin=8.0, zmax=26.0):
    # airborne lidar hardly hits a 1-ft shaft (< 3 returns below 17 ft); the cluster is mostly arm/luminaire returns
    k = np.nonzero((np.hypot(X - x, Y - y) < r) & (Hp > zmin) & (Hp < zmax))[0]
    if len(k) < 3: return dict(n=int(len(k)))
    # the pole is the densest vertical column: take the 1.5-ft cluster with most points
    best = None
    for j in k:
        m = np.hypot(X[k] - X[j], Y[k] - Y[j]) < 1.5
        if best is None or m.sum() > best[0]: best = (int(m.sum()), k[m])
    kk = best[1]
    return dict(n=int(len(k)), n_col=best[0], x=round(float(X[kk].mean()), 2), y=round(float(Y[kk].mean()), 2),
                dx=round(float(X[kk].mean() - x), 2), dy=round(float(Y[kk].mean() - y), 2),
                top_ft=round(float(Hp[kk].max()), 1))
ex_probe = {k: pole_probe(*v) for k, v in EX_POLES.items()}
sh = [(p['dx'], p['dy']) for k, p in ex_probe.items() if p.get('n_col', 0) >= 8 and not k.startswith('M')]
OUT['alignment'] = dict(
    shift_applied_ft=list(SHIFT),
    pre_shift_measured=dict(deck_edges_ft=dict(west=-3.63, east=4.45),
                            poles_ft=dict(C=[4.61, 0.54], E=[4.62, 1.68], H=[-2.63, -1.66], K=[4.72, -1.34])),
    note='Lidar placed with the scene <-> UTM helpers, then shifted by -shift_applied_ft (NAD83(2011) vs the NAIP/WGS84 '
         'scene frame); values below are residuals after the shift. Positive deck-edge offset = lidar edge '
         'outside the plan deck-edge line. Pole offsets = centroid of tall returns minus the plan pole centre (coarse, +-4 ft: the clusters are mostly arm/luminaire returns; the deck edges are the main evidence).',
    deck_edges=edge_res, existing_poles=ex_probe,
    mean_pole_offset_ft=[round(float(np.mean([a for a, b in sh])), 2), round(float(np.mean([b for a, b in sh])), 2)] if sh else None)
print('alignment', json.dumps(OUT['alignment'])[:900])

# ---------------------------------------------------------------- 3b. pavement level (site-flat check) and bridge
F = np.load('work/p3_rd_masks.npz')['final']
pc = mask_class(F, X, Y)
pav = gnd & (pc == 1)
under = np.abs(across(X, Y)) < deck_w / 2
# Spring Cypress pavement under / next to the bridge: the z = 0 reference for the deck
ref_k = pav & (np.abs(along(X, Y)) < 60) & (np.abs(across(X, Y)) < deck_w / 2 + 60)
Z_REF = float(np.median(Z[ref_k]))
OUT['pavement'] = dict(z_ref_navd88_ft=round(Z_REF, 2), z_ref_n=int(ref_k.sum()),
                       note='median class-2 ground on modelled pavement within 60 ft of the bridge on Spring Cypress',
                       spread_ft=dict(p5=round(float(np.percentile(Z[pav] - Z_REF, 5)), 2),
                                      p50=round(float(np.percentile(Z[pav] - Z_REF, 50)), 2),
                                      p95=round(float(np.percentile(Z[pav] - Z_REF, 95)), 2)))
# per-region pavement level (to judge the flat-site assumption)
reg = {}
for nm_, (xa, xb) in {'SB_int': (-260, -60), 'NB_int': (110, 310), 'under_bridge': (-60, 110)}.items():
    k = pav & (X > xa) & (X < xb) & (np.abs(Y) < 80)
    if k.any(): reg[nm_] = round(float(np.median(Z[k]) - Z_REF), 2)
OUT['pavement']['median_by_area_ft'] = reg

# deck top profile along the axis: points in the deck footprint, 6 ft in from each edge
SAp, SNp = along(X, Y), across(X, Y)
inner = np.abs(SNp) < deck_w / 2 - 6
prof = []
for s0 in np.arange(-500, 501, 10):
    k = np.nonzero(inner & (np.abs(SAp - s0) < 5))[0]
    if len(k) < 30: continue
    zz = Z[k] - Z_REF
    # road surface = densest 0.5-ft elevation bin, preferring the upper layer (deck over Spring Cypress)
    hb = np.arange(zz.min() - .25, zz.max() + .75, 0.5)
    cnt, _ = np.histogram(zz, hb)
    peaks = np.nonzero(cnt >= 0.35 * cnt.max())[0]
    j = peaks.max()
    top = float(np.median(zz[(zz >= hb[j] - 0.5) & (zz < hb[j + 1] + 0.5)]))
    g2 = C[k] == 2
    n17 = int((C[k] == 17).sum())
    # ground under / beside the deck: class-2 returns well below the top (header-bank slope, Spring Cypress)
    gl = zz[g2 & (zz < top - 3)]
    prof.append(dict(s=float(s0), top=round(top, 2), ground_under=round(float(np.median(gl)), 2) if len(gl) >= 5 else None,
                     n=int(len(k)), n_class17=n17))
OUT_prof = prof
# bridge (class 17 = bridge deck) extent along the axis
k17 = (C == 17) & inner
span = [float(np.percentile(SAp[k17], 0.5)), float(np.percentile(SAp[k17], 99.5))]
# side slopes / walls: cross-sections of the top surface across the mainline, at a few stations
xs_ = {}
for s0 in (-400, -300, -200, -150, 150, 200, 300, 400):
    row = []
    for q in np.arange(-deck_w / 2 - 80, deck_w / 2 + 81, 4):
        k = np.nonzero((np.abs(SAp - s0) < 4) & (np.abs(SNp - q) < 2))[0]
        if len(k) < 4: continue
        zz = Z[k] - Z_REF
        row.append([round(float(q), 1), round(float(np.percentile(zz, 20)), 2)])
    xs_[str(s0)] = row
# header bank: ground (lowest returns) under the deck ends, from the open span to the abutment
OUT['bridge'] = dict(
    axis_unit=[round(float(a), 5) for a in AX], normal_unit=[round(float(a), 5) for a in NRM],
    centre_on_Y0=[round(float(a), 2) for a in C0], deck_width_ft=round(deck_w, 1),
    note='s = distance along the SH 249 axis (north positive) from the deck centre line at Y = 0; heights '
         'relative to the Spring Cypress pavement reference. top = mainlane surface (densest upper layer), '
         'ground_under = median class-2 return more than 3 ft below the top (header banks / road under the deck), '
         'span_s_ft = 0.5-99.5 percentile of class-17 (bridge deck) returns along the axis. Cross-sections: '
         '[offset across the axis (east +), 20th-percentile surface].',
    profile=prof,
    span_s_ft=[round(span[0], 1), round(span[1], 1)],
    deck_top_over_spring_cypress_ft=round(float(np.median([p['top'] for p in prof if abs(p['s']) <= 30])), 2),
    cross_sections=xs_)
print('deck top over SC', OUT['bridge']['deck_top_over_spring_cypress_ft'], 'span', OUT['bridge']['span_s_ft'], 'ref', Z_REF)

# ---------------------------------------------------------------- 3c. buildings
B = json.load(open('work/p6_osm_buildings.json'))
bld_out, bmask = [], np.zeros(GX.shape, bool)
for b in B:
    poly = Polygon(b['ring']).buffer(0)
    bmask |= poly_mask(poly.buffer(1.5 / FT))
    shr = poly.buffer(-1 / FT)
    if shr.is_empty: shr = poly
    k = pts_in(shr)
    hk = Hp[k]
    roof = hk[hk > 2 / FT]
    rec = dict(osm_id=b['osm_id'], name=b['name'], kind=b['kind'], assumed_ft=b['height_ft'],
               n_pts=int(len(k)), n_roof=int(len(roof)),
               roof_frac=round(float(len(roof) / max(len(k), 1)), 3))
    if len(roof) >= 20 and rec['roof_frac'] > 0.3:
        rec.update(height_ft=round(float(np.median(roof)), 1), p90_ft=round(float(np.percentile(roof, 90)), 1),
                   p10_ft=round(float(np.percentile(roof, 10)), 1), flag=None)
    else:
        rec.update(height_ft=None, flag='no roof returns (building not there in 2024, or footprint off)')
    bld_out.append(rec)
OUT['buildings'] = bld_out
for r in bld_out: print('bldg', r['osm_id'], r['name'], r['kind'], r['assumed_ft'], '->', r['height_ft'], r['p90_ft'] if r['height_ft'] else r['flag'], r['roof_frac'])

# ---------------------------------------------------------------- 3d. trees
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
deck_blk = poly_mask(deck_full.buffer(10))
# raw canopy height: drop thin structures (poles, mast arms, wires, signs) by a grey opening with a 1.5-m disc
disk = lambda r: np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
Ho = ndi.grey_opening(H, footprint=disk(3))
CHM = ndi.gaussian_filter(Ho, 1.0)
veg_cand = (CHM > 3 / FT) & ~bmask & ~deck_blk
# min spacing ~4 m between tops: min_distance 4 cells (0.5 m) each way
peaks = peak_local_max(np.where(veg_cand, CHM, 0), min_distance=4, threshold_abs=4 / FT, exclude_border=False)
markers = np.zeros(CHM.shape, np.int32)
for i, (r, c) in enumerate(peaks, 1): markers[r, c] = i
lab = watershed(-CHM, markers, mask=veg_cand)
trees, drops = [], dict(pavement=0, small=0, not_veg=0, nudged=0)
mrf = ndi.mean(MR, lab, index=np.arange(1, len(peaks) + 1))
for i, (r, c) in enumerate(peaks, 1):
    htop = float(Ho[max(0, r - 2):r + 3, max(0, c - 2):c + 3].max())
    rr0, rr1, cc0, cc1 = max(0, r - 40), r + 41, max(0, c - 40), c + 41
    sub = (lab[rr0:rr1, cc0:cc1] == i) & (CHM[rr0:rr1, cc0:cc1] >= 0.5 * CHM[r, c])
    area = sub.sum() * CELL * CELL
    rad = math.sqrt(area / math.pi)
    if rad < 4.0: drops['small'] += 1; continue
    if mrf[i - 1] < 0.15: drops['not_veg'] += 1; continue      # solid object (vehicle, structure), not foliage
    x, y = float(GX[r, c]), float(GY[r, c])
    cl = int(mask_class(F, np.array([x]), np.array([y]))[0])
    if cl in (1, 4, 5):
        # crown top over the road: move the trunk back off the hard surface (up to 6 ft), else drop
        best = None
        for dd in np.arange(1, 6.01, 0.5):
            for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
                xx_, yy_ = x + dd * math.cos(a), y + dd * math.sin(a)
                if int(mask_class(F, np.array([xx_]), np.array([yy_]))[0]) in (2, 3):
                    best = (xx_, yy_); break
            if best: break
        if best is None: drops['pavement'] += 1; continue
        x, y = best; drops['nudged'] += 1; cl = int(mask_class(F, np.array([x]), np.array([y]))[0])
    trees.append(dict(x=round(x, 2), y=round(y, 2), r=round(rad, 2), h=round(htop, 1), mr=round(float(mrf[i - 1]), 2), cls=cl))
VAR = [('S', 7.0), ('M', 10.0), ('L', 13.0), ('XL', 16.0)]
rng = np.random.default_rng(9)
for t in trees:
    t['var'] = min(VAR, key=lambda v: abs(v[1] - t['r']))[0]
    t['rot'] = round(float(rng.uniform(0, 360)), 1)
OUT['trees'] = dict(
    method='CHM = highest return - class-2 ground on a 0.5 m grid, grey-opened with a 1.5 m disc (removes poles, '
           'arms, wires), Gaussian sigma 0.5 m; tops = local maxima > 4 m, >= 2 m apart (min_distance 4 cells); '
           'crowns = watershed of the CHM, restricted to >= 50 % of the top height; radius = sqrt(area/pi); '
           'height = max opened CHM within 1 m of the top. Kept if crown radius >= 4 ft and >= 15 % of the returns '
           'above 6 ft in the crown are from multi-return pulses (foliage). Excluded: building footprints + 1.5 m, '
           'deck footprint + 10 ft. Tops over pavement/curb/sidewalk moved up to 6 ft onto roadside/island, else dropped.',
    n=len(trees), dropped=drops, trees=trees)
print('trees', len(trees), drops, 'h range', min(t['h'] for t in trees), max(t['h'] for t in trees),
      'r range', min(t['r'] for t in trees), max(t['r'] for t in trees))

# ---------------------------------------------------------------- 3e. as-built check at proposed poles
OUT['as_built_check'] = dict(
    note='Returns 8-26 ft above ground (pole, arm root, luminaire) within 6 ft of each pole centre. The flight is 2024, so the '
         'proposed poles are not expected. Existing poles are the control.',
    proposed={k: pole_probe(*v) for k, v in PR_POLES.items()}, existing=ex_probe)
print('as-built', {k: (v['n'], v.get('n_col')) for k, v in OUT['as_built_check']['proposed'].items()})

json.dump(OUT, open('work/p9_lidar.json', 'w'), indent=1)
# grids for the 9A.2 bridge rebuild (gitignored): ground and highest surface, ft above the pavement reference
np.savez_compressed('lidar/p9_grids.npz', G=(G - Z_REF).astype(np.float32), D=(D - Z_REF).astype(np.float32),
                    x0=EX0, y1=EY1, cell_ft=CELL)

# ---------------------------------------------------------------- 4. check plot over the NAIP
from PIL import Image, ImageDraw, ImageFont
img = np.array(Image.open('imagery/SH249_SpringCypress_NAIP2022_60cm.tif').convert('RGB')).astype(np.float32)
RS = 1.0
xs = np.arange(EX0, EX1, RS) + RS / 2; ys = np.arange(EY1, EY0, -RS) - RS / 2
AX_, AY_ = np.meshgrid(xs, ys)
row, col = scene_ft_to_aerial_px(AX_, AY_)
rgb = np.stack([ndi.map_coordinates(img[..., k], [row, col], order=1) for k in range(3)], -1)
rgb = (rgb * 0.75).astype(np.uint8)
S = 2
ov = Image.fromarray(rgb).resize((rgb.shape[1] * S, rgb.shape[0] * S)); dr = ImageDraw.Draw(ov)
P_ = lambda x, y: ((x - EX0) * S, (EY1 - y) * S)
try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22); fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
except OSError: font = fs = ImageFont.load_default()
# model extent
dr.rectangle([*P_(X0, Y1), *P_(X1, Y0)], outline=(255, 255, 255), width=2)
for g in [deck_full]:
    dr.line([P_(*p) for p in g.exterior.coords], fill=(0, 200, 255), width=3)
import matplotlib.cm as cm
for t in trees:
    col_ = tuple(int(255 * v) for v in cm.viridis(np.clip((t['h'] - 15) / 50, 0, 1))[:3])
    cx, cy = P_(t['x'], t['y']); rr = t['r'] * S
    dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col_, width=2)
    dr.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(255, 40, 40))
for b, rec in zip(B, bld_out):
    pts = [P_(*p) for p in b['ring']] + [P_(*b['ring'][0])]
    dr.line(pts, fill=(255, 160, 0), width=3)
    cx, cy = np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts])
    txt = f"{rec['height_ft']:.0f}'" if rec['height_ft'] else 'n/a'
    txt += f" ({rec['assumed_ft']:.0f})"
    dr.text((cx - 40, cy - 12), txt, fill=(255, 255, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0))
dr.text((20, 20), 'p9 lidar check: USGS 3DEP TX_Houston_B24 over NAIP 2022. Orange: OSM footprints, lidar roof height '
        '(old assumed). Circles: lidar trees (crown radius, colour = height 15-65 ft). Cyan: deck edges. White: model extent.',
        fill=(255, 255, 255), font=fs, stroke_width=2, stroke_fill=(0, 0, 0))
os.makedirs('docs/images', exist_ok=True)
ov.convert('RGB').save('docs/images/p9_lidar_check.jpg', quality=85)
print('done', ov.size)
