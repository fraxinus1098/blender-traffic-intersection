"""Phase 5b: proposed pavement markings (sheets 40/41) -> classified plan-feet geometry (p5b_mk.json)."""
import json, math, numpy as np
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Polygon, LineString, Point
from shapely.strtree import STRtree
R = json.load(open('objs40.json'))
pads = json.load(open('pads.json'))
F = np.load('work/p3_rd_masks.npz')['final']
RES = 0.25; X0, Y1 = -400, 210
d_isl = distance_transform_edt(F != 2) * RES
d_np = distance_transform_edt(F == 1) * RES
A = (-44.8, 93.3); B = (64.6, -94.0)
def side(X, Y): return (B[0]-A[0])*(Y-A[1]) - (B[1]-A[1])*(X-A[0])
def keep(s, P):
    cx = sum(a for a, b in P)/len(P); cy = sum(b for a, b in P)/len(P); sd = side(cx, cy)
    return not ((s == '40' and sd > 0) or (s == '41' and sd < 0))
def rc(X, Y):
    r, c = int((Y1 - Y)/RES), int((X - X0)/RES)
    return (r, c) if 0 <= r < F.shape[0] and 0 <= c < F.shape[1] else None
def on_pave(X, Y, inset=0.4):
    p = rc(X, Y); return p is not None and F[p] == 1 and d_np[p] >= inset
def depth(X, Y):
    p = rc(X, Y); return d_np[p] if p is not None and F[p] == 1 else 0
def near_median(X, Y):
    p = rc(X, Y); return p is not None and d_isl[p] < 3.0
EXCL = [(214, 227, 69, 80)]   # (x0,x1,y0,y1): ramp-outline segment by pad 17 (NE corner, NB int.)
def excluded(X, Y): return any(a <= X <= b and c <= Y <= d for a, b, c, d in EXCL)
padpts = [(p['x'], p['y']) for p in pads]
def near_pad(X, Y, r=4.5): return any(math.hypot(X-a, Y-b) < r for a, b in padpts)
ROADDIR = (5.0, 121.0)
def ang_ok(a, b):
    t = math.degrees(math.atan2(b[1]-a[1], b[0]-a[0])) % 180
    return min(min(abs(t-d), 180-abs(t-d)) for d in ROADDIR)

objs = [(s, o) for s in ('40', '41') for o in R[s] if keep(s, o['pts'])]
arrowheads = []
for s, o in objs:
    P = o['pts']
    if o['fill'] and o['fc'].startswith('(0.0') and len(P) in (3, 4, 5):
        xs = [a for a, b in P]; ys = [b for a, b in P]
        if max(max(xs)-min(xs), max(ys)-min(ys)) < 4.5:
            try: arrowheads.append(Polygon(P).buffer(0.5))
            except Exception: pass
tree = STRtree(arrowheads)
callouts = []
for s_, o in objs:
    P = o['pts']
    if o['fill'] or not o['sc'].startswith('(0.0') or len(P) < 5: continue
    xs = [a for a, b in P]; ys = [b for a, b in P]; w = max(xs)-min(xs); h = max(ys)-min(ys)
    if math.dist(P[0], P[-1]) < 0.3 and 2.4 < max(w, h) < 7 and abs(w-h) < 0.8:
        callouts.append(Polygon(P).exterior.buffer(0.6))
ctree = STRtree(callouts)
def touches_callout(pt):
    return any(callouts[i].contains(Point(pt)) for i in ctree.query(Point(pt)))
def touches_arrow(pt):
    return any(arrowheads[i].contains(Point(pt)) for i in tree.query(Point(pt)))
out = dict(lines=[], hatch=[], dotted=[], fills=[], rpm=[])
st = dict(leader=0, offpave=0, circle=0, line=0, hatch=0, dotted=0, fill=0, fill_small=0, fill_leader=0, rpm=0, pad=0)
for s, o in objs:
    P = [tuple(p) for p in o['pts']]
    if len(P) < 2: continue
    xs = [a for a, b in P]; ys = [b for a, b in P]; ext = max(max(xs)-min(xs), max(ys)-min(ys))
    cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
    if o['fill']:
        if not o['fc'].startswith('(0.0') or len(P) < 3: continue
        if not on_pave(cx, cy, 0.0) or excluded(cx, cy) or near_pad(cx, cy, 3.0): continue
        if ext < 5.0: st['fill_small'] += 1; continue
        G = Polygon(P).buffer(0)
        if G.area / max(ext, 1e-6) < 0.45: st['fill_leader'] += 1; continue
        out['fills'].append(P); st['fill'] += 1; continue
    if not o['sc'].startswith('(0.0') or o['lw'] not in (0.24, 0.72): continue
    if o['t'] == 'rect' and o['dash'] != 'None': continue
    closed = math.dist(P[0], P[-1]) < 0.3 and len(P) > 3
    if closed and ext < 1.6:
        if on_pave(cx, cy, 0.0) and 0.4 < ext: out['rpm'].append((cx, cy, bool(near_median(cx, cy)))); st['rpm'] += 1
        continue
    if closed and 2.4 < ext < 8.5 and abs((max(xs)-min(xs))-(max(ys)-min(ys))) < 1.2: st['circle'] += 1; continue
    if len(P) == 2 and math.dist(P[0], P[1]) > 20 and ang_ok(P[0], P[1]) > 15: st['leader'] += 1; continue
    if len(P) == 2 and abs(P[0][0]-P[1][0]) < 0.3 and abs(P[0][1]-P[1][1]) > 100: continue   # sheet border
    if near_pad(cx, cy, 7.5) and ext < 12: st['pad'] += 1; continue
    if not closed and (touches_arrow(P[0]) or touches_arrow(P[-1]) or touches_callout(P[0]) or touches_callout(P[-1])): st['leader'] += 1; continue
    # curved polyline inside the intersection -> dotted guide line
    if len(P) > 2:
        ch = LineString([P[0], P[-1]]); dev = max(ch.distance(Point(p)) for p in P)
        mid = P[len(P)//2]
        plen = sum(math.dist(a, b) for a, b in zip(P, P[1:]))
        if dev > 1.5 and math.dist(P[0], P[-1]) < 0.5 and plen < 30: st['circle'] += 1; continue
        if dev > 1.5 and depth(*mid) > 12:
            out['dotted'].append(P); st['dotted'] += 1; continue
    segs = []
    for a, b in zip(P, P[1:]):
        mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
        if not on_pave(mx, my) or excluded(mx, my): st['offpave'] += 1; continue
        if math.dist(a, b) > 20 and ang_ok(a, b) > 15: st['leader'] += 1; continue
        segs.append((a, b))
    for a, b in segs:
        L = math.dist(a, b); mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
        col = 'yellow' if near_median(mx, my) else 'white'
        if len(P) == 2 and 3 < L < 40 and ang_ok(a, b) > 15:
            out['hatch'].append((a, b, col)); st['hatch'] += 1
        else:
            out['lines'].append((a, b, col)); st['line'] += 1
json.dump(out, open('p5b_mk.json', 'w'))
print(st)
