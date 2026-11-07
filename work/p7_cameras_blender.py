"""Phase 7 (Blender): driver's-eye, pedestrian and APS close-up cameras from work/p7_data.json.
Driver: 3.5 ft eye, centred in one lane (the middle / second-from-left lane), 8 ft behind the upstream edge of the
proposed stop bar (front bumper at the bar), looking downstream along the lane-line axis, pitched up 7 deg, 24 mm.
Ped: 5 ft eye above the local surface (raycast), 5 ft behind the first crosswalk bar (on the new ramp / landing),
facing across to the far ramp, pitched down 2 deg, 24 mm. APS: close-up of push button PB on P_PED_<APS_POLE>.
Cameras go in Engineering, tagged sh249_type = camera_driver | camera_ped | camera_aps. Re-running replaces CAM_P7_Drv_* / Ped_* / APS_* (CAM_P7_RadarTop belongs to p7_radar_blender.py)."""
import bpy, json, math
from mathutils import Vector, Euler, Matrix
FT = 0.3048
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
W = SH249_ROOT + r'work/'
D = json.load(open(W + 'p7_data.json'))
APS_POLE = globals().get('APS_POLE', 'D')
eng = bpy.data.collections['Engineering']
for o in list(bpy.data.objects):
    if o.name.startswith(('CAM_P7_Drv_', 'CAM_P7_Ped_', 'CAM_P7_APS_')):
        cd = o.data; bpy.data.objects.remove(o); bpy.data.cameras.remove(cd)

def cam(name, xyz_m, heading_deg, pitch_deg, lens=24.0, props=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 2000
    ob = bpy.data.objects.new(name, cd); eng.objects.link(ob)
    ob.location = xyz_m
    ob.rotation_euler = Euler((math.radians(90 + pitch_deg), 0, math.radians(heading_deg - 90)), 'XYZ')
    for k, v in (props or {}).items(): ob[k] = v
    return ob

# ---- ground height (proposed surfaces, ignoring markings / hidden cutters / radar zones) ----
def find_lc(lc, n):
    if lc.collection.name == n: return lc
    for c in lc.children:
        r = find_lc(c, n)
        if r: return r
SKIP = ('P_RC', 'ENG_RZ_', 'P_MK_', 'E_MK_', 'CTX_TREE', 'REF_')
def ground_z(x, y):
    dg = bpy.context.evaluated_depsgraph_get(); o = Vector((x, y, 5.0))
    for _ in range(12):
        hit, loc, nrm, idx, ob, mx = bpy.context.scene.ray_cast(dg, o, Vector((0, 0, -1)), distance=10)
        if not hit: return 0.0, None
        if ob.name.startswith(SKIP) or any(c.name == 'P_RampCutters' for c in ob.users_collection):
            o = loc - Vector((0, 0, 0.001)); continue
        return loc.z, ob.name
    return 0.0, None

made = []
# ---- driver's eye ----
for a in D['approaches']:
    lanes = a['lanes']; k = (len(lanes) - 1) // 2; ln = lanes[k]
    x, y = ln['eye']
    name = 'CAM_P7_Drv_%sint_%s' % (a['inter'], a['dir'])
    cam(name, (x * FT, y * FT, 3.5 * FT), a['travel_deg'], 7.0, props=dict(
        sh249_type='camera_driver', sh249_status='engineering', sh249_phase='engineering',
        sh249_approach=a['key'], sh249_heads=','.join(a['heads']), sh249_lane='%d of %d (from the left)' % (k + 1, len(lanes)),
        sh249_note='Driver eye 3.5 ft above pavement, lane %d of %d from the left on the %s approach to the %s feeder intersection, '
                   '8 ft behind the upstream edge of the proposed stop bar, looking downstream (%.1f deg).' % (
                       k + 1, len(lanes), a['dir'], a['inter'], a['travel_deg'])))
    made.append(name)
# ---- pedestrian ----
for c in D['crosswalks']:
    x, y = c['cam']; gz, gob = ground_z(x * FT, y * FT)
    if gz < 0: gz, gob = 0.0, 'pavement level (gap beside ramp mesh)'   # never below pavement
    name = 'CAM_P7_Ped_%s' % c['key']
    cam(name, (x * FT, y * FT, gz + 5.0 * FT), c['dir_deg'], -2.0, props=dict(
        sh249_type='camera_ped', sh249_status='engineering', sh249_phase='engineering', sh249_crosswalk=c['key'],
        sh249_note='Pedestrian eye 5 ft above the walking surface (%s, z %.2f ft), 5 ft behind the first crosswalk bar at the new ramp, '
                   'facing across: %s; ped poles %s; %.0f ft crossing.' % (gob, gz / FT, c['note'], c['peds'], c['length_ft'])))
    made.append(name)
# ---- APS push button close-up ----
pole = bpy.data.objects['P_PED_' + APS_POLE]; mw = pole.matrix_world; base = mw.translation
vs = [mw @ v.co for v in pole.data.vertices]
def rad(v): return math.hypot(v.x - base.x, v.y - base.y)
btn = [v for v in vs if 3.2 * FT < v.z < 4.3 * FT and rad(v) > 0.22 * FT]
sign = [v for v in vs if 4.3 * FT < v.z < 6.2 * FT and rad(v) > 0.22 * FT]
cb = sum(btn, Vector()) / len(btn); cs = sum(sign, Vector()) / len(sign)
# facing: horizontal direction from the pole axis to the sign/button cluster
f = Vector((cs.x - base.x, cs.y - base.y, 0)); f.normalize()
tgt = (cb + cs) / 2 + Vector((0, 0, 0.15 * FT))
side = Vector((-f.y, f.x, 0))
eye = tgt + f * (4.6 * FT) + Vector((0, 0, 0.3 * FT)) + side * (1.0 * FT)
d = tgt - eye; heading = math.degrees(math.atan2(d.y, d.x)); pitch = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
name = 'CAM_P7_APS_%s' % APS_POLE
cam(name, eye, heading, pitch, lens=35.0, props=dict(
    sh249_type='camera_aps', sh249_status='engineering', sh249_phase='engineering',
    sh249_note='Close-up of APS pedestal pole %s: push button %s with its R10-3e sign (sheet 28), button at 3 ft-9 in.' % (
        APS_POLE, pole.get('sh249_push_button', ''))))
made.append(name)
result = dict(made=made, aps=dict(btn=[round(c / FT, 2) for c in cb], sign=[round(c / FT, 2) for c in cs], n_btn=len(btn), n_sign=len(sign),
                                  facing_deg=round(math.degrees(math.atan2(f.y, f.x)), 1)))
