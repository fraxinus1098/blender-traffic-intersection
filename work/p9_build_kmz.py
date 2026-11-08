"""Phase 9D KMZ. usage (venv, repo root): .venv/bin/python work/p9_build_kmz.py <in.glb> <out.kmz>
Changes from p8_build_kmz.py:
  1. Markings, curb ramps and radar zones are KML Polygons with altitudeMode clampToGround (draped on Google Earth's
     terrain) instead of lifted COLLADA models: each mesh's triangles are projected to plan view and merged (shapely),
     one Placemark per object and colour. Signals and signs stay COLLADA models (as in Phase 8).
  2. One point Placemark per pole, cabinet, service pole, ground box and ground-mounted sign, with a balloon carrying
     the viewer's info (callout, status, type, sheet, arm length, note), in Existing / Proposed folders.
  3. GroundOverlays of the eight masked plan sheets (gx:LatLonQuad from the REF_* plane corners in
     work/p9_sheet_planes.json), hidden by default.
  4. A gx:Tour through the main viewer presets (work/p9_cameras.json).
All plan coordinates go scene ft -> UTM 15N (Phase 2 fit, p6_common.scene_ft_to_utm) -> WGS84 (pyproj). The COLLADA
models keep the Phase 8 anchoring (ORIGIN_SC + heading 1.670 deg), which agrees with that transform within 0.07 m."""
import json, struct, sys, zipfile, io, math, os, html
import numpy as np
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
sys.path.insert(0, 'work')
from p6_common import scene_ft_to_utm, FT
import importlib.util
spec = importlib.util.spec_from_file_location('p8kmz_helpers', 'work/p8_build_kmz.py')

GLB, OUT = sys.argv[1], sys.argv[2]
LAT0, LON0, HEADING = 30.0130799, -95.5906606, 1.670
to_ll = Transformer.from_crs('EPSG:32615', 'EPSG:4326', always_xy=True)
def ll(xm, ym):  # scene metres -> (lon, lat)
    E, N = scene_ft_to_utm(np.asarray(xm) / FT, np.asarray(ym) / FT)
    return to_ll.transform(E, N)

# ---------- GLB reading (same helpers as Phase 8) ----------
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
# COLLADA writer and colours: reuse Phase 8's build_dae / color_of by executing only their definitions
src8 = open('work/p8_build_kmz.py').read()
g8 = {'np': np, 'io': io, 'MATS': MATS, 'collada': __import__('collada')}
exec(src8[src8.index('PAINT = '):src8.index('\nf = open(GLB')], g8)
exec('from collada import source, geometry, material, scene as csc\n' + src8[src8.index('def color_of'):src8.index('colnode = ')], g8)
build_dae, color_of = g8['build_dae'], g8['color_of']

colnode = {n['name']: i for i, n in enumerate(N) if 'mesh' not in n}
par = {c: i for i, n in enumerate(N) for c in n.get('children', [])}
def world_of(i):
    M = np.eye(4); chain = []
    while i in par: i = par[i]; chain.append(i)
    for j in reversed(chain): M = M @ local(N[j])
    return M
def objects_in(col):  # [(node index, name, extras, parts)]
    ci = colnode[col]; M0 = world_of(ci) @ local(N[ci]); out = []
    for c in N[ci].get('children', []):
        parts = []; collect(c, M0, parts); out.append((c, N[c].get('name'), N[c].get('extras', {}), parts))
    return out

esc = lambda s: html.escape(str(s), quote=False)
def kcol(rgb, a):  # KML aabbggrr
    r, g, b = [int(round(v * 255)) for v in rgb]; return '%02x%02x%02x%02x' % (int(a * 255), b, g, r)

