"""Phase 7 (Blender): render cameras to export/<name>.png in one of three views, restoring everything afterwards.
Globals: CAMS = [(camera, out_name), ...], VIEW = 'proposed' | 'change' | 'radar', PCT (resolution %, default 100).
proposed: E_Signals + E_Markings excluded (as p6_render_blender.py).
change:   everything shown, p7_change_view.py applied (remove red, new green) and restored + purged afterwards.
radar:    proposed view + Engineering/ENG_RadarZones made renderable for the duration."""
import bpy, time
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
W = SH249_ROOT + r'work/'
OUT = globals().get('OUT', SH249_ROOT + r'export/')
CAMS = globals().get('CAMS', []); VIEW = globals().get('VIEW', 'proposed'); PCT = globals().get('PCT', 100)
sc = bpy.context.scene; vl = bpy.context.view_layer
def find_lc(lc, n):
    if lc.collection.name == n: return lc
    for c in lc.children:
        r = find_lc(c, n)
        if r: return r
HIDE = ['E_Signals', 'E_Markings'] if VIEW in ('proposed', 'radar') else []
prev = {n: find_lc(vl.layer_collection, n).exclude for n in ['E_Signals', 'E_Markings']}
rz = bpy.data.collections.get('ENG_RadarZones'); rz_prev = rz.hide_render if rz else None
cam0, pct0, path0 = sc.camera, sc.render.resolution_percentage, sc.render.filepath
times = {}; applied = False
try:
    for n in prev: find_lc(vl.layer_collection, n).exclude = n in HIDE
    if rz is not None: rz.hide_render = VIEW != 'radar'
    if VIEW == 'change':
        g = {'MODE': 'apply'}; exec(open(W + 'p7_change_view.py').read(), g); applied = True
    sc.render.resolution_percentage = PCT; sc.render.image_settings.file_format = 'PNG'
    for cam, name in CAMS:
        sc.camera = bpy.data.objects[cam]; sc.render.filepath = OUT + name + '.png'
        t = time.time(); bpy.ops.render.render(write_still=True); times[name] = round(time.time() - t, 1)
finally:
    if applied:
        g = {'MODE': 'restore', 'PURGE': True}; exec(open(W + 'p7_change_view.py').read(), g)
    for n, v in prev.items(): find_lc(vl.layer_collection, n).exclude = v
    if rz is not None: rz.hide_render = rz_prev
    sc.camera, sc.render.resolution_percentage, sc.render.filepath = cam0, pct0, path0
result = dict(view=VIEW, times=times, res=[sc.render.resolution_x, sc.render.resolution_y, PCT])
