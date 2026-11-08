"""Phase 9A.2 (Blender, clean model v11): import the rebuilt SH 249 bridge from work/p9_bridge.json.
Run inside Blender:  exec(open(r'<repo>/work/p9_bridge_blender.py').read())
Keeps the four Phase 3 objects (CTX_SH249_Deck / _Rails / _Embankment / _Bents: names, collection, tags) and swaps
their mesh data; adds CTX_SH249_Girders and CTX_SH249_Markings to the same collection with context tags.
Lifts the lidar trees that stand on the new side slopes (z from the lidar ground). Re-runnable."""
import bpy, bmesh, json
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
assert bpy.data.filepath.endswith('v11.blend'), 'apply only to the v11 clean model'
D = json.load(open(SH249_ROOT + 'work/p9_bridge.json'))
M = D['meta']
_B = json.load(open(SH249_ROOT + 'work/p9_lidar.json'))['bridge']
B_AX, B_NR, B_C0 = _B['axis_unit'], _B['normal_unit'], _B['centre_on_Y0']
SRC = 'USGS 3DEP lidar TX_Houston_B24 (2024) + Mapillary photos (2026)'

def mat(name, rgb, rough=0.85):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    m.diffuse_color = (*rgb, 1)
    return m
mat('MAT_P9_Mainlane', (0.50, 0.49, 0.46), 0.88)
mat('MAT_P9_SlopePaving', (0.40, 0.39, 0.36), 0.9)
mat('MAT_P9_Bridge_RedStripe', (0.42, 0.05, 0.04), 0.7)

NOTE = {
    'CTX_SH249_Deck': ('bridge_deck', f"Context (illustrative): SH 249 mainlane bridge deck, 9-in. slab. Ends at the lidar bridge-deck extent; top follows the lidar profile ({M['deck_top_crest_ft']:.1f} ft over Spring Cypress, {M['deck_top_ends_ft'][0]:.1f}/{M['deck_top_ends_ft'][1]:.1f} ft at the S/N abutments). Deck edges from sheets 38-39."),
    'CTX_SH249_Girders': ('bridge_girders', f"Context (illustrative): {M['n_girders']} Tx46-type prestressed girders per span (fascia beams rectangular); soffit about {M['min_soffit_over_spring_cypress_ft']:.1f} ft over Spring Cypress."),
    'CTX_SH249_Bents': ('bridge_bents', "Context (illustrative): bent caps and square columns (as in the 2026 photos) at the N, centre and S medians (Phase 3 positions) plus one bent at each header-bank toe; abutment caps at the lidar deck ends. Column positions avoid pavement and curbs."),
    'CTX_SH249_Rails': ('bridge_rail', "Context (illustrative): 32-in. concrete safety-shape barriers along both outside edges and the median; red stripe on the outside face over the bridge (as in the photos)."),
    'CTX_SH249_Embankment': ('bridge_embankment', "Context: mainline fill beyond the abutments (top = lidar profile), concrete slope paving on the header banks under the deck ends (toe assumed 4 ft behind the U-turn curbs) and near the bridge, side slopes from the lidar ground (grass)."),
    'CTX_SH249_Markings': ('bridge_markings', "Context (illustrative): SH 249 mainlane markings, 3 lanes per direction with a 12-ft inside shoulder (yellow edge line), 10/30-ft lane lines and a white outside edge line (lane count from the 2026 photos)."),
}
ctx = bpy.data.collections['Context']
res = {}
for name, d in D['objects'].items():
    me = bpy.data.meshes.new(name + '_p9')
    me.from_pydata([tuple(v) for v in d['v']], [], d['f'])
    for mn in d['mats']: me.materials.append(bpy.data.materials[mn])
    me.polygons.foreach_set('material_index', d['m'])
    if 'uv' in d:
        uvl = me.uv_layers.new(name='rastUVmap')
        lv = [0] * len(me.loops); me.loops.foreach_get('vertex_index', lv)
        flat = [c for i in lv for c in d['uv'][i]]
        uvl.data.foreach_set('uv', flat)
    bm = bmesh.new(); bm.from_mesh(me)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    if name in ('CTX_SH249_Deck', 'CTX_SH249_Embankment'):
        # 'paveUV' for the jointed concrete texture (MAT_P9_Mainlane, p9_concrete_blender.py): along the SH 249 axis
        # / 30 ft, across (q - 1 ft) / 24 ft, so the longitudinal joints fall on the 13/25/37/49-ft lane lines
        uvp = bm.loops.layers.uv.new('paveUV')
        for f in bm.faces:
            for l in f.loops:
                x, y = l.vert.co.x / 0.3048, l.vert.co.y / 0.3048
                s = (x - B_C0[0]) * B_AX[0] + (y - B_C0[1]) * B_AX[1]; q = (x - B_C0[0]) * B_NR[0] + (y - B_C0[1]) * B_NR[1]
                l[uvp].uv = (s / 30.0, (q - 1.0) / 24.0)
    bm.to_mesh(me); bm.free()
    me.validate(); me.update()
    smooth = name == 'CTX_SH249_Embankment'          # lidar-ground slopes: smooth shading
    for p in me.polygons: p.use_smooth = smooth
    o = bpy.data.objects.get(name)
    if o is None:
        o = bpy.data.objects.new(name, me); ctx.objects.link(o)
    else:
        old = o.data; o.data = me
        if old.users == 0: bpy.data.meshes.remove(old)
    me.name = name
    typ, note = NOTE[name]
    for k, v in dict(sh249_status='context', sh249_phase='context', sh249_type=typ, sh249_note=note,
                     sh249_source=f"plan deck edges (sheets 38-39); geometry: {SRC}").items():
        o[k] = v
    if 'sh249_deck_top_ft' in o.keys(): del o['sh249_deck_top_ft']        # 9A.1 uniform re-level, superseded
    res[name] = [len(me.vertices), len(me.polygons)]
# trees on the side slopes stand on the lidar ground
lifted = 0
by_idx = {o.name[:13]: o for o in bpy.data.objects if o.name.startswith('CTX_TREE_')}   # 'CTX_TREE_nnn_' (shape suffix may change)
for n, z in M['tree_z_m'].items():
    t = by_idx.get(n[:13])
    if t is not None: t.location.z = z; lifted += 1
res['trees_lifted'] = lifted
result = res
