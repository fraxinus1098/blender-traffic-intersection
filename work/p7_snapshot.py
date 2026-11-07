"""Phase 7 integrity check (Blender). MODE='save' writes a fingerprint of every E_/P_/CTX_ object,
every material and node group to work/p7_baseline_v08.json; MODE='compare' diffs the current scene against it.
Fingerprint: mesh data (verts/faces), matrix_world, material slots, custom props, modifiers (+ GN inputs),
visibility flags, collections; materials and node groups by node/link/default-value dump."""
import bpy, json, hashlib, numpy as np
MODE = globals().get('MODE', 'compare')
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
PATH = SH249_ROOT + r'work/p7_baseline_v08.json'
PFX = ('E_', 'P_', 'CTX_')
def h(x): return hashlib.md5(repr(x).encode()).hexdigest()
def val(v):
    if isinstance(v, (int, str, bool)) or v is None: return v
    try: return [round(float(a), 6) for a in v]
    except (TypeError, ValueError): pass
    if isinstance(v, float): return round(v, 6)
    if isinstance(v, (int, str, bool)) or v is None: return v
    return getattr(v, 'name', str(type(v)))
def mkeys(m):
    try: return sorted((k, str(m[k])) for k in m.keys())
    except TypeError: return None
def obj_fp(o):
    d = {'type': o.type, 'mw': h([round(a, 5) for r in o.matrix_world for a in r]),
         'parent': o.parent.name if o.parent else None,
         'mats': [s.material.name if s.material else None for s in o.material_slots],
         'props': h(sorted((k, str(o[k])) for k in o.keys())),
         'mods': h([(m.name, m.type, m.show_viewport, m.show_render,
                     mkeys(m),
                     getattr(m, 'node_group', None) and m.node_group.name) for m in o.modifiers]),
         'vis': [o.hide_viewport, o.hide_render, o.hide_get(), o.hide_select],
         'cols': sorted(c.name for c in o.users_collection), 'data': o.data.name if o.data else None}
    if o.type == 'MESH':
        me = o.data; v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v)
        p = np.empty(len(me.polygons) * 1, dtype=np.int32)
        lv = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get('vertex_index', lv)
        d['geo'] = [len(me.vertices), len(me.polygons), hashlib.md5(np.round(v, 5).tobytes()).hexdigest(),
                    hashlib.md5(lv.tobytes()).hexdigest(), sorted(me.uv_layers.keys())]
    elif o.type in ('FONT', 'CURVE'):
        d['geo'] = h([getattr(o.data, 'body', ''), o.data.size if hasattr(o.data, 'size') else 0])
    return d
def nt_fp(nt):
    if nt is None: return None
    nodes = []
    for n in sorted(nt.nodes, key=lambda n: n.name):
        ins = [(i.identifier, val(i.default_value)) for i in n.inputs if hasattr(i, 'default_value')]
        extra = getattr(n, 'image', None); extra = extra.filepath if extra else None
        nodes.append((n.name, n.bl_idname, ins, extra, getattr(n, 'node_tree', None) and n.node_tree.name))
    links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in nt.links)
    return h([nodes, links])
fp = {'objects': {o.name: obj_fp(o) for o in bpy.data.objects if o.name.startswith(PFX)},
      'materials': {m.name: [nt_fp(m.node_tree), val(m.diffuse_color)] for m in bpy.data.materials},
      'node_groups': {g.name: nt_fp(g) for g in bpy.data.node_groups}}
if MODE == 'save':
    json.dump(fp, open(PATH, 'w'), indent=0)
    result = {'saved': PATH, 'objects': len(fp['objects']), 'materials': len(fp['materials']), 'node_groups': len(fp['node_groups'])}
else:
    base = json.load(open(PATH)); diffs = []
    for k in ('objects', 'materials', 'node_groups'):
        for n, b in base[k].items():
            if n not in fp[k]: diffs.append((k, n, 'MISSING')); continue
            cur = json.loads(json.dumps(fp[k][n]))
            if cur != b:
                if isinstance(b, dict): diffs.append((k, n, [f for f in b if cur.get(f) != b[f]]))
                else: diffs.append((k, n, 'changed'))
        new = [n for n in fp[k] if n not in base[k]]
        if new: diffs.append((k, 'NEW', new[:60] + (['...%d' % len(new)] if len(new) > 60 else [])))
    result = {'n_checked': {k: len(base[k]) for k in base}, 'diffs': diffs}
