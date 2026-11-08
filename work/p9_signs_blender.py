"""Phase 9A.4 (Blender, clean model v11): legends on the six existing street-name signs (inside the E_MA_* meshes).
Run inside Blender:  exec(open(r'<repo>/work/p9_signs_blender.py').read())
Each sign panel (a MAT_Sign_Green island in the arm mesh) faces the same way as its arm's heads (Phase 4). Panels
facing Spring Cypress traffic (EB/WB) read the cross street "SH 249" (the Nov 2026 photo shows "SH 249" on the K arm
seen from WB); panels facing frontage-road traffic (NB/SB) read "Spring Cypress Rd". White text, Blender's default
font, same method as p5_import_blender.py. Skips arms that already have legends (sh249_sign_legends)."""
import bpy, bmesh, math
from mathutils import Vector, Matrix
FT = 0.3048
# arm object -> list of (approx. panel centre ft, facing unit vector (x, y), legend)
SIGNS = {
    'E_MA_C_Dual55x32ft': [((-212.6, 1.3), (1, 0), 'SH 249'), ((-192.3, -8.9), (-0.37, 0.93), 'Spring Cypress Rd')],
    'E_MA_E_44ft': [((-100.3, -51.6), (-1, 0), 'SH 249')],
    'E_MA_H_Dual55x32ft': [((235.5, 3.6), (0.5, -0.87), 'Spring Cypress Rd'), ((254.0, -2.5), (-1, 0), 'SH 249')],
    'E_MA_K_44ft': [((146.1, 49.3), (1, 0), 'SH 249')],
}

def add_text(obj, body, centre, face_deg, maxw, maxh, matname):
    """as p5_import_blender.add_text: text mesh standing on the sign face, merged into obj's mesh"""
    cu = bpy.data.curves.new('tmp_txt', 'FONT'); cu.body = body; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    ob = bpy.data.objects.new('tmp_txt', cu); bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.update()
    tm = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    xs = [v.co.x for v in tm.vertices]; ys = [v.co.y for v in tm.vertices]
    w = max(xs) - min(xs); h = max(ys) - min(ys); sc = min(maxw / w, maxh / h)
    M = (Matrix.Translation(centre) @ Matrix.Rotation(math.radians(face_deg + 90), 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'X')
         @ Matrix.Scale(sc, 4) @ Matrix.Translation((-(max(xs) + min(xs)) / 2, -(max(ys) + min(ys)) / 2, 0)))
    tm.transform(obj.matrix_world.inverted() @ M)
    me = obj.data; names = [m.name for m in me.materials]
    if matname not in names: me.materials.append(bpy.data.materials[matname]); names.append(matname)
    for p in tm.polygons: p.material_index = names.index(matname)
    bm = bmesh.new(); bm.from_mesh(me); bm.from_mesh(tm); bm.to_mesh(me); bm.free(); me.update()
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.curves.remove(cu); bpy.data.meshes.remove(tm)
    return sc

res = {}
for name, signs in SIGNS.items():
    o = bpy.data.objects[name]
    if 'sh249_sign_legends' in o.keys(): res[name] = 'skipped (done)'; continue
    names = [s.material.name if s.material else '' for s in o.material_slots]
    gi = names.index('MAT_Sign_Green'); mw = o.matrix_world
    gverts = [mw @ v.co for p in o.data.polygons if p.material_index == gi for v in (o.data.vertices[i] for i in p.vertices)]
    done = []
    for (cx, cy), (fx, fy), body in signs:
        f = Vector((fx, fy, 0)).normalized()
        near = [v for v in gverts if math.hypot(v.x / FT - cx, v.y / FT - cy) < 4.5]
        c = sum(near, Vector()) / len(near)
        t = max(v.dot(f) for v in near) - min(v.dot(f) for v in near)              # panel thickness (m)
        rgt = Vector((-f.y, f.x, 0))
        width = max(v.dot(rgt) for v in near) - min(v.dot(rgt) for v in near)
        face = math.degrees(math.atan2(f.y, f.x))
        add_text(o, body, c + f * (t / 2 + 0.021 * FT), face, width - 0.9 * FT, 0.72 * FT, 'MAT_Sign_White')
        done.append(f"{body} (faces {face:.0f} deg)")
    o['sh249_sign_legends'] = '; '.join(done)
    res[name] = done
result = res
