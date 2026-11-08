"""Phase 9A.4 (Blender, clean model v11): low-poly tree shape variants, still instanced (linked meshes).
Run inside Blender:  exec(open(r'<repo>/work/p9_trees_blender.py').read())
Builds 7 unit meshes (crown radius 1, total height 1; objects are scaled (r, r, h)):
  CTX_TreeMesh_Round_A/B   lumpy sphere crown                      h/r 1.7-2.6 (broadleaf)
  CTX_TreeMesh_Spread_A/B  wide dome, flat underside, short trunk  h/r < 1.7  (live-oak type)
  CTX_TreeMesh_Oval_A/B    taller egg crown, narrowing upward      h/r 2.6-3.6
  CTX_TreeMesh_Pine        long bare trunk, crown in the top 45 %  h/r >= 3.6 (loblolly-pine type, as in the photos)
then relinks every CTX_TREE_* object by its h/r, renames it CTX_TREE_<nnn>_<Shape> and updates sh249_variant.
Old CTX_TreeMesh_<S|M|L|XL>_<A|B> meshes are removed. Re-runnable."""
import bpy, bmesh, math, random

def mat(name, rgb, rough=0.9, spec=0.15):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = spec
    m.diffuse_color = (*rgb, 1)
    return m
M_TRUNK = bpy.data.materials['MAT_CTX_TreeTrunk']
M_LEAF = [bpy.data.materials['MAT_CTX_TreeCanopy_A'], bpy.data.materials['MAT_CTX_TreeCanopy_B']]
M_PINE = mat('MAT_CTX_TreeCanopy_Pine', (0.055, 0.11, 0.06))

def shape_of(h_over_r):
    if h_over_r < 1.7: return 'Spread'
    if h_over_r < 2.6: return 'Round'
    if h_over_r < 3.6: return 'Oval'
    return 'Pine'

def build(name, shape, leaf_mat):
    old = bpy.data.meshes.get(name)
    if old: old.name = name + '_old'
    rnd = random.Random(hash(name) & 0xffff)
    bm = bmesh.new()
    # (crown bottom, crown top, trunk radius) as fractions of the total height; crown radius 1
    base, top, tr = {'Round': (0.28, 1.0, 0.06), 'Spread': (0.32, 1.0, 0.07), 'Oval': (0.20, 1.0, 0.07),
                     'Pine': (0.55, 1.0, 0.10)}[shape]
    zc, vr = (base + top) / 2, (top - base) / 2
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=tr, radius2=tr * 0.65, depth=zc)
    bmesh.ops.translate(bm, verts=r['verts'], vec=(0, 0, zc / 2))
    blobs = [((0, 0, 0), 1.0)]
    if shape == 'Pine':                                         # irregular top: two offset clumps
        blobs = [((0, 0, -0.15), 0.85), ((0.25, 0.1, 0.35), 0.6), ((-0.2, -0.2, 0.25), 0.6)]
    for (ox, oy, oz), s in blobs:
        c = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        for v in c['verts']:
            j = 1 + rnd.uniform(-0.09, 0.09)
            x, y, z = v.co.x * j, v.co.y * j, v.co.z * j
            if shape == 'Spread' and z < 0: z *= 0.35             # flat underside
            if shape == 'Oval': k = 1 - 0.28 * max(z, 0); x *= k; y *= k
            v.co.x, v.co.y, v.co.z = (x + ox) * s, (y + oy) * s, zc + (z * s + oz) * vr
    for f in bm.faces:
        f.material_index = 0 if all(v.co.x ** 2 + v.co.y ** 2 < (tr * 1.5) ** 2 and v.co.z < base + 0.02 for v in f.verts) else 1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(M_TRUNK); me.materials.append(leaf_mat)
    for p in me.polygons: p.use_smooth = p.material_index == 1
    return me

meshes = {}
for shape in ('Round', 'Spread', 'Oval'):
    for li, ml in enumerate(M_LEAF):
        meshes[(shape, li)] = build(f'CTX_TreeMesh_{shape}_{"AB"[li]}', shape, ml)
meshes[('Pine', 0)] = meshes[('Pine', 1)] = build('CTX_TreeMesh_Pine', 'Pine', M_PINE)

from collections import Counter
cnt = Counter()
for o in sorted([o for o in bpy.data.collections['CTX_Trees'].objects if o.name.startswith('CTX_TREE_')], key=lambda o: o.name):
    idx = int(o.name.split('_')[2])
    r, h = o.scale.x, o.scale.z
    shape = shape_of(h / r)
    o.data = meshes[(shape, idx % 2)]
    o.name = f'CTX_TREE_{idx:03d}_{shape}'
    o['sh249_variant'] = shape
    cnt[shape] += 1
for m in list(bpy.data.meshes):
    if m.name.startswith('CTX_TreeMesh_') and m.users == 0: bpy.data.meshes.remove(m)
result = {'shapes': dict(cnt), 'meshes': sorted(m.name for m in bpy.data.meshes if m.name.startswith('CTX_TreeMesh_'))}
