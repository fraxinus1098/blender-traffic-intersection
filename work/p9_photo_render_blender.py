"""Phase 9B (Blender, v11 or an export copy): render model overlays from Mapillary photo cameras (transparent film).
Run inside Blender:  IDS = ['<id>', ...]; LAYER = 'existing' | 'proposed' | 'removed'; POSE = 'init' | 'solved';
                     PCT = 50; OUT = '<folder>'; exec(open(r'<repo>/work/p9_photo_render_blender.py').read())
Camera from work/p9_photos/p9_cams.json (pinhole after undistortion: K, size; pose_init from Mapillary SfM or
pose_solved from p9_photo_solve.py). Writes <OUT>/<id>_<LAYER>.png (RGBA).
LAYER: existing  = E_Signals + E_Signals_Remain + E_Markings (as built today; accuracy check)
       proposed  = change view: P_Signals, P_Signs, P_Markings green, E_Signals_Remain untinted (what will stand)
       removed   = E_Signals only (the compositor turns this into a red outline; removed markings are left out,
                   their outlines cluttered the photo)
Occluders: the bridge and buildings are holdouts (they hide what is behind them but are not drawn); trees, the
illustrative cars, roadway surfaces, aerial and radar zones are not rendered (the photo shows the real ones).
Everything (excludes, holdouts, object hide flags, camera, resolution, film, change view) is restored in a finally block."""
import bpy, json, math
from mathutils import Matrix
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
W = SH249_ROOT + 'work/'
IDS = globals()['IDS']; LAYER = globals().get('LAYER', 'existing'); POSE = globals().get('POSE', 'init')
PCT = globals().get('PCT', 50); OUT = globals().get('OUT', W + 'p9_photos/render/')
FT = 0.3048
CAMS = json.load(open(W + 'p9_photos/p9_cams.json'))
sc = bpy.context.scene; vl = bpy.context.view_layer

def walk(lc, out):
    out[lc.collection.name] = lc
    for c in lc.children: walk(c, out)
    return out
LC = walk(vl.layer_collection, {})
SHOW = {'existing': ['E_Signals', 'E_Signals_Remain', 'E_Markings'],
        'proposed': ['P_Signals', 'P_Signs', 'P_Markings', 'E_Signals_Remain'],
        'removed': ['E_Signals']}[LAYER]
HOLD = ['Context']                                     # bridge + buildings occlude (trees/cars excluded below)
NO = ['CTX_Trees', 'CTX_Vehicles']
state = {n: (lc.exclude, lc.holdout) for n, lc in LC.items()}
# re-including an excluded collection resets its objects' viewport hide (eye icon), e.g. the hidden P_CUT_* cutters
hidden = [o.name for o in vl.objects if o.hide_get()]
cam0, res0, pct0, film0, path0 = sc.camera, (sc.render.resolution_x, sc.render.resolution_y), sc.render.resolution_percentage, sc.render.film_transparent, sc.render.filepath
cd = bpy.data.cameras.new('TMP_P9_PHOTO'); cam = bpy.data.objects.new('TMP_P9_PHOTO', cd); sc.collection.objects.link(cam)
applied = False; done = []
try:
    for n, lc in LC.items():
        if n == sc.collection.name: continue
        lc.holdout = False
        lc.exclude = True
    def include(n):                                    # include n and its parents
        lc = LC[n]; lc.exclude = False
        for pn, plc in LC.items():
            if any(c is lc for c in plc.children) and pn != sc.collection.name: include(pn)
    for n in SHOW + HOLD + ['Engineering']: include(n)    # Engineering holds SUN_Main (and the cameras)
    for c in LC['Engineering'].children: c.exclude = True  # radar zones
    for n in HOLD: LC[n].holdout = True
    for n in NO: LC[n].exclude = True
    # Context's children other than trees/cars (bridge objects live directly in Context; buildings in CTX_Buildings)
    LC['CTX_Buildings'].exclude = False; LC['CTX_Buildings'].holdout = True
    for n in SHOW: LC[n].holdout = False
    # parents of SHOW collections must not be holdouts and their other children stay excluded
    for top in ('Existing', 'Proposed'):
        LC[top].holdout = False
        for c in LC[top].children:
            if c.collection.name not in SHOW: c.exclude = True
    if LAYER == 'proposed':
        g = {'MODE': 'apply'}; exec(open(W + 'p7_change_view.py').read(), g); applied = True
    sc.render.film_transparent = True; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.camera = cam
    for iid in IDS:
        C = CAMS[iid]; w, h = C['size']; K = C['K']
        pose = C['pose_solved'] if POSE == 'solved' else C['pose_init']
        fx = K[0][0]
        cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = fx / w * 36.0
        cd.shift_x = -(K[0][2] - (w - 1) / 2) / w; cd.shift_y = (K[1][2] - (h - 1) / 2) / w
        cd.clip_start = 0.1; cd.clip_end = 2000
        Rcv = Matrix(pose['R_world_from_cv'])
        Rbl = Rcv @ Matrix(((1, 0, 0), (0, -1, 0), (0, 0, -1)))      # Blender camera: -Z forward, +Y up
        M = Rbl.to_4x4(); M.translation = [c * FT for c in pose['loc_ft']]
        cam.matrix_world = M
        sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.resolution_percentage = PCT
        sc.render.filepath = OUT.rstrip('/\\') + '/' + f'{iid}_{LAYER}.png'
        bpy.ops.render.render(write_still=True)
        done.append(sc.render.filepath)
finally:
    if applied:
        g = {'MODE': 'restore', 'PURGE': True}; exec(open(W + 'p7_change_view.py').read(), g)
    for n, (ex, ho) in state.items():
        if n in LC: LC[n].exclude, LC[n].holdout = ex, ho
    for n in hidden:
        if n in vl.objects: bpy.data.objects[n].hide_set(True)
    sc.camera = cam0; sc.render.resolution_x, sc.render.resolution_y = res0; sc.render.resolution_percentage = pct0
    sc.render.film_transparent = film0; sc.render.filepath = path0
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
result = {'written': done, 'layer': LAYER, 'pose': POSE}
