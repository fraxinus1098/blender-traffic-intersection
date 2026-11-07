# Phase 5a Blender import (run inside Blender). Reads work/p5_proposed_signals.json, builds Proposed/P_Signals,
# creates MAT_Retro_Yellow and MAT_Radar if missing, then adds sign legends as text meshes (Blender default font).
import bpy, json, math, bmesh
from mathutils import Matrix, Vector
FT = 0.3048
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
J = json.load(open(SH249_ROOT + r'work/p5_proposed_signals.json'))
ONLY = None   # set to a list of object names to rebuild only those
prop = bpy.data.collections['Proposed']
coll = bpy.data.collections.get('P_Signals') or bpy.data.collections.new('P_Signals')
if coll.name not in [c.name for c in prop.children]: prop.children.link(coll)
def mk(name, base, rough=0.5, metal=0.0, emc=None, ems=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = base; b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emc: b.inputs['Emission Color'].default_value = emc; b.inputs['Emission Strength'].default_value = ems
    m.diffuse_color = base; return m
mk('MAT_Retro_Yellow', (0.95, 0.72, 0.02, 1), 0.35, 0, (1.0, 0.8, 0.05, 1), 0.25)
mk('MAT_Radar', (0.80, 0.80, 0.78, 1), 0.45, 0.0)
for d in J['objs']:
    if ONLY and d['name'] not in ONLY: continue
    old = bpy.data.objects.get(d['name'])
    if old: bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(d['name']); me.from_pydata(d['v'], [], d['f']); me.update()
    for n in J['mats']: me.materials.append(bpy.data.materials[n])
    for p, i in zip(me.polygons, d['mi']): p.material_index = i
    used = set(d['mi'])
    for i in reversed(range(len(me.materials))):
        if i not in used: me.materials.pop(index=i)
    ob = bpy.data.objects.new(d['name'], me); ob.location = d['loc']; coll.objects.link(ob)
    for k, v in d['props'].items(): ob[k] = v
def U(a): a = math.radians(a); return Vector((math.cos(a), math.sin(a), 0))
def add_text(sign, body, centre, face, maxw, maxh, matname):
    cu = bpy.data.curves.new('tmp_txt', 'FONT'); cu.body = body; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    ob = bpy.data.objects.new('tmp_txt', cu); bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.update()
    tm = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    xs = [v.co.x for v in tm.vertices]; ys = [v.co.y for v in tm.vertices]
    w = max(xs) - min(xs); h = max(ys) - min(ys); sc = min(maxw / w, maxh / h)
    M = (Matrix.Translation(centre) @ Matrix.Rotation(math.radians(face + 90), 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'X')
         @ Matrix.Scale(sc, 4) @ Matrix.Translation((-(max(xs) + min(xs)) / 2, -(max(ys) + min(ys)) / 2, 0)))
    tm.transform(sign.matrix_world.inverted() @ M)
    me = sign.data; names = [m.name for m in me.materials]
    if matname not in names: me.materials.append(bpy.data.materials[matname]); names.append(matname)
    for p in tm.polygons: p.material_index = names.index(matname)
    bm = bmesh.new(); bm.from_mesh(me); bm.from_mesh(tm); bm.to_mesh(me); bm.free(); me.update()
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.curves.remove(cu); bpy.data.meshes.remove(tm)
for s in J['signs']:
    if ONLY and s['name'] not in ONLY: continue
    sign = bpy.data.objects[s['name']]; f = U(s['face']); c = Vector(s['c']); rgt = U(s['face'] + 90)
    if s['sid'] in ('S1', 'S2'):
        add_text(sign, 'Spring Cypress Rd' if s['sid'] == 'S1' else 'SH 249', c + f * (s['t'] / 2 + 0.021) * FT, s['face'],
                 (7.0 if s['sid'] == 'S1' else 3.4) * FT, 0.72 * FT, 'MAT_Sign_White')
    elif s['sid'] in ('S3', 'S4'):
        sgn = -1 if s['sid'] == 'S3' else 1
        add_text(sign, 'ONE WAY', c + f * 0.064 * FT + rgt * (-0.25 * sgn) * FT, s['face'], 1.75 * FT, 0.36 * FT, 'MAT_Sign_Black')
    else:
        add_text(sign, 'ONLY', c + f * 0.012 * FT, s['face'], 0.75 * FT, 0.28 * FT, 'MAT_Sign_Black')
result = {'objects': len(coll.objects)}
