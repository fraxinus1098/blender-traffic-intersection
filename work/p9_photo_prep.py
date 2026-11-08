"""Phase 9B step 1-2: undistort Mapillary perspective frames and convert Mapillary's SfM pose to the scene frame.
Run from the repo root:  .venv/bin/python work/p9_photo_prep.py <image_id> [<image_id> ...]
Inputs:  work/p9_photos/raw/<id>_orig.jpg and <id>_full.json (Graph API fields camera_parameters, computed_rotation,
         computed_geometry, computed_compass_angle, width, height).
Outputs: work/p9_photos/raw/<id>_undist.jpg (pinhole, same size and focal length), and an entry in
         work/p9_photos/p9_cams.json: {id: {K, size, pose_init: {loc_m, R_world_from_cv}, ...}}.
Camera model (OpenSfM 'perspective', as Mapillary reports it): normalised coords x = X/Z, r^2 = x^2 + y^2,
distorted = x (1 + k1 r^2 + k2 r^4), pixel = centre + f * max(w, h) * distorted. Same as OpenCV with dist = [k1, k2, 0, 0].
Pose: computed_rotation is an angle-axis R mapping topocentric ENU -> camera (x right, y down, z forward); the
scene's +Y has a true bearing of 1.670 deg (ORIGIN_SC), so ENU -> scene is a rotation by +1.670 deg about z."""
import json, sys, math, os
import numpy as np, cv2
from pyproj import Transformer
sys.path.insert(0, 'work')
from p6_common import utm_to_scene_ft, FT
RAW = 'work/p9_photos/raw/'
OUT = 'work/p9_photos/p9_cams.json'
EYE_M = 1.3                                   # dashcam height above the pavement (initial guess)
B = math.radians(1.670)
ENU2SCENE = np.array([[math.cos(B), -math.sin(B), 0], [math.sin(B), math.cos(B), 0], [0, 0, 1]])
# check: scene +Y in ENU should be (sin B, cos B): ENU2SCENE.T @ (0,1,0) = (sin B, cos B, 0)
assert np.allclose(ENU2SCENE.T @ np.array([0, 1, 0]), [math.sin(B), math.cos(B), 0])
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32615', always_xy=True)
cams = json.load(open(OUT)) if os.path.exists(OUT) else {}
for iid in sys.argv[1:]:
    J = json.load(open(RAW + f'{iid}_full.json'))
    w, h = J['width'], J['height']
    f, k1, k2 = J['camera_parameters']
    fp = f * max(w, h)
    K = np.array([[fp, 0, (w - 1) / 2], [0, fp, (h - 1) / 2], [0, 0, 1]])
    img = cv2.imread(RAW + f'{iid}_orig.jpg')
    assert img.shape[1] == w and img.shape[0] == h, img.shape
    und = cv2.undistort(img, K, np.array([k1, k2, 0, 0]), None, K)
    cv2.imwrite(RAW + f'{iid}_undist.jpg', und, [cv2.IMWRITE_JPEG_QUALITY, 92])
    R_cam_from_enu, _ = cv2.Rodrigues(np.array(J['computed_rotation'], float))
    R_world_from_cv = ENU2SCENE @ R_cam_from_enu.T          # scene <- camera(cv)
    fwd = R_world_from_cv @ np.array([0, 0, 1.0]); up = R_world_from_cv @ np.array([0, -1.0, 0])
    lon, lat = J['computed_geometry']['coordinates']
    E, N = to_utm.transform(lon, lat); X, Y = utm_to_scene_ft(E, N)
    heading_true = (math.degrees(math.atan2(*(ENU2SCENE.T @ fwd)[:2])) + 360) % 360
    pitch = math.degrees(math.asin(fwd[2])); roll = math.degrees(math.atan2(-np.cross(fwd, up)[2], up[2]))
    cams[iid] = dict(size=[w, h], K=K.tolist(), dist=[k1, k2], creator=J['creator']['username'],
                     captured_at=J['captured_at'], computed_compass_angle=J['computed_compass_angle'],
                     pose_init=dict(loc_ft=[round(float(X), 2), round(float(Y), 2), round(EYE_M / FT, 2)],
                                    R_world_from_cv=R_world_from_cv.round(6).tolist(),
                                    heading_true_deg=round(heading_true, 2), pitch_deg=round(pitch, 2), roll_deg=round(roll, 2)))
    print(iid, 'f_px', round(fp, 1), 'hfov', round(2 * math.degrees(math.atan(w / 2 / fp)), 1), 'scene ft', round(float(X), 1), round(float(Y), 1),
          'heading', round(heading_true, 1), '(compass', round(J['computed_compass_angle'], 1), ') pitch', round(pitch, 2), 'roll', round(roll, 2))
json.dump(cams, open(OUT, 'w'), indent=1)