# ---------- 1. COLLADA signals and signs ----------
MODELS = [('Existing', 'E_Signals', 'existing_signals_remove', 'Signals to be removed (callouts A–M) – 3D'),
          ('Existing', 'E_Signals_Remain', 'existing_signals_remain', 'Equipment to remain (R3-8 signs, ITS boxes, CTMS hub) – 3D'),
          ('Proposed', 'P_Signals', 'proposed_signals', 'Proposed signals (mast arms A–C, K–M, APS poles, radar, cabinet U, service V) – 3D'),
          ('Proposed', 'P_Signs', 'proposed_signs', 'Proposed S6 R1-5BL signs – 3D')]
fold = {'Existing': [], 'Proposed': [], 'Engineering': []}; files = {}; report = []
for folder, col, fname, label in MODELS:
    parts = [p for _, _, _, ps in objects_in(col) for p in ps]
    dae, ntri, nm = build_dae(parts, 0.0)
    files[f'models/{fname}.dae'] = dae; report.append(f'{col}: {ntri} tris, {nm} mats, {len(dae) // 1024} KB')
    fold[folder].append(f"""<Placemark><name>{esc(label)}</name>
  <Model id="{fname}"><altitudeMode>relativeToGround</altitudeMode>
    <Location><longitude>{LON0}</longitude><latitude>{LAT0}</latitude><altitude>0</altitude></Location>
    <Orientation><heading>{HEADING}</heading><tilt>0</tilt><roll>0</roll></Orientation>
    <Scale><x>1</x><y>1</y><z>1</z></Scale><Link><href>models/{fname}.dae</href></Link></Model></Placemark>""")

# ---------- 2. draped polygons ----------
STY = {}
def style(key, rgb, fill_a, line_a=0.0, width=0):
    STY[key] = f'<Style id="{key}"><LineStyle><color>{kcol(rgb, line_a)}</color><width>{width}</width></LineStyle>' \
               f'<PolyStyle><color>{kcol(rgb, fill_a)}</color><outline>{1 if line_a else 0}</outline></PolyStyle></Style>'
    return key
def footprint(P, I):
    tris = [Polygon(P[t, :2]) for t in I]
    tris = [t for t in tris if t.is_valid and t.area > 1e-6]
    return unary_union([t.buffer(0.005, join_style=2) for t in tris]).buffer(-0.004, join_style=2).simplify(0.01)
def kml_poly(g):
    out = []
    for p in (g.geoms if isinstance(g, MultiPolygon) else [g]):
        if p.is_empty or p.area < 0.02: continue
        def ring(c):
            lo, la = ll(np.array(c)[:, 0], np.array(c)[:, 1])
            return ' '.join(f'{a:.8f},{b:.8f},0' for a, b in zip(lo, la))
        inner = ''.join(f'<innerBoundaryIs><LinearRing><coordinates>{ring(r.coords)}</coordinates></LinearRing></innerBoundaryIs>' for r in p.interiors)
        out.append(f'<Polygon><altitudeMode>clampToGround</altitudeMode><outerBoundaryIs><LinearRing><coordinates>{ring(p.exterior.coords)}'
                   f'</coordinates></LinearRing></outerBoundaryIs>{inner}</Polygon>')
    return out
DRAPE = [('Existing', 'E_Markings', 'Existing pavement markings (to be removed)', 0.85),
         ('Proposed', 'P_Markings', 'Proposed pavement markings', 0.95),
         ('Proposed', 'P_Ramps', 'Proposed curb ramps', 0.9),
         ('Engineering', 'ENG_RadarZones', 'Radar detection zones (illustrative)', 0.35)]
