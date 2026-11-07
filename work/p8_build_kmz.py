"""Phase 8 KMZ (cloud container). usage: python3 p8_build_kmz.py <in.glb> <out.kmz>
Reads the Phase 8 GLB, keeps signals, signs, markings and ramps (no aerial, roadway, context or radar zones) and writes
one COLLADA model per group (pycollada; metres, Z-up, plain per-material colours, world transforms baked):
  Existing:  E_Signals (to be removed), E_Signals_Remain (to remain), E_Markings (to be removed)
  Proposed:  P_Signals, P_Signs, P_Markings, P_Ramps
KML: one folder per phase (toggleable), one Placemark/Model per group, all anchored at ORIGIN_SC
(Lat 30.0130799, Lon -95.5906606), heading 1.670 deg (scene +Y bearing), altitudeMode relativeToGround.
Markings and ramps are lifted MK_LIFT m so Google Earth terrain doesn't swallow them. Plus an origin pin and a LookAt."""
import json, struct, sys, zipfile, io, math, numpy as np, collada
from collada import source, geometry, material, scene as csc

GLB, OUT = sys.argv[1], sys.argv[2]
LAT0, LON0, HEADING = 30.0130799, -95.5906606, 1.670
MK_LIFT = 0.10
GROUPS = [  # (folder, collection node, model name, label, lift)
    ('Existing', 'E_Signals', 'existing_signals_remove', 'Signals to be removed (callouts A–M)', 0.0),
    ('Existing', 'E_Signals_Remain', 'existing_signals_remain', 'Equipment to remain (R3-8 signs, ITS boxes, CTMS hub)', 0.0),
    ('Existing', 'E_Markings', 'existing_markings', 'Existing pavement markings (to be removed)', MK_LIFT),
    ('Proposed', 'P_Signals', 'proposed_signals', 'Proposed signals (mast arms A–C, K–M, APS poles, radar, cabinet U, service V)', 0.0),
    ('Proposed', 'P_Signs', 'proposed_signs', 'Proposed S6 R1-5BL signs', 0.0),
    ('Proposed', 'P_Markings', 'proposed_markings', 'Proposed pavement markings', MK_LIFT),
    ('Proposed', 'P_Ramps', 'proposed_ramps', 'Proposed curb ramps', MK_LIFT),
]
PAINT = {'MAT_Paint_White': (0.93, 0.93, 0.93), 'MAT_Paint_Yellow': (0.95, 0.74, 0.10)}

f = open(GLB, 'rb').read()
jl = struct.unpack('<I', f[12:16])[0]; J = json.loads(f[20:20 + jl]); BIN = f[20 + jl + 8:]
N, ACC, BV, MATS = J['nodes'], J['accessors'], J['bufferViews'], J['materials']
CT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
def acc(i):
    a = ACC[i]; b = BV[a['bufferView']]; dt = CT[a['componentType']]; nc = NC[a['type']]
    off = b.get('byteOffset', 0) + a.get('byteOffset', 0); stride = b.get('byteStride', 0)
    isz = np.dtype(dt).itemsize * nc
    if stride and stride != isz:
        raw = np.frombuffer(BIN, np.uint8, a['count'] * stride, off).reshape(a['count'], stride)[:, :isz]
        return raw.copy().view(dt).reshape(a['count'], nc)
    return np.frombuffer(BIN, dt, a['count'] * nc, off).reshape(a['count'], nc) if nc > 1 else np.frombuffer(BIN, dt, a['count'], off)
def qmat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def local(n):
    if 'matrix' in n: return np.array(n['matrix']).reshape(4, 4).T
    M = np.eye(4); R = qmat(n.get('rotation', [0, 0, 0, 1])); S = np.diag(n.get('scale', [1, 1, 1]))
    M[:3, :3] = R @ S; M[:3, 3] = n.get('translation', [0, 0, 0]); return M
YUP2ZUP = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)  # glTF (x,y,z) -> Blender (x,-z,y)
def collect(idx, M, out):
    n = N[idx]; M = M @ local(n)
    if 'mesh' in n:
        for p in J['meshes'][n['mesh']]['primitives']:
            P = acc(p['attributes']['POSITION']).astype(float); I = acc(p['indices']).astype(np.int64).reshape(-1, 3)
            Nn = acc(p['attributes']['NORMAL']).astype(float) if 'NORMAL' in p['attributes'] else None
            W = YUP2ZUP @ M
            Pw = P @ W[:3, :3].T + W[:3, 3]
            if Nn is not None:
                Nw = Nn @ np.linalg.inv(W[:3, :3]).T; Nw /= np.linalg.norm(Nw, axis=1, keepdims=True) + 1e-12
            if np.linalg.det(W[:3, :3]) < 0: I = I[:, ::-1]
            out.append((p.get('material', -1), Pw, Nw if Nn is not None else None, I, n.get('name')))
    for c in n.get('children', []): collect(c, M, out)
def color_of(mi):
    if mi < 0: return (0.6, 0.6, 0.6)
    m = MATS[mi]
    if m['name'] in PAINT: return PAINT[m['name']]
    c = m.get('pbrMetallicRoughness', {}).get('baseColorFactor', [0.6, 0.6, 0.6, 1])[:3]
    e = m.get('emissiveFactor', [0, 0, 0])
    lin = [min(1.0, c[k] + 0.5 * e[k]) for k in range(3)]
    return tuple(round(v ** (1 / 2.2), 4) for v in lin)  # linear -> sRGB for Google Earth's plain diffuse

