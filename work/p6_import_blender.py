"""Phase 6 (Blender): import OSM building massing + NAIP-derived trees into collection Context.
Run inside Blender:  exec(open(r'<repo>/work/p6_import_blender.py').read())
Set STEP = 'buildings' or 'trees' (or 'all'). Re-running replaces CTX_BLDG_* / CTX_TREE_* objects only."""
import bpy, json, math, os, random
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
WORK = SH249_ROOT + r'work/'
FT = 0.3048
STEP = globals().get('STEP', 'all')
ctx = bpy.data.collections['Context']

def mat(name, rgb, rough=0.9, spec=0.3):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = spec
    m.diffuse_color = (*rgb, 1)
    return m

def sub_collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name); ctx.children.link(c)
    return c

def tag(o, props):
    for k, v in props.items(): o[k] = v

def import_buildings():
    col = sub_collection('CTX_Buildings')
    for o in list(col.objects):
        if o.name.startswith('CTX_BLDG_'): bpy.data.objects.remove(o)
    m_wall = mat('MAT_CTX_Bldg_Wall', (0.56, 0.53, 0.49), 0.9)
    m_roof = mat('MAT_CTX_Bldg_Roof', (0.62, 0.62, 0.60), 0.85)
    m_can = mat('MAT_CTX_Canopy', (0.80, 0.80, 0.80), 0.6)
    data = json.load(open(WORK + 'p6_context.json'))
    for name, d in data.items():
        me = bpy.data.meshes.new(name)
        me.from_pydata(d['v'], [], d['f']); me.validate(); me.update()
        canopy = d['props']['sh249_type'] == 'building_canopy'
        me.materials.append(m_can if canopy else m_wall)
        me.materials.append(m_can if canopy else m_roof)
        for p, mi in zip(me.polygons, d['m']): p.material_index = mi
        for p in me.polygons: p.use_smooth = False
        o = bpy.data.objects.new(name, me); col.objects.link(o)
        tag(o, d['props'])
    return len(data)

def tree_meshes():
    """Four low-poly broadleaf variants: 6-sided trunk + flattened icosphere crown (subdiv 1).
    Unit size: crown radius 1 m, total height 1 m; instances are scaled per tree."""
    import bmesh
    m_trunk = mat('MAT_CTX_TreeTrunk', (0.20, 0.15, 0.10), 0.95)
    m_leaf = [mat('MAT_CTX_TreeCanopy_A', (0.085, 0.16, 0.055), 0.9, 0.15),
              mat('MAT_CTX_TreeCanopy_B', (0.11, 0.18, 0.06), 0.9, 0.15)]
    # (name, crown base as fraction of height, crown vertical radius fraction, trunk radius fraction of crown r)
    V = {'S': (0.30, 0.36, 0.06), 'M': (0.33, 0.34, 0.055), 'L': (0.36, 0.33, 0.05), 'XL': (0.38, 0.32, 0.045)}
    out = {}
    for k, (base, vr, tr) in V.items():
        for li, ml in enumerate(m_leaf):
            name = f'CTX_TreeMesh_{k}_{"AB"[li]}'
            old = bpy.data.meshes.get(name)
            if old: bpy.data.meshes.remove(old)
            bm = bmesh.new()
            # trunk: from 0 to crown centre
            zc = base + vr
            r = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=tr, radius2=tr * 0.7, depth=zc)
            bmesh.ops.translate(bm, verts=r['verts'], vec=(0, 0, zc / 2))
            c = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
            rnd = random.Random(hash(name) & 0xffff)
            for v in c['verts']:
                j = 1 + rnd.uniform(-0.09, 0.09)                     # lumpy crown
                v.co.x *= j; v.co.y *= j; v.co.z = v.co.z * vr * j + zc
            for f in bm.faces:            # trunk verts lie within 0.2 of the axis; crown verts at ~0.9-1.1
                f.material_index = 0 if all(v.co.x ** 2 + v.co.y ** 2 < 0.04 for v in f.verts) else 1
            me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
            me.materials.append(m_trunk); me.materials.append(ml)
            for p in me.polygons: p.use_smooth = p.material_index == 1
            out[(k, li)] = me
    return out

def import_trees():
    col = sub_collection('CTX_Trees')
    for o in list(col.objects):
        if o.name.startswith('CTX_TREE_'): bpy.data.objects.remove(o)
    meshes = tree_meshes()
    T = json.load(open(WORK + 'p6_trees.json'))['trees']
    for i, t in enumerate(T):
        li = i % 2
        me = meshes[(t['var'], li)]
        o = bpy.data.objects.new(f"CTX_TREE_{i:03d}_{t['var']}", me)      # linked mesh = instance
        col.objects.link(o)
        r, h = t['r'] * FT, t['h'] * FT
        o.location = (t['x'] * FT, t['y'] * FT, -0.10)
        o.rotation_euler = (0, 0, math.radians(t['rot']))
        o.scale = (r, r, h)
        tag(o, dict(sh249_status='context', sh249_phase='context', sh249_type='tree',
                    sh249_note=f"NAIP-derived (2022 60 cm, ExG canopy); crown dia {2*t['r']:.0f} ft, height {t['h']:.0f} ft (assumed from crown)",
                    sh249_source='NAIP-derived', sh249_variant=t['var']))
    return len(T)

res = {}
if STEP in ('buildings', 'all'): res['buildings'] = import_buildings()
if STEP in ('trees', 'all'): res['trees'] = import_trees()
result = res
