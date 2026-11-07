# Phase 5b Blender import: reads work/p5b_proposed_mk_ramps.json.
# Builds Proposed/P_Markings, P_Ramps, P_Signs and the hidden P_RampCutters prisms. Then run p5b_cut_blender.py,
# which cuts the existing raised surfaces at the ramps (Geometry Nodes modifier "P5b_RampCut").
import bpy, json, math, bmesh
from mathutils import Matrix, Vector
FT = 0.3048
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
J = json.load(open(SH249_ROOT + r'work/p5b_proposed_mk_ramps.json'))
prop = bpy.data.collections['Proposed']
def coll(name, parent=prop):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in [x.name for x in parent.children]: parent.children.link(c)
    return c
def mk(name, base, rough=0.5, metal=0.0, emc=None, ems=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = base; b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emc: b.inputs['Emission Color'].default_value = emc; b.inputs['Emission Strength'].default_value = ems
    m.diffuse_color = base; return m
mk('MAT_DetectWarn', (0.85, 0.62, 0.03, 1), 0.6)
mk('MAT_Sign_Red', (0.55, 0.02, 0.02, 1), 0.4)
mk('MAT_RPM_White', (0.9, 0.9, 0.9, 1), 0.3, 0, (1, 1, 1, 1), 0.2)
mk('MAT_RPM_Amber', (0.9, 0.55, 0.02, 1), 0.3, 0, (1, 0.6, 0.05, 1), 0.2)
for d in J['objs']:
    old = bpy.data.objects.get(d['name'])
    if old: bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(d['name']); me.from_pydata(d['v'], [], d['f']); me.update()
    for n in J['mats']: me.materials.append(bpy.data.materials[n])
    for p, i in zip(me.polygons, d['mi']): p.material_index = i
    used = set(d['mi'])
    for i in reversed(range(len(me.materials))):
        if i not in used: me.materials.pop(index=i)
    ob = bpy.data.objects.new(d['name'], me); ob.location = d['loc']; coll(d['coll']).objects.link(ob)
    for k, v in d['props'].items(): ob[k] = v
# text on S6 signs
def add_text(sign, body, centre, face, maxw, maxh, matname):
    cu = bpy.data.curves.new('tmp_txt', 'FONT'); cu.body = body; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    ob = bpy.data.objects.new('tmp_txt', cu); bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.update()
    tm = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    xs = [v.co.x for v in tm.vertices]; ys = [v.co.y for v in tm.vertices]
    sc = min(maxw / (max(xs) - min(xs)), maxh / (max(ys) - min(ys)))
    M = (Matrix.Translation(centre) @ Matrix.Rotation(math.radians(face + 90), 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'X')
         @ Matrix.Scale(sc, 4) @ Matrix.Translation((-(max(xs) + min(xs)) / 2, -(max(ys) + min(ys)) / 2, 0)))
    tm.transform(sign.matrix_world.inverted() @ M)
    me = sign.data; names = [m.name for m in me.materials]
    if matname not in names: me.materials.append(bpy.data.materials[matname]); names.append(matname)
    for p in tm.polygons: p.material_index = names.index(matname)
    bm = bmesh.new(); bm.from_mesh(me); bm.from_mesh(tm); bm.to_mesh(me); bm.free(); me.update()
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.curves.remove(cu); bpy.data.meshes.remove(tm)
bpy.context.view_layer.update()
for t in J['text']:
    s = bpy.data.objects[t['name']]
    for body, c, w, h, mat in t['items']: add_text(s, body, Vector(c), t['face'], w * FT, h * FT, mat)
# ramp cutters
cc = coll('P_RampCutters')
for o in list(cc.objects): bpy.data.objects.remove(o, do_unlink=True)
z0, z1 = 0.045 * FT, 3.0 * FT
for c in J['cutters']:
    bm = bmesh.new(); r = c['ring']
    bot = [bm.verts.new((x, y, z0)) for x, y in r]; top = [bm.verts.new((x, y, z1)) for x, y in r]
    bm.faces.new(bot[::-1]); bm.faces.new(top)
    for i in range(len(r)):
        j = (i + 1) % len(r); bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bm.normal_update(); me = bpy.data.meshes.new(c['name']); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(c['name'], me); cc.objects.link(ob)
    ob.display_type = 'WIRE'; ob.hide_render = True; ob['sh249_status'] = 'helper'
targets = []   # ramp cuts are applied by p5b_cut_blender.py (run it next)
# existing markings are replaced by the proposed marking plan
for n, sh in (('E_MK_White', '38, 39'), ('E_MK_Yellow', '38, 39')):
    ob = bpy.data.objects[n]
    ob['sh249_status'] = 'remove'; ob['sh249_phase'] = 'existing'; ob['sh249_sheet'] = sh; ob['sh249_type'] = 'pavement markings'
    ob['sh249_note'] = 'Existing pavement markings, removed and replaced by the proposed marking plan (sheets 40-41; sheet 23 note 36).'
result = {'objs': len(J['objs']), 'cutters': len(J['cutters']), 'targets': targets}
