# Phase 5b ramp cuts (run in Blender after p5b_import_blender.py).
# The Exact Boolean can't classify open single-sided surfaces, so instead:
# 1) split the raised surfaces along each cutter edge (bmesh bisect, topology only - looks identical),
# 2) add a Geometry Nodes modifier "P5b_RampCut" that deletes faces whose centre sits under a cutter prism
#    (raycast straight up into collection P_RampCutters). Toggle the modifier to see the uncut existing surfaces.
import bpy, bmesh
from mathutils import Vector
cc = bpy.data.collections['P_RampCutters']
for c in cc.objects:            # cutters must be evaluated: hide with the eye toggle, not "disable in viewports"
    c.hide_viewport = False; c.hide_render = True; c.display_type = 'WIRE'
    try: c.hide_set(True)
    except Exception: pass
rings = []
for c in cc.objects:
    vs = [c.matrix_world @ v.co for v in c.data.vertices]; n = len(vs) // 2
    rings.append([Vector((v.x, v.y, 0)) for v in vs[:n]])
targets = ['E_RD_Curb', 'E_RD_Roadside', 'E_RD_Sidewalk_assumed'] + [o.name for o in bpy.data.collections['E_Roadway'].objects if o.name.startswith('E_ISL_')]
ng = bpy.data.node_groups.get('P5b_RampCut')
if not ng:
    ng = bpy.data.node_groups.new('P5b_RampCut', 'GeometryNodeTree')
    ng.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; L = ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    ci = N.new('GeometryNodeCollectionInfo'); ci.transform_space = 'RELATIVE'; ci.inputs['Collection'].default_value = cc
    ri = N.new('GeometryNodeRealizeInstances')
    rc = N.new('GeometryNodeRaycast'); rc.inputs['Ray Direction'].default_value = (0, 0, 1); rc.inputs['Ray Length'].default_value = 10.0
    dl = N.new('GeometryNodeDeleteGeometry'); dl.domain = 'FACE'
    L.new(ci.outputs[0], ri.inputs[0]); L.new(ri.outputs[0], rc.inputs['Target Geometry'])
    L.new(gi.outputs[0], dl.inputs['Geometry']); L.new(rc.outputs['Is Hit'], dl.inputs['Selection']); L.new(dl.outputs[0], go.inputs[0])
stats = {}
for n in targets:
    ob = bpy.data.objects[n]
    for m in [m for m in ob.modifiers if m.name == 'P5b_RampCut']: ob.modifiers.remove(m)
    if not ob.get('sh249_p5b_split'):
        mwi = ob.matrix_world.inverted(); bm = bmesh.new(); bm.from_mesh(ob.data)
        for ring in rings:
            lr = [mwi @ p for p in ring]
            xs = [p.x for p in lr]; ys = [p.y for p in lr]
            x0, x1, y0, y1 = min(xs) - 0.6, max(xs) + 0.6, min(ys) - 0.6, max(ys) + 0.6
            for i in range(len(lr)):
                a, b = lr[i], lr[(i + 1) % len(lr)]
                d = b - a; no = Vector((-d.y, d.x, 0)).normalized()
                faces = [f for f in bm.faces if any(x0 <= v.co.x <= x1 and y0 <= v.co.y <= y1 for v in f.verts)]
                if not faces: continue
                edges = list({e for f in faces for e in f.edges}); verts = list({v for f in faces for v in f.verts})
                bmesh.ops.bisect_plane(bm, geom=faces + edges + verts, plane_co=a, plane_no=no)
        bm.to_mesh(ob.data); bm.free(); ob.data.update(); ob['sh249_p5b_split'] = 1
    md = ob.modifiers.new('P5b_RampCut', 'NODES'); md.node_group = ng
    stats[n] = len(ob.data.polygons)
result = {'targets': stats}
