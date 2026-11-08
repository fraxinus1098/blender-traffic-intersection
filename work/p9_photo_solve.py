"""Phase 9B step 2: camera solve for the Mapillary frames (pinhole after p9_photo_prep.py undistortion).
Run from the repo root (venv):
  .venv/bin/python work/p9_photo_solve.py project <id> [init|solved]   -> scratch image with model points drawn
  .venv/bin/python work/p9_photo_solve.py solve <id>                   -> pose_solved in work/p9_photos/p9_cams.json
Model points (scene ft) are named features of the existing equipment (work/p9_photos/p9_model_points.json, exported
from v11). Photo points are picked by eye on the undistorted image and stored in work/p9_photos/p9_picks.json
({id: {point name: [u, v] full-resolution px}}). The solve is OpenCV solvePnP (iterative, from the Mapillary pose)
with the Mapillary intrinsics fixed; residuals are reported in px and in ft at each point's depth."""
import json, sys, math, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
CAMS = 'work/p9_photos/p9_cams.json'; PICKS = 'work/p9_photos/p9_picks.json'
SCR = os.environ.get('P9_SCRATCH', 'work/p9_photos/render')
MP = json.load(open('work/p9_photos/p9_model_points.json'))
FT = 0.3048
def o(n): return MP[n]['origin']
# named 3D points (ft). Pole top = 30 ft shaft top; arm roots at 19.5 ft; head = housing centre.
P3 = {}
for n, k in (('E_MA_K_44ft', 'K'), ('E_MA_H_Dual55x32ft', 'H'), ('E_MA_C_Dual55x32ft', 'C'), ('E_MA_E_44ft', 'E')):
    x, y, _ = o(n); P3[f'{k}_base'] = (x, y, 0.5); P3[f'{k}_top'] = (x, y, 30.0); P3[f'{k}_arm_root'] = (x, y, 19.5)
for n in MP:
    if n.startswith('E_HEAD_'): P3['head_' + n.split('_')[2]] = tuple(o(n))
    if n.startswith('E_PED_'): x, y, _ = o(n); P3[n[2:] + '_base'] = (x, y, 0.5); P3[n[2:] + '_top'] = (x, y, 10.0)
    if n.startswith('E_ELECSVC_'): x, y, _ = o(n); P3[n.split('_')[2] + '_svc_base'] = (x, y, 0.5); P3[n.split('_')[2] + '_svc_top'] = (x, y, 16.0)
# street-name sign panel centres (p9_signs_blender.py SIGNS table)
P3.update({'sign_K': (146.1, 49.3, 18.5), 'sign_H_W': (235.5, 3.6, 18.5), 'sign_H_S': (254.0, -2.5, 19.1),
           'sign_C_N': (-212.6, 1.3, 19.1), 'sign_C_E': (-192.3, -8.9, 18.5), 'sign_E': (-100.3, -51.6, 18.5)})

def cam(iid, which):
    C = json.load(open(CAMS))[iid]; K = np.array(C['K'])
    p = C['pose_solved' if which == 'solved' else 'pose_init']
    Rwc = np.array(p['R_world_from_cv']); t = np.array(p['loc_ft']) * FT
    return C, K, Rwc, t
def project(K, Rwc, t, pts_ft):
    X = np.array(pts_ft, float) * FT
    Xc = (X - t) @ Rwc                         # camera coords = Rwc^T (X - t)
    uv = (K @ Xc.T).T; return uv[:, :2] / uv[:, 2:3], Xc[:, 2]

mode, iid = sys.argv[1], sys.argv[2]
if mode == 'project':
    which = sys.argv[3] if len(sys.argv) > 3 else 'init'
    C, K, Rwc, t = cam(iid, which)
    names = list(P3); uv, z = project(K, Rwc, t, [P3[n] for n in names])
    im = Image.open(f'work/p9_photos/raw/{iid}_undist.jpg').convert('RGB'); dr = ImageDraw.Draw(im)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    picks = json.load(open(PICKS)).get(iid, {}) if os.path.exists(PICKS) else {}
    w, h = C['size']
    for n, (u, v), zz in zip(names, uv, z):
        if zz <= 0 or not (-200 < u < w + 200 and -200 < v < h + 200): continue
        dr.ellipse([u - 9, v - 9, u + 9, v + 9], outline=(255, 0, 255), width=4)
        dr.text((u + 12, v - 14), n, fill=(255, 0, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0))
        if n in picks:
            pu, pv = picks[n]; dr.line([u, v, pu, pv], fill=(255, 255, 0), width=3)
            dr.ellipse([pu - 7, pv - 7, pu + 7, pv + 7], outline=(0, 255, 0), width=4)
    os.makedirs(SCR, exist_ok=True)
    im.save(f'{SCR}/{iid}_proj_{which}.jpg', quality=85); print('wrote', f'{SCR}/{iid}_proj_{which}.jpg')
