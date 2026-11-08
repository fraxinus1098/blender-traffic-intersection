"""Phase 9C: extra data for the viewer (plan sheets, photo overlays, visibility cones) -> one JSON inlined in the HTML.
Run from the repo root (venv):  .venv/bin/python work/p9_viewer_data.py [out.json]   (default work/p9_tests/p9_viewer_data.json)
Inputs:
  work/p9_sheet_planes.json   corners (scene metres) and UVs of the REF_* sheet planes, exported from v12_export
                              (the same planes the Phase 4-5 plan-overlay checks used)
  plans/masked/*.png          masked plan sheets (5100 x 3300), downscaled to 4096 px wide for WebGL
  work/p9_photos/p9_photos.json, p9_cams.json and <id>_{photo.jpg,existing.png,proposed.png}  (p9_photo_composite.py)
  work/p7_data.json, work/p9_visibility_v11.json  driver approaches (stop bars, lanes, heads) and head visibility
All positions are converted to glTF/three.js metres: Blender (x, y, z) -> (x, z, -y)."""
import json, sys, base64, io, math
from PIL import Image

FT = 0.3048
OUT = sys.argv[1] if len(sys.argv) > 1 else 'work/p9_tests/p9_viewer_data.json'
gl = lambda x, y, z: [round(x, 4), round(z, 4), round(-y, 4)]
def b64(path_or_img, fmt=None):
    if isinstance(path_or_img, str): return base64.b64encode(open(path_or_img, 'rb').read()).decode()
    buf = io.BytesIO(); path_or_img.save(buf, fmt, optimize=True); return base64.b64encode(buf.getvalue()).decode()

# ---- plan sheets ----
sheets = []
for name, s in json.load(open('work/p9_sheet_planes.json')).items():
    num = int(name.split('_')[1]); kind = 'signal' if 'signal' in name else 'markings'
    status = 'existing' if 'existing' in name else 'proposed'
    im = Image.open('plans/masked/' + s['image']).convert('RGBA')
    im = im.resize((4096, round(im.height * 4096 / im.width)), Image.LANCZOS)
    sheets.append(dict(name=name, sheet=num, kind=kind, status=status, label=f'Sheet {num} – {kind} ({status})',
                       corners=[gl(*c[0][:2], 0.0) for c in s['corners']], uv=[c[1] for c in s['corners']],
                       png=b64(im, 'PNG')))

# ---- photos ----
photos = []
meta = json.load(open('work/p9_photos/p9_photos.json')); cams = json.load(open('work/p9_photos/p9_cams.json'))
for iid, m in meta.items():
    C = cams[iid]; p = C['pose_solved']; R = p['R_world_from_cv']
    fwd = [R[i][2] for i in range(3)]; up = [-R[i][1] for i in range(3)]
    x, y, z = [c * FT for c in p['loc_ft']]
    w, h = C['size']; f = C['K'][0][0]
    chk = m['check_px_ft']
    photos.append(dict(id=iid, title=m['title'], credit=m['credit'], creator=m['creator'], captured_at=m['captured_at'],
        source=m['source'], licence=m['licence'], pos=gl(x, y, z), fwd=gl(*fwd), up=gl(*up),
        vfov_deg=round(math.degrees(2 * math.atan(h / 2 / f)), 2), hfov_deg=m['camera']['hfov_deg'],
        crop_frac=m['size'][1] / (m['size'][0] * h / w),       # visible part of the frame height (hood cropped)
        solve=dict(points=m['solve_points'], lines=list(m['solve_lines']), check=chk, line_median_px=m['line_median_px']),
        photo=b64(f'work/p9_photos/{iid}_photo.jpg'), existing=b64(f'work/p9_photos/{iid}_existing.png'),
        proposed=b64(f'work/p9_photos/{iid}_proposed.png')))

# ---- driver cones (MUTCD 4D.13: 20 deg either side, from 10 ft behind the stop line at the approach centre, 3.5 ft eye) ----
D = json.load(open('work/p7_data.json'))['approaches']; V = json.load(open('work/p9_visibility_v11.json'))
cones = {}
for a in D:
    k = a['key']; v = V[k]; up = math.radians(a['axis_up_deg']); tr = math.radians(a['travel_deg'])
    bx, by = a['bar_centre']; ax, ay = bx + 10 * math.cos(up), by + 10 * math.sin(up)
    heads = {}
    for hn, hi in v['heads'].items():
        vis = min(l['at_bar'][hn]['vis'] for l in v['lanes'])
        fails = [l['lane'] for l in v['lanes'] if l['first_fail_ft'] is not None]
        heads[hn] = dict(cone_deg=hi['cone_angle_deg'], past_stop_ft=hi['past_stop_line_ft'], vis_min=vis,
                         ok_cone=abs(hi['cone_angle_deg']) <= 20, ok_long=40 <= hi['past_stop_line_ft'] <= 180,
                         ok_vis=vis >= 5 / 9 and not fails)
    cones[v['cam']] = dict(key=k, apex=gl(ax * FT, ay * FT, 3.5 * FT), dir=gl(math.cos(tr), math.sin(tr), 0),
                           half_deg=20, len_m=round(200 * FT, 2), long_m=[round(40 * FT, 3), round(180 * FT, 3)],
                           bar=[gl(e[0] * FT, e[1] * FT, 0) for e in a['bar_ends']],
                           speed=v['speed'], req_ft=v['req_ft'], lanes=len(v['lanes']), heads=heads)

json.dump(dict(sheets=sheets, photos=photos, cones=cones), open(OUT, 'w'), separators=(',', ':'))
print(OUT, 'sheets', len(sheets), 'photos', len(photos), 'cones', len(cones),
      'MB', round(sum(len(s['png']) for s in sheets) / 1e6, 1), round(sum(len(p['photo']) + len(p['existing']) + len(p['proposed']) for p in photos) / 1e6, 1))
