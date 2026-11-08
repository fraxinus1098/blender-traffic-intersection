"""Phase 9A.4 (Blender, clean model v11): MAT_Aerial_NAIP uses work/tex/p9_aerial_fade.jpg (edges faded to the
ground-haze colour, from p9_aerial_fade.py) instead of the GeoTIFF, so the aerial no longer ends in a hard line.
Run inside Blender:  exec(open(r'<repo>/work/p9_horizon_blender.py').read())   (re-runnable)"""
import bpy
import os as _os, bpy as _bpy  # repo root = folder above blend/ (override with SH249_ROOT)
SH249_ROOT = globals().get('SH249_ROOT') or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)).replace('\\', '/') + '/'
assert bpy.data.filepath.endswith('v11.blend'), 'apply only to the v11 clean model'
m = bpy.data.materials['MAT_Aerial_NAIP']
tex = [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE']
assert len(tex) == 1, [n.name for n in tex]
path = SH249_ROOT + 'work/tex/p9_aerial_fade.jpg'
img = bpy.data.images.get('p9_aerial_fade.jpg') or bpy.data.images.load(path)
img.filepath = bpy.path.relpath(path); img.reload()
old = tex[0].image
tex[0].image = img
result = {'was': old.name if old else None, 'now': img.name, 'path': img.filepath}