elif mode == 'edge':
    # detect the bridge top edge (sky -> barrier) column by column: strongest bright-to-dark step in [y0, y1]
    y0, y1, x0, x1 = map(int, sys.argv[3:7])
    g = cv2.GaussianBlur(cv2.imread(f'work/p9_photos/raw/{iid}_undist.jpg', cv2.IMREAD_GRAYSCALE).astype(np.float32), (5, 5), 1.5)
    pts = []
    for x in range(x0, x1, 20):
        col = g[y0:y1, x - 2:x + 3].mean(1)
        d = col[:-6] - col[6:]                       # bright above, dark below
        k = int(np.argmax(d)); pts.append([x, y0 + k + 3, float(d[k])])
    picks = json.load(open(PICKS)) if os.path.exists(PICKS) else {}
    picks.setdefault(iid, {})['line:bridge_top_E'] = [[p[0], p[1]] for p in pts if p[2] > 15]
    json.dump(picks, open(PICKS, 'w'), indent=1)
    print(len(picks[iid]['line:bridge_top_E']), 'edge points', [(p[0], p[1], round(p[2])) for p in pts][::6])
elif mode == 'solve':
    from scipy.optimize import least_squares
    C, K, Rwc, t = cam(iid, os.environ.get('P9_START', 'init'))     # P9_START=solved refines the last solve
    picks = json.load(open(PICKS))[iid]
    USE = sys.argv[3].split(',') if len(sys.argv) > 3 else None          # optional subset of point names
    names = [n for n in picks if n in P3 and (USE is None or n in USE)]
    X = np.array([P3[n] for n in names], float).reshape(-1, 3); x = np.array([picks[n] for n in names], float).reshape(-1, 2)
    lines = {n[5:]: np.array(v, float) for n, v in picks.items() if n.startswith('line:')}
    L3 = {}
    if 'bridge_top_E' in lines:          # east barrier top: plan deck edge, lidar profile + 2.67 ft barrier
        Bj = json.load(open('work/p9_lidar.json'))['bridge']
        AXb, NRb, C0b, HWb = np.array(Bj['axis_unit']), np.array(Bj['normal_unit']), np.array(Bj['centre_on_Y0']), Bj['deck_width_ft'] / 2
        ps = np.array([p['s'] for p in Bj['profile']]); pt = np.array([p['top'] for p in Bj['profile']])
        ss = np.arange(-260, 261, 5.0); xy = C0b + ss[:, None] * AXb + HWb * NRb
        L3['bridge_top_E'] = np.column_stack([xy, np.interp(ss, ps, pt) + 2.67])
    FREE_F = os.environ.get('P9_FREE_F') == '1'     # also refine the focal length (Mapillary self-calibration)
    K0 = K.copy()
    if os.path.exists('work/p9_photos/p9_lines3d.json'):
        for n, v in json.load(open('work/p9_photos/p9_lines3d.json')).items():
            if n in lines: L3[n] = np.array(v['pts'], float)
    # optional: existing white markings vs bright paint in the photo (distance transform of a top-hat paint mask)
    MARK = os.environ.get('P9_MARK') == '1'; MW = float(os.environ.get('P9_MARK_W', 0.08)); CAP = float(os.environ.get('P9_MARK_CAP', 25)); RMAX = float(os.environ.get('P9_MARK_R', 220))
    if MARK:
        V0 = int(os.environ.get('P9_MARK_V0', 1150)); V1 = int(os.environ.get('P9_MARK_V1', 1950))
        gimg = cv2.imread(f'work/p9_photos/raw/{iid}_undist.jpg', cv2.IMREAD_GRAYSCALE)
        th = cv2.morphologyEx(gimg, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
        paint = ((th > int(os.environ.get('P9_PAINT_TH', 45))) & (gimg > np.percentile(gimg[V0:V1], 80))).astype(np.uint8); paint[:V0] = 0; paint[V1:] = 0
        paint = cv2.morphologyEx(paint, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        DT = cv2.distanceTransform(1 - paint, cv2.DIST_L2, 5)
        cv2.imwrite(f'{SCR}/{iid}_paint.png', paint * 255)
        tris = np.array(json.load(open('work/p9_photos/p9_mk_white_tris.json'))['tris'], float)
        c0 = t / FT; fwd0 = Rwc @ [0, 0, 1]
        cen = tris.mean(1); dvec = cen[:, :2] - c0[:2]
        keep = (np.hypot(*dvec.T) < RMAX) & ((dvec @ fwd0[:2]) > 8)
        MS = []
        for tri in tris[keep]:
            e = max(np.linalg.norm(tri[i] - tri[(i + 1) % 3]) for i in range(3)); n = max(1, int(math.ceil(e / 2.0)))
            for i in range(n + 1):
                for j in range(n + 1 - i):
                    a, b = i / n, j / n; MS.append(tri[0] + a * (tri[1] - tri[0]) + b * (tri[2] - tri[0]))
        MS = np.unique(np.round(np.array(MS), 1), axis=0)
        print('marking samples', len(MS), 'paint px', int(paint.sum()))
    def unpack(p):
        R_cw, _ = cv2.Rodrigues(p[:3]); return R_cw.T, p[3:6] / 1.0
    def Kof(p):
        Kp = K0.copy()
        if FREE_F: Kp[0, 0] = Kp[1, 1] = K0[0, 0] * p[6]
        return Kp
    def resid(p):
        Rw, tt = unpack(p); r = []; K = Kof(p)
        if len(X): uv, _ = project(K, Rw, tt, X); r.append(((uv - x) / 1.0).ravel())
        for n, pts in lines.items():
            uvl, zl = project(K, Rw, tt, L3[n]); uvl = uvl[zl > 0]
            if len(uvl) < 2: r.append(np.full(len(pts), 200.0)); continue
            a, b = uvl[:-1], uvl[1:]; ab = b - a
            for q in pts:
                tq = np.clip(((q - a) * ab).sum(1) / (ab * ab).sum(1), 0, 1)
                r.append([np.min(np.hypot(*(a + tq[:, None] * ab - q).T)) * 0.5])   # weight 0.5 per line point
        if MARK:
            uvm, zm = project(K, Rw, tt, MS)
            u, v = uvm[:, 0], uvm[:, 1]
            ok = (zm > 1) & (u >= 0) & (u < DT.shape[1] - 1) & (v >= V0) & (v < V1)
            dm = np.full(len(MS), CAP)
            dm[ok] = np.minimum(DT[v[ok].astype(int), u[ok].astype(int)], CAP)
            r.append(dm * MW)
        return np.concatenate([np.ravel(v) for v in r])
    rvec0, _ = cv2.Rodrigues(Rwc.T)
    p0 = np.concatenate([rvec0.ravel(), t] + ([[1.0]] if FREE_F else []))
    FIX_ROT = os.environ.get('P9_FIX_ROT') == '1'      # keep Mapillary's SfM rotation, solve the position only
    if FIX_ROT:
        full = p0.copy()
        r3 = lambda q: resid(np.concatenate([full[:3], q, full[6:]]))
        s3 = least_squares(r3, p0[3:6], loss='soft_l1', f_scale=8.0, x_scale=[1, 1, 0.3])
        full[3:6] = s3.x
        class _S: pass
        sol = _S(); sol.x = full
    else:
        sol = least_squares(resid, p0, loss='soft_l1', f_scale=8.0, x_scale=np.r_[0.01, 0.01, 0.01, 1, 1, 0.3, [0.01] * FREE_F])
    Rwc_s, t_s = unpack(sol.x); K = Kof(sol.x)
    if FREE_F: print('focal scale', round(float(sol.x[6]), 4), 'f_px', round(float(K[0, 0]), 1))
    if len(X): uv, z = project(K, Rwc_s, t_s, X); res = np.hypot(*(uv - x).T); res_ft = res * z / K[0, 0] / FT
    else: res = res_ft = np.zeros(0)
    # also report every named point that has a pick but was not used
    allp = [n for n in picks if n in P3]
    uva, za = project(K, Rwc_s, t_s, [P3[n] for n in allp])
    chk = {n: (round(float(np.hypot(*(uva[i] - picks[n]))), 1), round(float(np.hypot(*(uva[i] - picks[n])) * za[i] / K[0, 0] / FT), 2)) for i, n in enumerate(allp)}
    lr = resid(sol.x)[2 * len(names):2 * len(names) + sum(len(v) for v in lines.values())] / 0.5
    if MARK:
        mres = resid(sol.x)[-len(MS):] / MW; print('marking samples median px', round(float(np.median(mres)), 1), 'within 5 px', round(float((mres < 5).mean()), 2))
    fwd = Rwc_s @ [0, 0, 1]; up = Rwc_s @ [0, -1, 0]
    cams = json.load(open(CAMS))
    if FREE_F: cams[iid]['K_solved'] = K.round(3).tolist()
    cams[iid]['pose_solved'] = dict(loc_ft=(t_s / FT).round(3).tolist(), R_world_from_cv=Rwc_s.round(6).tolist(),
        heading_scene_deg=round(math.degrees(math.atan2(fwd[1], fwd[0])), 2), pitch_deg=round(math.degrees(math.asin(fwd[2])), 2),
        roll_deg=round(math.degrees(math.atan2(-np.cross(fwd, up)[2], up[2])), 2),
        points=names, lines={n: len(v) for n, v in lines.items()},
        residual_px={n: round(float(r), 1) for n, r in zip(names, res)},
        residual_ft={n: round(float(r), 2) for n, r in zip(names, res_ft)},
        check_px_ft=chk, line_median_px=round(float(np.median(lr)), 1) if len(lr) else None,
        rms_px=round(float(np.sqrt((res ** 2).mean())), 2) if len(res) else None, median_ft=round(float(np.median(res_ft)), 2) if len(res) else None)
    json.dump(cams, open(CAMS, 'w'), indent=1)
    d0 = np.array(cams[iid]['pose_init']['loc_ft'])
    print('solved', iid, 'loc ft', (t_s / FT).round(2), 'moved ft', (t_s / FT - d0).round(2),
          'pitch', cams[iid]['pose_solved']['pitch_deg'], 'roll', cams[iid]['pose_solved']['roll_deg'])
    print('rms px', cams[iid]['pose_solved']['rms_px'], 'line median px', cams[iid]['pose_solved']['line_median_px'])
    print('all picks (px, ft):', chk)
