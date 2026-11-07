import numpy as np, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
U = ''
RES = 0.25
X0, X1, Y0, Y1 = -170.0, 200.0, -90.0, 90.0
NX, NY = int((X1 - X0) / RES), int((Y1 - Y0) / RES)
# sheet planes in Blender (metres): centre, size 207.264 x 134.112, 5100 x 3300 px
sheets = {38: (-46.8206672668457, 8.737600326538086), 39: (84.64973449707031, -6.1975998878479)}
W, H = 207.264, 134.112
plan = np.zeros((NY, NX), np.float32)
for s, (cx, cy) in sheets.items():
    a = np.array(Image.open(U + f'plans/masked/sheet{s}_SC_markings_existing_{1 if s==38 else 2}_mask.png'))
    from scipy.ndimage import maximum_filter
    alpha = maximum_filter(a[..., 3], size=7).astype(np.float32) / 255
    # grid pixel centres -> sheet pixel
    gx = X0 + (np.arange(NX) + .5) * RES
    gy = Y1 - (np.arange(NY) + .5) * RES
    u = ((gx - (cx - W / 2)) / W * 5100).astype(int)
    v = (((cy + H / 2) - gy) / H * 3300).astype(int)
    vu = (u >= 0) & (u < 5100); vv = (v >= 0) & (v < 3300)
    sub = alpha[np.ix_(v.clip(0, 3299), u.clip(0, 5099))]
    sub[~vv, :] = 0; sub[:, ~vu] = 0
    # use max-pool from full res to keep thin lines: approximate by dilating source first
    plan = np.maximum(plan, sub)
np.save('plan_grid.npy', plan)
Image.fromarray((255 - plan * 255).astype(np.uint8)).save('plan_grid.png')
print(NX, NY, plan.mean())
