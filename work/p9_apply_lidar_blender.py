"""Phase 9A.1 (Blender, clean model v11): apply the lidar heights from work/p9_lidar.json.
Run inside Blender:  STEP = 'buildings' | 'trees' | 'bridge';  exec(open(r'<repo>/work/p9_apply_lidar_blender.py').read())
- buildings: CTX_BLDG_* roofs moved to the measured median roof height (canopy: slab top to the measured top,
  2-ft slab and columns follow); sh249_height_ft / sh249_note / sh249_source updated. Footprints unchanged.
- trees: every CTX_TREE_* replaced by the lidar trees, linking the existing CTX_TreeMesh_<var>_<A|B> meshes
  (same instancing, materials and collection as Phase 6).
- bridge: the four CTX_SH249_* objects re-levelled to the measured deck top over Spring Cypress (structure depth
  6 ft, rail 2.67 ft kept). Uniform height; 9A.2 rebuilds the bridge to follow the full profile.
Idempotent: heights are set from the JSON, not added."""
import bpy, json, math
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
assert bpy.data.filepath.endswith('v11.blend'), 'apply only to the v11 clean model'
FT = 0.3048
ZG = -0.10
STEP = globals().get('STEP')
D = json.load(open(SH249_ROOT + 'work/p9_lidar.json'))
SRC = 'USGS 3DEP lidar TX_Houston_B24 (2024 flight)'

def set_z(me, f):
    co = [0.0] * (len(me.vertices) * 3); me.vertices.foreach_get('co', co)
    for i in range(2, len(co), 3): co[i] = f(co[i])
    me.vertices.foreach_set('co', co); me.update()

def buildings():
    rec = {str(r['osm_id']): r for r in D['buildings']}
    done = []
    for o in bpy.data.collections['CTX_Buildings'].objects:
        r = rec.get(str(o.get('sh249_osm_id')))
        if r is None: continue
        old = float(o['sh249_height_ft'])
        base_note = o['sh249_note'].split('; height')[0]
        if r['height_ft'] is None:
            o['sh249_note'] = f"{base_note}; height {old:.0f} ft, assumed by type (no lidar roof returns in 2024)"
            done.append((o.name, old, None)); continue
        h = r['height_ft']
        if o['sh249_type'] == 'building_canopy':
            # slab 15-17 ft + columns from the ground: lift everything above ground by (h - 17 ft)
            top_old = max(v.co.z for v in o.data.vertices)
            dz = h * FT - top_old
            set_z(o.data, lambda z: z + dz if z > ZG + 1e-3 else z)
            note = f"{base_note}; canopy top {h:.0f} ft (lidar median; 2-ft slab), was {old:.0f} ft assumed"
        else:
            top_old = max(v.co.z for v in o.data.vertices)
            set_z(o.data, lambda z: h * FT if z > top_old - 1e-3 else z)
            note = f"{base_note}; height {h:.0f} ft, lidar median roof (p90 {r['p90_ft']:.0f} ft), was {old:.0f} ft assumed"
        o['sh249_height_ft'] = round(h, 1)
        o['sh249_note'] = note
        o['sh249_source'] = f"OSM way {r['osm_id']}; height: {SRC}"
        done.append((o.name, old, h))
    return done

def trees():
    col = bpy.data.collections['CTX_Trees']
    for o in list(col.objects):
        if o.name.startswith('CTX_TREE_'): bpy.data.objects.remove(o)
    T = D['trees']['trees']
    # any tree mesh as a placeholder; p9_trees_blender.py (run at the end) links the shape variants
    me0 = next(m for m in bpy.data.meshes if m.name.startswith('CTX_TreeMesh_'))
    for i, t in enumerate(T):
        me = bpy.data.meshes.get(f"CTX_TreeMesh_{t['var']}_{'AB'[i % 2]}") or me0
        o = bpy.data.objects.new(f"CTX_TREE_{i:03d}_{t['var']}", me)
        col.objects.link(o)
        o.location = (t['x'] * FT, t['y'] * FT, ZG)
        o.rotation_euler = (0, 0, math.radians(t['rot']))
        o.scale = (t['r'] * FT, t['r'] * FT, t['h'] * FT)
        for k, v in dict(sh249_status='context', sh249_phase='context', sh249_type='tree',
                         sh249_note=f"Lidar tree ({SRC}): crown dia {2 * t['r']:.0f} ft, height {t['h']:.0f} ft (measured)",
                         sh249_source='lidar-derived (USGS 3DEP 2024)', sh249_variant=t['var']).items():
            o[k] = v
    if 'CTX_TreeMesh_Pine' in bpy.data.meshes:          # 9A.4 shape variants exist: relink them
        exec(open(SH249_ROOT + 'work/p9_trees_blender.py').read(), {'bpy': bpy})
    return len(T)

def bridge():
    T = D['bridge']['deck_top_over_spring_cypress_ft']
    DEPTH, Z_LOW = 6.0, 0.5
    def fwd(z, top):                 # Phase 3 z (deck top 24, soffit 18 ft) -> z for a deck top `top`
        zf, sof = z / FT, top - DEPTH
        if zf <= 18.0 + 1e-3: return (Z_LOW + (zf - Z_LOW) * (sof - Z_LOW) / (18.0 - Z_LOW)) * FT
        return (zf + top - 24.0) * FT
    def inv(z, top):                 # inverse of fwd
        zf, sof = z / FT, top - DEPTH
        if zf <= sof + 1e-3: return (Z_LOW + (zf - Z_LOW) * (18.0 - Z_LOW) / (sof - Z_LOW)) * FT
        return (zf - top + 24.0) * FT
    sof = T - DEPTH
    for n in ('CTX_SH249_Deck', 'CTX_SH249_Rails', 'CTX_SH249_Embankment', 'CTX_SH249_Bents'):
        o = bpy.data.objects[n]
        prev = float(o.get('sh249_deck_top_ft', 24.0))      # height currently applied (Phase 3: 24 ft)
        set_z(o.data, lambda z: fwd(inv(z, prev), T))
        o['sh249_deck_top_ft'] = round(T, 2)
        o['sh249_note'] = (f"Context (illustrative): deck edges from sheets 38-39; deck top {T:.1f} ft above Spring Cypress "
                           f"({SRC}), soffit {sof:.1f} ft assumed (6-ft structure depth); bent positions illustrative")
        o['sh249_source'] = f"plan-derived (sheets 38-39); deck height: {SRC}"
    return dict(deck_top_ft=T, soffit_ft=sof)

result = {'step': STEP, 'out': {'buildings': buildings, 'trees': trees, 'bridge': bridge}[STEP]()}
