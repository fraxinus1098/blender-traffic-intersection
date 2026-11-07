"""Phase 7 (Blender): signal-head visibility check for every approach, PROPOSED view (E_Signals, E_Markings excluded).
For each approach (work/p7_data.json) and each lane: eye 3.5 ft, 8 ft behind the stop bar; 3x3 rays to each head
(20-80% of its face) -> visible fraction and blocking objects. Profile along each lane from the stop bar back to the
MUTCD Table 4D-2 distance (45 mph 460 ft, 50 mph 540 ft) every 20 ft: number of heads >= 50% visible.
Also: 20-deg cone from 10 ft behind the stop line at the approach centre (MUTCD 4D.13), longitudinal distance of
each head past the stop line (40-180 ft, 4D.14), and whether each head is in frame of the approach camera.
Writes work/p7_visibility.json; restores collection excludes."""
import bpy, json, math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
FT = 0.3048
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
W = SH249_ROOT + r'work/'
D = json.load(open(W + 'p7_data.json'))
REQ = {45: 460, 50: 540}
sc = bpy.context.scene; vl = bpy.context.view_layer
def find_lc(lc, n):
    if lc.collection.name == n: return lc
    for c in lc.children:
        r = find_lc(c, n)
        if r: return r
HIDE = ['E_Signals', 'E_Markings']
prev = {n: find_lc(vl.layer_collection, n).exclude for n in HIDE}
def unit(a): return Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
out = {}
try:
    for n in HIDE: find_lc(vl.layer_collection, n).exclude = True
    vl.update(); dg = bpy.context.evaluated_depsgraph_get()
    def owner(ob): return ob.parent.name if ob.parent else ob.name
    def head_vis(eye, head):
        mw = head.matrix_world; vs = [mw @ v.co for v in head.data.vertices]
        c = sum(vs, Vector()) / len(vs); fwd = (c - eye).normalized()
        r = fwd.cross(Vector((0, 0, 1))).normalized(); u = r.cross(fwd).normalized()
        pr = [(v - c).dot(r) for v in vs]; pu = [(v - c).dot(u) for v in vs]; pf = [(v - c).dot(fwd) for v in vs]
        front = min(pf)
        ok, blk = 0, {}
        for a in (.2, .5, .8):
            for b in (.2, .5, .8):
                t = c + r * (min(pr) + a * (max(pr) - min(pr))) + u * (min(pu) + b * (max(pu) - min(pu))) + fwd * (front * .5)
                d = t - eye; dist = d.length
                hit, loc, nrm, idx, ob, mx = sc.ray_cast(dg, eye, d.normalized(), distance=dist + 0.5)
                if (not hit) or ob.name == head.name or (loc - eye).length >= dist - 0.02: ok += 1
                else: blk[ob.name] = blk.get(ob.name, 0) + 1
        return ok / 9, blk, c
    for a in D['approaches']:
        trav = unit(a['travel_deg']); up = -trav
        heads = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n.startswith('P_HEAD_') and n.split('_')[2] in a['heads']]
        req = REQ[a['speed_mph']]
        e1, e2 = Vector(a['bar_ends'][0] + [0]) * FT, Vector(a['bar_ends'][1] + [0]) * FT
        barmid = (e1 + e2) / 2
        cone_pt = barmid + up * (10 * FT) + Vector((0, 0, 3.5 * FT))
        hinfo = {}
        for h in heads:
            c = sum((h.matrix_world @ v.co for v in h.data.vertices), Vector()) / len(h.data.vertices)
            dv = c - cone_pt; ang = math.degrees(math.atan2(trav.cross(Vector((dv.x, dv.y, 0))).z, trav.dot(Vector((dv.x, dv.y, 0)))))
            hinfo[h.name] = dict(cone_angle_deg=round(ang, 1), past_stop_line_ft=round((c - barmid).dot(trav) / FT, 1))
        cam = bpy.data.objects['CAM_P7_Drv_%sint_%s' % (a['inter'], a['dir'])]
        lanes = []
        for li, ln in enumerate(a['lanes']):
            edge = Vector(ln['bar_edge'] + [0]) * FT
            prof = []
            for s in range(8, req + 1, 20):
                eye = edge + up * (s * FT) + Vector((0, 0, 3.5 * FT))
                res = {h.name: head_vis(eye, h)[:2] for h in heads}
                nv = sum(1 for v in res.values() if v[0] >= .5)
                blk = sorted({b for v in res.values() if v[0] < .5 for b in v[1]})
                prof.append([s, nv, blk])
            eye = edge + up * (8 * FT) + Vector((0, 0, 3.5 * FT))
            at_bar = {}
            for h in heads:
                f, blk, c = head_vis(eye, h)
                dv = c - eye; hz = math.hypot(dv.x, dv.y)
                at_bar[h.name] = dict(vis=round(f, 2), blocked_by=blk, elev_deg=round(math.degrees(math.atan2(dv.z, hz)), 1),
                                      horiz_deg=round(math.degrees(math.atan2(trav.cross(Vector((dv.x, dv.y, 0))).z, trav.dot(Vector((dv.x, dv.y, 0))))), 1),
                                      dist_ft=round(dv.length / FT, 1))
            fail = [p for p in prof if p[1] < 2]
            lanes.append(dict(lane=li + 1, of=len(a['lanes']), at_bar=at_bar, profile=prof,
                              first_fail_ft=fail[0][0] if fail else None, fail_blockers=sorted({b for p in fail for b in p[2]})))
        inframe = {}
        for h in heads:
            c = sum((h.matrix_world @ v.co for v in h.data.vertices), Vector()) / len(h.data.vertices)
            p = world_to_camera_view(sc, cam, c); inframe[h.name] = bool(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0)
        out[a['key']] = dict(heads=hinfo, lanes=lanes, cam=cam.name, in_frame=inframe, req_ft=req, speed=a['speed_mph'])
finally:
    for n, v in prev.items(): find_lc(vl.layer_collection, n).exclude = v
json.dump(out, open(W + 'p7_visibility.json', 'w'), indent=1)
summ = {}
for k, v in out.items():
    summ[k] = dict(cone={h.split('_')[2]: x['cone_angle_deg'] for h, x in v['heads'].items()},
                   past={h.split('_')[2]: x['past_stop_line_ft'] for h, x in v['heads'].items()},
                   frame=[h.split('_')[2] for h, x in v['in_frame'].items() if not x],
                   lanes=[(l['lane'], {h.split('_')[2]: x['vis'] for h, x in l['at_bar'].items()}, l['first_fail_ft'], l['fail_blockers'][:6]) for l in v['lanes']])
result = summ