npoly = {}
for folder, col, label, alpha in DRAPE:
    pms = []
    for ni, name, ex, parts in objects_in(col):
        by = {}
        for mi, P, Nn, I, _ in parts:
            mname = MATS[mi]['name'] if mi >= 0 else 'default'
            if col == 'ENG_RadarZones' and not mname.endswith('Fill'): continue   # labels and edges: polygon outline instead
            by.setdefault(mname, []).append((P, I))
        for mname, lst in by.items():
            g = unary_union([footprint(P, I) for P, I in lst])
            polys = kml_poly(g)
            if not polys: continue
            rgb = color_of(MATS.index(next(m for m in MATS if m['name'] == mname))) if mname != 'default' else (0.6, 0.6, 0.6)
            sk = style('s_' + mname.replace('.', '_'), rgb, alpha, 1.0 if col == 'ENG_RadarZones' else 0.0, 2 if col == 'ENG_RadarZones' else 0)
            d = esc(ex.get('sh249_note', ''))
            pms.append(f'<Placemark><name>{esc(name)} ({esc(mname.replace("MAT_", ""))})</name><description>{d}</description><styleUrl>#{sk}</styleUrl>'
                       f'<MultiGeometry>{"".join(polys)}</MultiGeometry></Placemark>')
            npoly[col] = npoly.get(col, 0) + len(polys)
    vis = '<visibility>0</visibility>' if col == 'ENG_RadarZones' else ''
    fold[folder].append(f'<Folder><name>{esc(label)} – draped</name>{vis}\n' + '\n'.join(pms) + '</Folder>')

# ---------- 3. equipment point placemarks with balloons ----------
CATS = [('Mast arm poles', ('mast arm pole',)), ('Pedestrian poles', ('pedestal',)), ('Cabinets and power', ('cabinet', 'electrical service')),
        ('Ground boxes', ('ground box',)), ('Ground-mounted signs', ('ground-mounted',))]
