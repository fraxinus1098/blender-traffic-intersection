"""Phase 6 (Blender): Eevee lighting for a clear Houston mid-morning.
Sun: 2026-04-15 10:00 CDT at ORIGIN_SC (30.01308 N, 95.59066 W): elevation 38.9 deg, true azimuth 102.1 deg
(scene azimuth 100.5 deg from +Y, since scene +Y bears 1.67 deg). Computed by work/p6_sun.py (NOAA).
World: clear-sky colour gradient (horizon pale blue to zenith blue; ground haze below the horizon).
Hosek-Wilkie was tried but renders very dim in Eevee here. SUN_Main supplies direct light.
Run: exec(open(r'<repo>/work/p6_light_blender.py').read())"""
import bpy, math
from mathutils import Vector
TO_SUN = Vector((0.7655, -0.1414, 0.6277)).normalized()
SUN_ENERGY = globals().get('SUN_ENERGY', 3.4)          # W/m^2 (Standard view transform)
SKY_STRENGTH = globals().get('SKY_STRENGTH', 0.9)
SUN_ANGLE_DEG = 1.2                                     # angular diameter -> soft shadow penumbra
sc = bpy.context.scene

sun = bpy.data.objects['SUN_Main']
sun.rotation_mode = 'XYZ'
sun.rotation_euler = TO_SUN.to_track_quat('Z', 'Y').to_euler()   # light shines along -Z
L = sun.data
L.energy = SUN_ENERGY
L.color = (1.0, 0.965, 0.91)                            # slightly warm mid-morning sun
L.angle = math.radians(SUN_ANGLE_DEG)
L.use_shadow = True
if hasattr(L, 'shadow_maximum_resolution'): L.shadow_maximum_resolution = 0.001
if hasattr(L, 'use_shadow_jitter'): L.use_shadow_jitter = True
sun['sh249_note'] = 'Sun for 2026-04-15 10:00 CDT: elev 38.9 deg, true az 102.1 deg (p6_sun.py)'

w = sc.world; nt = w.node_tree; N = nt.nodes
bg = N['Background']
for n in list(N):
    if n.name.startswith('P6_'): N.remove(n)
# clear-sky gradient on view direction z: ground haze below the horizon, pale horizon, blue zenith
tc = N.new('ShaderNodeTexCoord'); tc.name = 'P6_TC'; tc.location = (-900, 300)
sep = N.new('ShaderNodeSeparateXYZ'); sep.name = 'P6_Sep'; sep.location = (-700, 300)
mr = N.new('ShaderNodeMapRange'); mr.name = 'P6_Map'; mr.location = (-500, 300)
mr.inputs['From Min'].default_value = -0.2; mr.inputs['From Max'].default_value = 1.0
cr = N.new('ShaderNodeValToRGB'); cr.name = 'P6_SkyRamp'; cr.location = (-300, 300)
el = cr.color_ramp.elements
STOPS = [(0.00, (0.30, 0.31, 0.29)), (0.165, (0.72, 0.80, 0.90)), (0.30, (0.50, 0.66, 0.88)), (1.00, (0.24, 0.43, 0.78))]
while len(el) > 2: el.remove(el[-1])
el[0].position, el[0].color = STOPS[0][0], (*STOPS[0][1], 1)
el[1].position, el[1].color = STOPS[-1][0], (*STOPS[-1][1], 1)
for p, c in STOPS[1:-1]:
    e = el.new(p); e.color = (*c, 1)
cr.color_ramp.interpolation = 'EASE'
nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
nt.links.new(mr.outputs['Result'], cr.inputs['Fac'])
nt.links.new(cr.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = SKY_STRENGTH

ee = sc.eevee
ee.use_shadows = True
ee.shadow_ray_count = 2
ee.shadow_step_count = 8
ee.use_raytracing = True
ee.use_fast_gi = True
if hasattr(ee, 'taa_render_samples'): ee.taa_render_samples = 64
ee.use_shadow_jitter_viewport = False
sc['SH249_sun_datetime'] = '2026-04-15 10:00 CDT (15:00 UTC)'
sc['SH249_sun_elev_deg'] = 38.88
sc['SH249_sun_az_true_deg'] = 102.14
result = dict(sun_rot=[round(a, 4) for a in sun.rotation_euler], energy=L.energy, sky=SKY_STRENGTH)
