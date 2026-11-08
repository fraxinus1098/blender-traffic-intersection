"""Phase 9B step 4: build the viewer images for the Mapillary photo overlays.
Run from the repo root (venv):  .venv/bin/python work/p9_photo_composite.py [<id> ...]   (default: all solved frames)
Inputs:  work/p9_photos/raw/<id>_undist.jpg (p9_photo_prep.py), work/p9_photos/render/<id>_{existing,proposed,removed}.png
         (p9_photo_render_blender.py at PCT = 50, i.e. half resolution), pose and credits in work/p9_photos/p9_cams.json.
Outputs (committed; CC BY-SA 4.0 like the photos):
  work/p9_photos/<id>_photo.jpg      the undistorted photo, half resolution, cropped above the hood and the dashcam text
  work/p9_photos/<id>_existing.png   RGBA overlay: existing signals and markings as modelled from the plans
  work/p9_photos/<id>_proposed.png   RGBA overlay: change view (new = green, remaining = untinted) plus a red outline
                                     around everything that the project removes (from the 'removed' render)
  work/p9_photos/p9_photos.json      per photo: credit, licence, capture date, crop, camera pose and residuals
  docs/images/p9_photo_<id>.jpg      check sheet: photo / existing / proposed composites stacked
"""
import json, sys, os, datetime
import numpy as np, cv2
from PIL import Image

D = 'work/p9_photos/'
CROP_V = 1920              # full-resolution rows kept (the hood starts at about v = 1970 in both frames)
SCALE = 0.5                # renders are at PCT = 50
cams = json.load(open(D + 'p9_cams.json'))
ids = sys.argv[1:] or [i for i, c in cams.items() if 'pose_solved' in c and os.path.exists(f'{D}render/{i}_existing.png')]
meta = json.load(open(D + 'p9_photos.json')) if os.path.exists(D + 'p9_photos.json') else {}
NAMES = {'28581715364843976': 'NB intersection, westbound Spring Cypress approach',
         '1503912631573961': 'SB intersection, westbound Spring Cypress, leaving the underpass'}
for iid in ids:
    C = cams[iid]; w, h = C['size']; W, H = int(w * SCALE), int(CROP_V * SCALE)
    photo = Image.open(f'{D}raw/{iid}_undist.jpg').convert('RGB').resize((int(w * SCALE), int(h * SCALE)), Image.LANCZOS).crop((0, 0, W, H))
    photo.save(f'{D}{iid}_photo.jpg', quality=88)
    ex = Image.open(f'{D}render/{iid}_existing.png').convert('RGBA').crop((0, 0, W, H))
    pr = np.array(Image.open(f'{D}render/{iid}_proposed.png').convert('RGBA').crop((0, 0, W, H)))
    rm = np.array(Image.open(f'{D}render/{iid}_removed.png').convert('RGBA').crop((0, 0, W, H)))[..., 3]
    ex.save(f'{D}{iid}_existing.png', optimize=True)
    # red outline of removed items: dilated mask minus the mask (a 3-px ring), skipped where a proposed item is drawn
    m = (rm > 40).astype(np.uint8)
    ring = (cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0) & (m == 0) & (pr[..., 3] < 128)
    out = pr.copy()
    out[ring] = (230, 20, 20, 255)
    Image.fromarray(out, 'RGBA').save(f'{D}{iid}_proposed.png', optimize=True)
    # check sheet
    def comp(ov):
        b = photo.convert('RGBA'); b.alpha_composite(ov if isinstance(ov, Image.Image) else Image.fromarray(ov, 'RGBA')); return b.convert('RGB')
    sheet = Image.new('RGB', (W, H * 3))
    for k, im in enumerate((photo, comp(ex), comp(out))): sheet.paste(im, (0, H * k))
    os.makedirs('docs/images', exist_ok=True)
    sheet.resize((W // 2, H * 3 // 2), Image.LANCZOS).save(f'docs/images/p9_photo_{iid}.jpg', quality=85)
    p = C['pose_solved']
    meta[iid] = dict(title=NAMES.get(iid, iid), creator=C.get('creator'), captured_at=datetime.datetime.fromtimestamp(C["captured_at"] / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                     source=f'https://www.mapillary.com/app/?pKey={iid}', licence='CC BY-SA 4.0',
                     credit=f"Photo: {C.get('creator')} via Mapillary, CC BY-SA 4.0. Overlay: this project, CC BY-SA 4.0.",
                     size=[W, H], crop_note=f'undistorted, scaled {SCALE}, rows 0-{CROP_V} of {h} (hood and dashcam text removed)',
                     camera=dict(loc_ft=p['loc_ft'], heading_scene_deg=p['heading_scene_deg'], pitch_deg=p['pitch_deg'],
                                 roll_deg=p['roll_deg'], hfov_deg=round(float(np.degrees(2 * np.arctan(w / 2 / C['K'][0][0]))), 1)),
                     solve_points=p['points'], solve_lines=p['lines'], check_px_ft=p['check_px_ft'], line_median_px=p['line_median_px'])
    print(iid, W, H, 'ring px', int(ring.sum()))
json.dump(meta, open(D + 'p9_photos.json', 'w'), indent=1)
