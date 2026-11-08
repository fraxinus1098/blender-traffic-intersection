"""Phase 9: GLB export (run in blend/sh249_sc_v12_export.blend ONLY). Same as p8_export_glb.py except the
filename check and the camera presets file (work/p9_cameras.json).
Globals: OUT (glb path), DRACO (bool, default False), GPU_INST (bool, default True), JPEG_Q (default 85).
Selects Aerial, Context, Existing, Proposed (minus P_RampCutters) and Engineering/ENG_RadarZones;
leaves out Reference, P_RampCutters, SUN_Main, ORIGIN_SC and the cameras (camera presets go to p9_cameras.json).
Runs mesh.validate() on every exported mesh first (the exporter calls it and warns if it changes anything).
Restores the selection afterwards. Writes the exporter log lines to the result."""
import bpy, json, io, contextlib, os
assert bpy.data.filepath.lower().endswith('v12_export.blend'), 'run only in the export copy'
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
ROOT = SH249_ROOT + r''
OUT = globals().get('OUT', ROOT + 'export/sh249_springcypress.glb')
DRACO = globals().get('DRACO', False)
GPU_INST = globals().get('GPU_INST', True)
JPEG_Q = globals().get('JPEG_Q', 85)
C = bpy.data.collections
def all_objs(col):
    s = set(col.objects)
    for ch in col.children: s |= all_objs(ch)
    return s
sel = set()
for n in ('Aerial', 'Context', 'Existing', 'Proposed'):
    sel |= all_objs(C[n])
sel -= all_objs(C['P_RampCutters'])
sel |= all_objs(C['ENG_RadarZones'])
sel = {o for o in sel if o.type == 'MESH'}
fixed = [o.name for o in sel if o.data.validate()]
vl = bpy.context.view_layer
prev_sel = [o for o in vl.objects if o.select_get()]; prev_act = vl.objects.active
# temporary, restored in finally: unselectable objects (the aerial) can't be selected; the Reference layer
# collection is excluded so its empty child collections don't become nodes
unsel = [o for o in sel if o.hide_select]
for o in unsel: o.hide_select = False
ref_lc = vl.layer_collection.children['Reference']; ref_ex = ref_lc.exclude; ref_lc.exclude = True
for o in vl.objects: o.select_set(False)
for o in sel: o.select_set(True)
not_sel = [o.name for o in sel if not o.select_get()]
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, use_visible=False,
            use_renderable=False, export_extras=True, export_apply=True, export_cameras=False, export_lights=False,
            export_image_format='JPEG', export_jpeg_quality=JPEG_Q, export_image_quality=JPEG_Q,
            export_draco_mesh_compression_enable=DRACO, export_gpu_instances=GPU_INST,
            export_hierarchy_full_collections=True, export_yup=True)
finally:
    ref_lc.exclude = ref_ex
    for o in unsel: o.hide_select = True
    for o in vl.objects: o.select_set(False)
    for o in prev_sel: o.select_set(True)
    vl.objects.active = prev_act
# camera presets for the viewer (Blender Z-up metres -> glTF Y-up: (x, z, -y))
cams = {}
for o in bpy.data.objects:
    if o.type != 'CAMERA': continue
    m = o.matrix_world; d = o.data
    p = m.translation; fwd = -(m.to_3x3().col[2]); up = m.to_3x3().col[1]
    cv = lambda v: [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]
    cams[o.name] = {'pos': cv(p), 'fwd': cv(fwd), 'up': cv(up), 'type': d.type,
        'lens': d.lens, 'sensor': d.sensor_width, 'ortho': d.ortho_scale, 'clip_end': d.clip_end,
        'note': o.get('sh249_note', '')}
json.dump(cams, open(ROOT + 'work/p9_cameras.json', 'w'), indent=1)
log = [l for l in buf.getvalue().splitlines() if l.strip()]
result = {'out': OUT, 'bytes': os.path.getsize(OUT), 'n_selected': len(sel), 'not_selectable': not_sel, 'validate_fixed': fixed,
          'warnings': [l for l in log if 'WARN' in l.upper() or 'ERROR' in l.upper()][:40], 'n_log': len(log), 'cams': len(cams)}
