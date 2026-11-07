"""Phase 6 (Blender): GLB-safe surface materials.
Each textured material = UV Map(rastUVmap) -> Mapping(POINT, scale) -> Image Texture -> Principled Base Color.
The glTF exporter writes the Mapping scale as KHR_texture_transform, so tiles survive Phase 8.
rastUVmap spans the aerial (1233.77 x 826.63 m), so scale = (1233.77/T, 826.63/T) for a T-metre tile.
Also adds a rastUVmap UV layer (same affine as the aerial) to the marking meshes, which had none.
Run: exec(open(r'<repo>/work/p6_materials_blender.py').read())"""
import bpy
TEX = '//../work/tex/'
AW, AH = 1233.7716064453125, 826.626953125
# rastUVmap affine (fitted on E_RD_Pavement, max error 4e-8): u = a.x + b.y + c, v = d.x + e.y + f  (metres)
UVA = ((0.0008094363534843712, 0.00004195044502427331, 0.4952358567880078),
       (-0.0000626126332451867, 0.001208113986723311, 0.49743842059422216))

SPEC = {  # material: (texture, tile metres, roughness, specular level)
    'MAT_Asphalt':         ('p6_asphalt.jpg', 8.0, 0.92, 0.35),
    'MAT_Curb':            ('p6_concrete_curb.jpg', 3.0, 0.85, 0.4),
    'MAT_Sidewalk':        ('p6_sidewalk.jpg', 3.0, 0.85, 0.4),
    'MAT_Island_Concrete': ('p6_island_conc.jpg', 3.0, 0.88, 0.4),
    'MAT_Grass':           ('p6_grass.jpg', 4.0, 0.95, 0.2),
    'MAT_Paint_White':     ('p6_paint_white.jpg', 1.5, 0.55, 0.5),
    'MAT_Paint_Yellow':    ('p6_paint_yellow.jpg', 1.5, 0.55, 0.5),
}
PLAIN = {}  # MAT_Concrete, bridge, embankment, detectable warning left at their Phase 3-5 values

def textured(name, img, T, rough, spec):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes
    bsdf = N.get('Principled BSDF')
    for n in list(N):
        if n.name in ('P6_UV', 'P6_Map', 'P6_Tex'): N.remove(n)
    uv = N.new('ShaderNodeUVMap'); uv.name = 'P6_UV'; uv.uv_map = 'rastUVmap'; uv.location = (-900, 300)
    mp = N.new('ShaderNodeMapping'); mp.name = 'P6_Map'; mp.vector_type = 'POINT'; mp.location = (-700, 300)
    mp.inputs['Scale'].default_value = (AW / T, AH / T, 1.0)
    tx = N.new('ShaderNodeTexImage'); tx.name = 'P6_Tex'; tx.location = (-450, 300)
    im = bpy.data.images.load(TEX + img, check_existing=True)
    tx.image = im; tx.interpolation = 'Linear'; tx.extension = 'REPEAT'
    nt.links.new(uv.outputs['UV'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], tx.inputs['Vector'])
    nt.links.new(tx.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Specular IOR Level'].default_value = spec
    return m

def add_rast_uv(o):
    me = o.data
    if 'rastUVmap' in me.uv_layers: return False
    uvl = me.uv_layers.new(name='rastUVmap')
    mw = o.matrix_world
    (a, b, c), (d, e, f) = UVA
    for l in me.loops:
        v = mw @ me.vertices[l.vertex_index].co
        uvl.data[l.index].uv = (a * v.x + b * v.y + c, d * v.x + e * v.y + f)
    return True

res = {'textured': [], 'uv_added': [], 'plain': []}
for o in ('E_MK_White', 'E_MK_Yellow', 'P_MK_White', 'P_MK_Yellow'):
    if add_rast_uv(bpy.data.objects[o]): res['uv_added'].append(o)
for name, (img, T, r, s) in SPEC.items():
    textured(name, img, T, r, s); res['textured'].append(name)
# curb gets its own textured material (MAT_Concrete stays plain for the UV-less foundations/ramps)
curb = bpy.data.objects['E_RD_Curb']
curb.material_slots[0].material = bpy.data.materials['MAT_Curb']
for name, (rgb, r) in PLAIN.items():
    b = bpy.data.materials[name].node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = r
    res['plain'].append(name)
viewport = {'MAT_Asphalt': (0.05, 0.05, 0.055), 'MAT_Curb': (0.39, 0.38, 0.35), 'MAT_Sidewalk': (0.46, 0.44, 0.41),
            'MAT_Island_Concrete': (0.30, 0.29, 0.27), 'MAT_Grass': (0.06, 0.12, 0.03)}
for k, v in viewport.items(): bpy.data.materials[k].diffuse_color = (*v, 1)
result = res
