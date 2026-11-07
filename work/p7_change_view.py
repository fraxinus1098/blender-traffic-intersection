"""Phase 7 (Blender): change view. MODE='apply' tints objects by sh249_status (remove = red, new = green) by swapping
TINTED COPIES of their materials into object-level slots; shared materials are never edited. remain / context / untagged
stay neutral. The original slot state (link + object-level material) is stored in the scene property
SH249_p7_cv_state, so MODE='restore' puts everything back exactly (and, with PURGE=True, deletes the *__CV_* copies).
Render the change view with p7_render_blender.py (VIEW='change'), which applies and restores around the renders."""
import bpy, json
MODE = globals().get('MODE', 'apply'); PURGE = globals().get('PURGE', True)
KEY = 'SH249_p7_cv_state'
TINT = {'remove': (0.85, 0.06, 0.05), 'new': (0.10, 0.72, 0.14)}
FAC = 0.6
sc = bpy.context.scene

def tinted(mat, status):
    name = '%s__CV_%s' % (mat.name if mat else 'NONE', status)
    m = bpy.data.materials.get(name)
    if m: return m
    rgb = TINT[status]
    if mat is None:
        m = bpy.data.materials.new(name); m.use_nodes = True
    else:
        m = mat.copy(); m.name = name
    m['sh249_cv_copy'] = status
    nt = m.node_tree
    outn = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output), None) \
        or next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
    src = outn.inputs['Surface'].links[0].from_socket if outn.inputs['Surface'].links else None
    p = nt.nodes.new('ShaderNodeBsdfPrincipled'); p.name = 'CV_Tint'
    p.inputs['Base Color'].default_value = (*rgb, 1); p.inputs['Roughness'].default_value = 0.5
    p.inputs['Emission Color'].default_value = (*rgb, 1); p.inputs['Emission Strength'].default_value = 0.25
    if src is None:
        nt.links.new(p.outputs['BSDF'], outn.inputs['Surface'])
    else:
        mx = nt.nodes.new('ShaderNodeMixShader'); mx.name = 'CV_Mix'; mx.inputs[0].default_value = FAC
        nt.links.new(src, mx.inputs[1]); nt.links.new(p.outputs['BSDF'], mx.inputs[2]); nt.links.new(mx.outputs[0], outn.inputs['Surface'])
    m.diffuse_color = (*rgb, 1)
    return m

def targets():
    for o in bpy.data.objects:
        st = o.get('sh249_status')
        if st not in TINT or not o.name.startswith(('E_', 'P_')): continue
        if any(c.name == 'P_RampCutters' for c in o.users_collection): continue
        if not hasattr(o.data, 'materials'): continue
        yield o, st

if MODE == 'apply':
    if KEY in sc: raise RuntimeError('change view already applied; run MODE="restore" first')
    state = []; n = 0
    for o, st in targets():
        if len(o.material_slots) == 0:
            o.data.materials.append(None); state.append([o.name, -1, 'ADDED', None])  # (not expected; recorded for restore)
        for i, s in enumerate(o.material_slots):
            objmat = None
            if s.link == 'OBJECT': objmat = s.material.name if s.material else None
            if state and state[-1][1] == -1 and state[-1][0] == o.name: pass
            state.append([o.name, i, s.link, objmat])
            eff = s.material
            s.link = 'OBJECT'; s.material = tinted(eff, st); n += 1
    sc[KEY] = json.dumps(state)
    result = {'applied_slots': n, 'objects': len({s[0] for s in state}),
              'copies': sorted(m.name for m in bpy.data.materials if m.get('sh249_cv_copy'))[:80]}
else:
    if KEY not in sc: result = {'restore': 'nothing to restore'}
    else:
        state = json.loads(sc[KEY]); added = set()
        for name, i, link, objmat in state:
            o = bpy.data.objects.get(name)
            if o is None: continue
            if i == -1: added.add(name); continue
            s = o.material_slots[i]
            s.link = 'OBJECT'; s.material = bpy.data.materials.get(objmat) if objmat else None
            s.link = link
        for name in added:
            o = bpy.data.objects[name]; o.data.materials.pop(index=len(o.data.materials) - 1)
        del sc[KEY]
        purged = 0
        if PURGE:
            for m in [m for m in bpy.data.materials if m.get('sh249_cv_copy')]:
                bpy.data.materials.remove(m); purged += 1
        result = {'restored_slots': len(state), 'purged_copies': purged}
