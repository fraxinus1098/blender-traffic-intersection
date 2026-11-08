"""Phase 9A.4 (Blender, clean model v11): a few static low-poly cars at the stop bars, for scale.
Run inside Blender:  exec(open(r'<repo>/work/p9_vehicles_blender.py').read())
Collection Context/CTX_Vehicles (toggled with the context layer). One car per lane at each approach's proposed stop
bar (work/p7_data.json), front bumper 4 ft behind the bar, except lane 2 from the left, where the Phase 7 driver
cameras stand. Three body types x four paints, as shared meshes (instanced in the GLB). Illustrative only: no traffic
data. Re-running replaces CTX_VEH_* objects."""
import bpy, bmesh, json, math, random
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
FT = 0.3048

def mat(name, rgb, rough=0.45, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; m.diffuse_color = (*rgb, 1)
    return m
PAINT = {'White': mat('MAT_CTX_Car_White', (0.80, 0.80, 0.78), 0.35, 0.1),
         'Silver': mat('MAT_CTX_Car_Silver', (0.45, 0.46, 0.47), 0.35, 0.5),
         'Red': mat('MAT_CTX_Car_Red', (0.45, 0.03, 0.03), 0.35, 0.2),
         'Blue': mat('MAT_CTX_Car_Blue', (0.04, 0.07, 0.18), 0.35, 0.3)}
GLASS = mat('MAT_CTX_Car_Glass', (0.03, 0.04, 0.05), 0.08)
TYRE = mat('MAT_CTX_Car_Tyre', (0.025, 0.025, 0.025), 0.8)

# side profiles (x forward, z up, ft): body, greenhouse; length, width, wheel radius
TYPES = {
    'Sedan': ([(-7.75, 0.9), (7.6, 0.9), (7.75, 1.6), (7.5, 2.6), (3.2, 2.9), (-6.0, 3.0), (-7.6, 2.8), (-7.75, 1.6)],
              [(2.8, 2.9), (0.6, 4.45), (-3.8, 4.55), (-5.9, 3.0)], 15.5, 6.0, 1.05),
    'SUV': ([(-8.0, 1.1), (7.8, 1.1), (8.0, 1.9), (7.7, 3.2), (4.2, 3.5), (-7.8, 3.6), (-8.0, 2.0)],
            [(3.9, 3.5), (2.0, 5.6), (-7.4, 5.7), (-7.8, 3.6)], 16.0, 6.4, 1.25),
    'Pickup': ([(-9.5, 1.2), (9.3, 1.2), (9.5, 2.1), (9.2, 3.5), (5.2, 3.8), (-9.5, 3.9), (-9.5, 2.0)],
               [(4.7, 3.8), (3.0, 6.0), (-1.6, 6.1), (-2.3, 3.85)], 19.0, 6.6, 1.25),
}

def extrude(bm, prof, hw, mi):
    n = len(prof)
    a = [bm.verts.new((x * FT, -hw * FT, z * FT)) for x, z in prof]
    b = [bm.verts.new((x * FT, hw * FT, z * FT)) for x, z in prof]
    fs = [bm.faces.new(a[::-1]), bm.faces.new(b)]
    for i in range(n):
        j = (i + 1) % n; fs.append(bm.faces.new([a[i], a[j], b[j], b[i]]))
    for f in fs: f.material_index = mi

def car_mesh(typ, paint):
    name = f'CTX_VehMesh_{typ}_{paint}'
    old = bpy.data.meshes.get(name)
    if old: old.name = name + '_old'
    body, cab, L, W, rw = TYPES[typ]
    bm = bmesh.new()
    extrude(bm, body, W / 2, 0)
    extrude(bm, cab, W / 2 - 0.35, 1)
    for sx in (1, -1):
        for sy in (1, -1):
            r = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=rw * FT, radius2=rw * FT, depth=0.75 * FT)
            bmesh.ops.rotate(bm, verts=r['verts'], cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(math.pi / 2, 3, 'X'))
            bmesh.ops.translate(bm, verts=r['verts'], vec=(sx * (L / 2 - 2.7) * FT, sy * (W / 2 - 0.45) * FT, rw * FT))
            for f in {f for v in r['verts'] for f in v.link_faces}: f.material_index = 2
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in (PAINT[paint], GLASS, TYRE): me.materials.append(m)
    return me

ctx = bpy.data.collections['Context']
col = bpy.data.collections.get('CTX_Vehicles')
if col is None:
    col = bpy.data.collections.new('CTX_Vehicles'); ctx.children.link(col)
for o in list(col.objects): bpy.data.objects.remove(o)
for m in list(bpy.data.meshes):
    if m.name.startswith('CTX_VehMesh_') and m.users == 0: bpy.data.meshes.remove(m)
meshes = {}
D = json.load(open(SH249_ROOT + 'work/p7_data.json'))
rnd = random.Random(249)
k = 0
for ap in D['approaches']:
    tu = (math.cos(math.radians(ap['travel_deg'])), math.sin(math.radians(ap['travel_deg'])))
    for li, lane in enumerate(ap['lanes']):
        if li == 1: continue                                   # driver-camera lane
        typ = rnd.choice(['Sedan', 'Sedan', 'SUV', 'SUV', 'Pickup']); paint = rnd.choice(list(PAINT))
        if (typ, paint) not in meshes: meshes[(typ, paint)] = car_mesh(typ, paint)
        L = TYPES[typ][2]
        bx, by = lane['bar_edge']
        cx, cy = bx - tu[0] * (4 + L / 2), by - tu[1] * (4 + L / 2)
        o = bpy.data.objects.new(f"CTX_VEH_{k:02d}_{ap['key']}_L{li + 1}", meshes[(typ, paint)])
        col.objects.link(o)
        o.location = (cx * FT, cy * FT, 0.0)
        o.rotation_euler = (0, 0, math.radians(ap['travel_deg']))
        for kk, v in dict(sh249_status='context', sh249_phase='context', sh249_type='vehicle',
                          sh249_note=f"Illustrative static vehicle for scale ({typ.lower()}), waiting at the {ap['dir']} stop bar of the {ap['inter']} intersection, lane {li + 1} from the left. Not traffic data.",
                          sh249_source='illustrative').items():
            o[kk] = v
        k += 1
for m in list(bpy.data.meshes):
    if m.name.startswith('CTX_VehMesh_') and m.name.endswith('_old') and m.users == 0: bpy.data.meshes.remove(m)
result = {'cars': k, 'meshes': sorted(m.name for m in meshes.values())}