ICON = {'new': ('ff24b81a', 'http://maps.google.com/mapfiles/kml/paddle/grn-circle.png'),
        'remove': ('ff0d0fd9', 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'),
        'remain': ('ff9a9a9a', 'http://maps.google.com/mapfiles/kml/paddle/wht-circle.png')}
for st, (c, href) in ICON.items():
    STY['eq_' + st] = f'<Style id="eq_{st}"><IconStyle><scale>0.8</scale><Icon><href>{href}</href></Icon></IconStyle><LabelStyle><scale>0.75</scale></LabelStyle>' \
                      f'<BalloonStyle><text>$[description]</text></BalloonStyle></Style>'
ST_TXT = {'remove': 'Existing – to be removed', 'remain': 'Existing – to remain', 'new': 'Proposed (new)'}
eq = {'Existing': {}, 'Proposed': {}}; neq = 0
for col in ('E_Signals', 'E_Signals_Remain', 'P_Signals', 'P_Signs'):
    for ni, name, ex, parts in objects_in(col):
        t = ex.get('sh249_type', ''); st = ex.get('sh249_status')
        cat = next((c for c, keys in CATS if any(k in t for k in keys)), None)
        if not cat or st not in ICON or not parts: continue
        P = np.vstack([p[1] for p in parts]); x, y = (P[:, 0].min() + P[:, 0].max()) / 2, (P[:, 1].min() + P[:, 1].max()) / 2
        if 'mast arm pole' in t:   # pole shaft = the lowest vertices (the arm extends the bounding box)
            low = P[P[:, 2] < P[:, 2].min() + 0.5]; x, y = low[:, 0].mean(), low[:, 1].mean()
        lo, la = ll(x, y)
        rows = [('Callout', ex.get('sh249_callout')), ('Status', ST_TXT[st]), ('Type', t), ('Sheet', ex.get('sh249_sheet'))]
        rows += [(k[6:].replace('_', ' ').capitalize(), (round(v, 2) if isinstance(v, float) else v)) for k, v in ex.items()
                 if k.startswith('sh249_') and k not in ('sh249_callout', 'sh249_status', 'sh249_type', 'sh249_sheet', 'sh249_note', 'sh249_phase')]
        tbl = ''.join(f'<tr><th align="left" style="color:#5b6670;padding-right:8px">{esc(k)}</th><td>{esc(v)}</td></tr>' for k, v in rows if v not in (None, ''))
        desc = f'<![CDATA[<div style="width:340px;font-family:sans-serif;font-size:12px"><b style="font-size:14px">{esc(name)}</b>' \
               f'<p>{esc(ex.get("sh249_note", ""))}</p><table>{tbl}</table><p style="color:#7a1c12"><b>For illustration only – not for construction</b></p></div>]]>'
        folder = 'Proposed' if st == 'new' else 'Existing'
        eq[folder].setdefault(cat, []).append(f'<Placemark><name>{esc(ex.get("sh249_callout", ""))}</name><description>{desc}</description>'
            f'<styleUrl>#eq_{st}</styleUrl><Point><coordinates>{lo:.8f},{la:.8f},0</coordinates></Point></Placemark>')
        neq += 1
for folder, cats in eq.items():
    sub = ''.join(f'<Folder><name>{esc(c)}</name>' + ''.join(v) + '</Folder>' for c, v in cats.items())
    fold[folder].append(f'<Folder><name>Equipment (click for details)</name>{sub}</Folder>')

# ---------- 4. plan sheet ground overlays ----------
ovl = []
for name, s in json.load(open('work/p9_sheet_planes.json')).items():
    im = Image.open('plans/masked/' + s['image']).convert('RGBA'); im = im.resize((4096, round(im.height * 4096 / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True); files[f'sheets/{s["image"]}'] = buf.getvalue()
    # gx:LatLonQuad wants the image's lower-left, lower-right, upper-right, upper-left corners
    byuv = {tuple(c[1]): c[0] for c in s['corners']}
    q = [byuv[(0.0, 0.0)], byuv[(1.0, 0.0)], byuv[(1.0, 1.0)], byuv[(0.0, 1.0)]]
    lo, la = ll(np.array([c[0] for c in q]), np.array([c[1] for c in q]))
    num = name.split('_')[1]
    ovl.append(f'<GroundOverlay><name>Sheet {num}: {esc(" ".join(name.split("_")[2:]))}</name><visibility>0</visibility><drawOrder>{10 + int(num)}</drawOrder>'
               f'<color>e6ffffff</color><Icon><href>sheets/{s["image"]}</href></Icon><altitudeMode>clampToGround</altitudeMode>'
               f'<gx:LatLonQuad><coordinates>{" ".join(f"{a:.8f},{b:.8f}" for a, b in zip(lo, la))}</coordinates></gx:LatLonQuad></GroundOverlay>')

# ---------- 5. tour through the viewer presets ----------
CAMS = json.load(open('work/p9_cameras.json'))
TOUR = [('Overview (oblique)', 'CAM_Review_Oblique'), ('Top (plan)', 'CAM_Review_Top'), ('SB intersection close-up', 'CAM_P5_SB'),
        ('SB curb ramps', 'CAM_P5b_SB_Ramps'), ("Driver's eye: SB int., southbound feeder", 'CAM_P7_Drv_SBint_SB'),
        ("Driver's eye: SB int., westbound", 'CAM_P7_Drv_SBint_WB'), ('NB intersection close-up', 'CAM_P5_NB'),
        ('NB curb ramps', 'CAM_P5b_NB_Ramps'), ("Driver's eye: NB int., northbound feeder", 'CAM_P7_Drv_NBint_NB'),
        ("Driver's eye: NB int., westbound", 'CAM_P7_Drv_NBint_WB'), ('Overview (oblique)', 'CAM_Review_Oblique')]
def view_of(cam):
    c = CAMS[cam]; px, py, pz = c['pos'][0], -c['pos'][2], c['pos'][1]   # glTF -> scene metres
    fx, fy, fz = c['fwd'][0], -c['fwd'][2], c['fwd'][1]
    if c['type'] == 'ORTHO':   # top views: LookAt straight down with a range that shows the ortho width at GE's ~60 deg FOV
        lo, la = ll(px, py); rng = c['ortho'] / 2 / math.tan(math.radians(30))
        return f'<LookAt><longitude>{lo:.8f}</longitude><latitude>{la:.8f}</latitude><altitude>0</altitude><heading>{HEADING:.2f}</heading>' \
               f'<tilt>0</tilt><range>{rng:.1f}</range><altitudeMode>relativeToGround</altitudeMode></LookAt>'
    lo, la = ll(px, py); lo2, la2 = ll(px + fx * 10, py + fy * 10)
    head = math.degrees(math.atan2((lo2 - lo) * math.cos(math.radians(la)), la2 - la))
    tilt = 90 + math.degrees(math.asin(max(-1, min(1, fz))))
    return f'<Camera><longitude>{lo:.8f}</longitude><latitude>{la:.8f}</latitude><altitude>{pz:.2f}</altitude><heading>{head:.2f}</heading>' \
           f'<tilt>{tilt:.2f}</tilt><roll>0</roll><altitudeMode>relativeToGround</altitudeMode></Camera>'
steps = []
for label, cam in TOUR:
    if cam not in CAMS: continue
    steps.append(f'<gx:FlyTo><gx:duration>4.0</gx:duration><gx:flyToMode>smooth</gx:flyToMode>{view_of(cam)}</gx:FlyTo><gx:Wait><gx:duration>2.5</gx:duration></gx:Wait>')
tour = f'<gx:Tour><name>Tour of the viewer presets</name><description>Overview, both intersections, curb ramps and driver\'s-eye views (3.5 ft at the stop bar).</description><gx:Playlist>{"".join(steps)}</gx:Playlist></gx:Tour>'

desc = ('Visualization of the TxDOT traffic signal upgrade, SH 249 at Spring Cypress Rd (CSJ 0720-03-153), from plan sheets '
        '24-28, 38-41 and 67. FOR ILLUSTRATION ONLY - NOT FOR CONSTRUCTION. Signals and signs are 3D models anchored at the plan '
        'origin ORIGIN_SC (heading 1.670 deg); markings, curb ramps and radar zones are draped on the terrain; the plan-sheet overlays '
        'and radar zones are off by default. Turn off 3D Buildings if Google\'s photogrammetry hides the markings.')
kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
<name>SH 249 at Spring Cypress Rd – signal upgrade (CSJ 0720-03-153)</name>
<description>{esc(desc)}</description>
<open>1</open>
<LookAt><longitude>{LON0}</longitude><latitude>{LAT0 - 0.0016}</latitude><altitude>0</altitude>
  <heading>-15</heading><tilt>55</tilt><range>420</range><altitudeMode>relativeToGround</altitudeMode></LookAt>
<Style id="origin"><IconStyle><scale>0.8</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>
{chr(10).join(STY.values())}
{tour}
<Placemark><name>Plan origin (ORIGIN_SC)</name>
  <description>Lat 30.0130799, Lon -95.5906606 (WGS84). Spring Cypress midline, midway between the outer SB and NB mainlane edges.</description>
  <styleUrl>#origin</styleUrl><Point><coordinates>{LON0},{LAT0},0</coordinates></Point></Placemark>
<Folder><name>Existing</name><open>1</open>
{chr(10).join(fold['Existing'])}
</Folder>
<Folder><name>Proposed</name><open>1</open>
{chr(10).join(fold['Proposed'])}
</Folder>
<Folder><name>Engineering</name>
{chr(10).join(fold['Engineering'])}
</Folder>
<Folder><name>Plan sheets (masked, off by default)</name><visibility>0</visibility>
{chr(10).join(ovl)}
</Folder>
</Document>
</kml>
"""
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('doc.kml', kml)  # must be the first entry
    for k, v in files.items(): z.writestr(k, v)
for r in report: print(r)
print('draped polygons', npoly, 'equipment placemarks', neq, 'sheets', len(ovl), 'tour steps', len(steps))
print('kmz', round(os.path.getsize(OUT) / 1024), 'KB; doc.kml', round(len(kml) / 1024), 'KB')
