"""Phase 9A.3 (Blender, clean model v11): jointed concrete pavement (the 2026 photos show concrete everywhere:
frontage roads, Spring Cypress, U-turns, mainlanes).
Run inside Blender:  exec(open(r'<repo>/work/p9_concrete_blender.py').read())
- MAT_P9_ConcretePave: UV Map 'paveUV' -> Image Texture work/tex/p9_concrete_pave.jpg (30 x 24 ft tile, sawn joints)
  -> Principled. MAT_P9_Mainlane (bridge deck + mainline fill) gets the same texture.
- E_RD_Pavement: faces split along v = V_N and v = V_S (v = Y - 0.045 X, lines parallel to Spring Cypress) and along
  the deck edge lines (flat cuts, no shape change), then a 'paveUV' layer: faces in the Spring Cypress band
  (V_S < v < V_N) and under the deck use joints along Spring Cypress; the rest (frontage roads) along SH 249.
  Its material slot goes MAT_Asphalt -> MAT_P9_ConcretePave (MAT_Asphalt is kept with a fake user).
Re-runnable: the split is only done once (checked by the 'paveUV' layer)."""
import bpy, bmesh, json, math
from mathutils import Vector
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
assert bpy.data.filepath.endswith('v11.blend'), 'apply only to the v11 clean model'
FT = 0.3048
TU, TV = 30.0, 24.0                       # tile along / across (ft)
V_N, V_S = 62.0, -66.0                    # Spring Cypress band (ft), between the frontage stop bars
B = json.load(open(SH249_ROOT + 'work/p9_lidar.json'))['bridge']
AX, NR, C0, HW = B['axis_unit'], B['normal_unit'], B['centre_on_Y0'], B['deck_width_ft'] / 2
SC = (1 / math.hypot(1, 0.045), 0.045 / math.hypot(1, 0.045))

def textured(name, rough=0.85):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    for n in [n for n in N if n.name.startswith('P9_')]: N.remove(n)
    bsdf = N.get('Principled BSDF')
    uv = N.new('ShaderNodeUVMap'); uv.name = 'P9_UV'; uv.uv_map = 'paveUV'; uv.location = (-700, 300)
    tx = N.new('ShaderNodeTexImage'); tx.name = 'P9_Tex'; tx.location = (-450, 300)
    path = SH249_ROOT + 'work/tex/p9_concrete_pave.jpg'
    img = bpy.data.images.get('p9_concrete_pave.jpg') or bpy.data.images.load(path)
    img.filepath = bpy.path.relpath(path); tx.image = img
    L.new(uv.outputs['UV'], tx.inputs['Vector']); L.new(tx.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough
    m.diffuse_color = (0.30, 0.29, 0.27, 1)
    return m
mp = textured('MAT_P9_ConcretePave'); textured('MAT_P9_Mainlane')

def sc_uv(x, y):      # along Spring Cypress / across, ft
    return (x * SC[0] + y * SC[1]) / TU, (y - 0.045 * x) * SC[0] / TV
def ax_uv(x, y):      # along SH 249 / across (joints 1 ft off the axis so they fall on the 13/25/37/49-ft lines)
    s = (x - C0[0]) * AX[0] + (y - C0[1]) * AX[1]; q = (x - C0[0]) * NR[0] + (y - C0[1]) * NR[1]
    return s / TU, (q - 1.0) / TV

o = bpy.data.objects['E_RD_Pavement']; me = o.data
res = {'pavement_mods': [m.name for m in o.modifiers]}
if 'paveUV' not in me.uv_layers:
    bm = bmesh.new(); bm.from_mesh(me)
    n0 = len(bm.faces)
    cuts = [((0, V_N * FT, 0), (-0.045, 1, 0)), ((0, V_S * FT, 0), (-0.045, 1, 0))]
    for sgn in (-1, 1):
        cuts.append((((C0[0] + sgn * HW * NR[0]) * FT, (C0[1] + sgn * HW * NR[1]) * FT, 0), (NR[0], NR[1], 0)))
    for co, no in cuts:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    uvl = bm.loops.layers.uv.new('paveUV')
    n_sc = 0
    for f in bm.faces:
        c = f.calc_center_median(); x, y = c.x / FT, c.y / FT
        v = y - 0.045 * x; q = (x - C0[0]) * NR[0] + (y - C0[1]) * NR[1]
        use_sc = V_S < v < V_N or abs(q) < HW
        n_sc += use_sc
        for l in f.loops:
            lx, ly = l.vert.co.x / FT, l.vert.co.y / FT
            l[uvl].uv = sc_uv(lx, ly) if use_sc else ax_uv(lx, ly)
    bm.to_mesh(me); bm.free(); me.update()
    res.update(faces_before=n0, faces_after=len(me.polygons), faces_sc=n_sc)
for s in o.material_slots:
    if s.material and s.material.name == 'MAT_Asphalt': s.material = mp
a = bpy.data.materials.get('MAT_Asphalt')
if a: a.use_fake_user = True
res['slots'] = [s.material.name for s in o.material_slots]
res['uv_layers'] = list(me.uv_layers.keys())
res['z_range'] = [min(v.co.z for v in me.vertices), max(v.co.z for v in me.vertices)]
result = res