def build_dae(parts, lift):
    mesh = collada.Collada()
    mesh.assetInfo.upaxis = collada.asset.UP_AXIS.Z_UP
    mesh.assetInfo.unitmeter = 1.0; mesh.assetInfo.unitname = 'meter'
    by_mat = {}
    for mi, P, Nn, I, name in parts: by_mat.setdefault(mi, []).append((P, Nn, I))
    nodes = []; ntri = 0
    for k, (mi, lst) in enumerate(sorted(by_mat.items())):
        mname = (MATS[mi]['name'] if mi >= 0 else 'default').replace('.', '_')
        eff = material.Effect('eff%d' % k, [], 'lambert', diffuse=color_of(mi) + (1.0,), double_sided=True)
        mat = material.Material('mat%d' % k, mname, eff)
        mesh.effects.append(eff); mesh.materials.append(mat)
        P = np.vstack([a[0] for a in lst]); off = np.cumsum([0] + [len(a[0]) for a in lst[:-1]])
        I = np.vstack([a[2] + o for a, o in zip(lst, off)])
        Nn = np.vstack([a[1] if a[1] is not None else np.tile([0, 0, 1.0], (len(a[0]), 1)) for a in lst])
        P = P.copy(); P[:, 2] += lift
        vs = source.FloatSource('v%d' % k, np.round(P, 4).ravel(), ('X', 'Y', 'Z'))
        ns = source.FloatSource('n%d' % k, np.round(Nn, 3).ravel(), ('X', 'Y', 'Z'))
        geom = geometry.Geometry(mesh, 'g%d' % k, mname, [vs, ns])
        il = source.InputList(); il.addInput(0, 'VERTEX', '#v%d' % k); il.addInput(0, 'NORMAL', '#n%d' % k)
        geom.primitives.append(geom.createTriangleSet(I.ravel(), il, 'm%d' % k))
        mesh.geometries.append(geom)
        nodes.append(csc.GeometryNode(geom, [csc.MaterialNode('m%d' % k, mat, inputs=[])]))
        ntri += len(I)
    sc = csc.Scene('scene', [csc.Node('model', children=nodes)])
    mesh.scenes.append(sc); mesh.scene = sc
    buf = io.BytesIO(); mesh.write(buf); return buf.getvalue(), ntri, len(by_mat)

colnode = {n['name']: i for i, n in enumerate(N) if 'mesh' not in n}
par = {c: i for i, n in enumerate(N) for c in n.get('children', [])}
def world_of(i):  # parent chain of a collection node (identity in practice)
    M = np.eye(4); chain = []
    while i in par: i = par[i]; chain.append(i)
    for j in reversed(chain): M = M @ local(N[j])
    return M
kml_folders = {'Existing': [], 'Proposed': []}; files = {}; report = []
for folder, col, fname, label, lift in GROUPS:
    parts = []
    ci = colnode[col]
    for c in N[ci].get('children', []): collect(c, world_of(ci) @ local(N[ci]), parts)
    dae, ntri, nm = build_dae(parts, lift)
    files['models/%s.dae' % fname] = dae
    allP = np.vstack([p[1] for p in parts])
    report.append((col, len(N[ci].get('children', [])), ntri, nm, round(len(dae) / 1024), allP.min(0).round(1).tolist(), allP.max(0).round(1).tolist()))
    kml_folders[folder].append(f"""    <Placemark>
      <name>{label}</name>
      <Model id="{fname}">
        <altitudeMode>relativeToGround</altitudeMode>
        <Location><longitude>{LON0}</longitude><latitude>{LAT0}</latitude><altitude>0</altitude></Location>
        <Orientation><heading>{HEADING}</heading><tilt>0</tilt><roll>0</roll></Orientation>
        <Scale><x>1</x><y>1</y><z>1</z></Scale>
        <Link><href>models/{fname}.dae</href></Link>
      </Model>
    </Placemark>""")
desc = ('Visualization of the TxDOT traffic signal upgrade, SH 249 at Spring Cypress Rd (CSJ 0720-03-153), from plan sheets '
        '24-28, 38-41 and 67. FOR ILLUSTRATION ONLY - NOT FOR CONSTRUCTION. Anchor: plan origin ORIGIN_SC (Spring Cypress '
        'midline between the SB and NB mainlane edges), heading 1.670 deg. Markings and ramps lifted %.2f m above ground.' % MK_LIFT)
kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>SH 249 at Spring Cypress Rd – signal upgrade (CSJ 0720-03-153)</name>
  <description>{desc}</description>
  <open>1</open>
  <LookAt><longitude>{LON0}</longitude><latitude>{LAT0 - 0.0016}</latitude><altitude>0</altitude>
    <heading>-15</heading><tilt>55</tilt><range>420</range><altitudeMode>relativeToGround</altitudeMode></LookAt>
  <Style id="origin"><IconStyle><scale>0.8</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>
  <Placemark>
    <name>Plan origin (ORIGIN_SC)</name>
    <description>Lat 30.0130799, Lon -95.5906606 (WGS84). Spring Cypress midline, midway between the outer SB and NB mainlane edges.</description>
    <styleUrl>#origin</styleUrl>
    <Point><coordinates>{LON0},{LAT0},0</coordinates></Point>
  </Placemark>
  <Folder>
    <name>Existing</name>
    <open>1</open>
{chr(10).join(kml_folders['Existing'])}
  </Folder>
  <Folder>
    <name>Proposed</name>
    <open>1</open>
{chr(10).join(kml_folders['Proposed'])}
  </Folder>
</Document>
</kml>
"""
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('doc.kml', kml)  # must be the first entry
    for k, v in files.items(): z.writestr(k, v)
for r in report: print('%-18s objs %3d tris %6d mats %2d dae %5d KB  min %s max %s' % r)
import os; print('kmz', round(os.path.getsize(OUT) / 1024), 'KB')
