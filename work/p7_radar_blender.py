"""Phase 7 (Blender): radar detection zones from work/p7_radar_zones.json (built by p7_geom.py + p7_build_zones.py).
One object per radar, ENG_RZ_<id>: translucent fill + outline ribbon + flat label (text converted to mesh, so it
exports to GLB). Collection Engineering/ENG_RadarZones, hide_render = True (normal renders unaffected; the
Phase 7 render script switches it on). Re-running replaces ENG_RZ_* only."""
import bpy, bmesh, json, math, re
from mathutils import Matrix, Vector
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
W = SH249_ROOT + r'work/'
Z = json.load(open(W + 'p7_radar_zones.json'))
FT = 0.3048
eng = bpy.data.collections['Engineering']
col = bpy.data.collections.get('ENG_RadarZones') or bpy.data.collections.new('ENG_RadarZones')
if col.name not in eng.children: eng.children.link(col)
col.hide_render = True
for o in list(col.objects):
    if o.name.startswith('ENG_RZ_'):
        me = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me)

def mat(name, rgb, alpha, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    p.inputs['Base Color'].default_value = (*rgb, 1); p.inputs['Alpha'].default_value = alpha
    p.inputs['Roughness'].default_value = 0.6
    p.inputs['Emission Strength'].default_value = 0.0
    if emit:
        p.inputs['Emission Color'].default_value = (*rgb, 1); p.inputs['Emission Strength'].default_value = emit
    nt.links.new(p.outputs['BSDF'], out.inputs['Surface'])
    m.surface_render_method = 'BLENDED' if alpha < 1 else 'DITHERED'
    m.use_backface_culling = False; m.diffuse_color = (*rgb, alpha)
    return m
M = {'PR': [mat('MAT_P7_RZ_PR_Fill', (0.05, 0.75, 0.95), 0.20), mat('MAT_P7_RZ_PR_Edge', (0.05, 0.75, 0.95), 0.9, 0.3)],
     'ADV': [mat('MAT_P7_RZ_ADV_Fill', (0.95, 0.25, 0.85), 0.20), mat('MAT_P7_RZ_ADV_Edge', (0.95, 0.25, 0.85), 0.9, 0.3)]}
LAB = mat('MAT_P7_RZ_Label', (1, 1, 1), 1.0, 0.4)
DIRW = {'SB': 'SB', 'NB': 'NB', 'EB': 'EB', 'WB': 'WB'}

def text_mesh(body, size, align='CENTER'):
    cu = bpy.data.curves.new('tmp_p7_txt', 'FONT'); cu.body = body; cu.size = size
    cu.align_x = align; cu.align_y = 'CENTER'; cu.space_line = 1.1; cu.resolution_u = 3
    ob = bpy.data.objects.new('tmp_p7_txt', cu); bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    return me

made = []
for z in Z:
    rad = bpy.data.objects.get('P_RADAR_' + z['id'])
    sched = ''
    if rad:
        m_ = re.search(r'schedule\): (.*?)\. Mounted', rad.get('sh249_note', ''))
        sched = m_.group(1) if m_ else ''
    meta = z['meta']; kind = z['kind']
    bm = bmesh.new()
    for part, mi in ((z['fill'], 0), (z['edge'], 1)):
        vs = [bm.verts.new(v) for v in part['v']]
        for f in part['f']:
            try: bm.faces.new([vs[i] for i in f]).material_index = mi
            except ValueError: pass
    # label: id (5 ft) + approach line (2 ft), flat, reading for the approaching driver
    sub = '%s %s' % (DIRW[meta['dir']], 'stop-bar presence' if kind == 'PR' else 'advance %d-%d ft' % tuple(meta['range_ft']))
    k = 2.0 if kind == 'ADV' else 1.0          # ADV zones are ~200 ft long: double-size labels
    for body, size, dy in ((z['id'], 5.0 * k * FT, 1.6 * k * FT), (sub, 2.0 * k * FT, -2.6 * k * FT)):
        tm = text_mesh(body, size)
        R = Matrix.Rotation(math.radians(z['label_rot_deg']), 4, 'Z')
        T = Matrix.Translation(Vector((z['label_xy_m'][0], z['label_xy_m'][1], 0.036))) @ R @ Matrix.Translation((0, dy, 0))
        tm.transform(T)
        off = len(bm.verts); bm.verts.ensure_lookup_table()
        nv = [bm.verts.new(v.co) for v in tm.vertices]
        for p in tm.polygons:
            try: bm.faces.new([nv[i] for i in p.vertices]).material_index = 2
            except ValueError: pass
        bpy.data.meshes.remove(tm)
    me = bpy.data.meshes.new('ENG_RZ_' + z['id']); bm.to_mesh(me); bm.free()
    for m in (M[kind][0], M[kind][1], LAB): me.materials.append(m)
    ob = bpy.data.objects.new('ENG_RZ_' + z['id'], me); col.objects.link(ob)
    ob.visible_shadow = False
    ob['sh249_status'] = 'engineering'; ob['sh249_phase'] = 'engineering'; ob['sh249_type'] = 'radar_zone'
    ob['sh249_callout'] = z['id']; ob['sh249_radar'] = 'P_RADAR_' + z['id']; ob['sh249_sheet'] = 28
    ob['sh249_zone_kind'] = 'presence' if kind == 'PR' else 'advance'
    ob['sh249_approach'] = meta['approach']; ob['sh249_aim_deg'] = meta['aim_deg']
    if meta['range_ft']: ob['sh249_range_ft'] = meta['range_ft']
    if meta['fov_cover'] is not None: ob['sh249_fov_cover'] = meta['fov_cover']
    ob['sh249_note'] = ('Radar detection zone %s (sheet 28 radar schedule: %s). Illustrative footprint: %s. '
                        'Final zone placement and aim are set by the radar vendor (sheet 23 notes 39, 43, 44).') % (z['id'], sched, meta['desc'])
    made.append((ob.name, len(me.polygons)))
# plan camera for the radar overview (ortho, 1500 ft wide, covers all ADV zones)
cd = bpy.data.cameras.get('CAM_P7_RadarTop') or bpy.data.cameras.new('CAM_P7_RadarTop')
cd.type = 'ORTHO'; cd.ortho_scale = 1500 * FT; cd.clip_end = 2000
cam = bpy.data.objects.get('CAM_P7_RadarTop') or bpy.data.objects.new('CAM_P7_RadarTop', cd)
if cam.name not in eng.objects: eng.objects.link(cam)
cam.location = (75 * FT, -20 * FT, 600 * FT); cam.rotation_euler = (0, 0, 0)
cam['sh249_type'] = 'camera_review'; cam['sh249_status'] = 'engineering'; cam['sh249_phase'] = 'engineering'
result = {'made': made, 'collection': col.name, 'hide_render': col.hide_render}
