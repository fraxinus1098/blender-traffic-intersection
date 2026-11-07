"""Phase 6 (Blender): render review cameras in the PROPOSED view (E_Signals + E_Markings excluded).
Set CAMS = [(camera, out_name), ...] and PCT (resolution %) before exec. Restores excludes and camera."""
import bpy, time
sc = bpy.context.scene; vl = bpy.context.view_layer
CAMS = globals().get('CAMS', [('CAM_Review_Oblique', 'phase6_oblique')])
PCT = globals().get('PCT', 100)
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
OUT = SH249_ROOT + r'export/'
def find_lc(lc, name):
    if lc.collection.name == name: return lc
    for c in lc.children:
        r = find_lc(c, name)
        if r: return r
HIDE = ['E_Signals', 'E_Markings']
prev = {n: find_lc(vl.layer_collection, n).exclude for n in HIDE}
cam0, pct0, path0 = sc.camera, sc.render.resolution_percentage, sc.render.filepath
times = {}
try:
    for n in HIDE: find_lc(vl.layer_collection, n).exclude = True
    sc.render.resolution_percentage = PCT
    sc.render.image_settings.file_format = 'PNG'
    for cam, name in CAMS:
        sc.camera = bpy.data.objects[cam]
        sc.render.filepath = OUT + name + '.png'
        t = time.time(); bpy.ops.render.render(write_still=True); times[name] = round(time.time() - t, 1)
finally:
    for n, v in prev.items(): find_lc(vl.layer_collection, n).exclude = v
    sc.camera, sc.render.resolution_percentage, sc.render.filepath = cam0, pct0, path0
result = dict(times=times, res=[sc.render.resolution_x, sc.render.resolution_y, PCT])
