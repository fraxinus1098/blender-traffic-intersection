"""Phase 9A.4: soften the horizon where the aerial ends -> work/tex/p9_aerial_fade.jpg
Run from the repo root:  .venv/bin/python work/p9_aerial_fade.py
The NAIP 2022 image (imagery/, 2000 x 1340, 0.617 m/px) with its outer 18 % on every side blended (smoothstep) to the
world's ground-haze colour seen just beyond the aerial in the renders (sRGB 180/187/193). The model extent and the
context margin (model + 60 m) lie well inside the untouched centre. MAT_Aerial_NAIP uses this copy since v11
(p9_horizon_blender.py); the GeoTIFF stays the source."""
import numpy as np
from PIL import Image
im = np.array(Image.open('imagery/SH249_SpringCypress_NAIP2022_60cm.tif').convert('RGB')).astype(np.float32)
H, W = im.shape[:2]
BAND, HAZE = 0.18, np.array([180, 187, 193], np.float32)
def ramp(n):
    t = np.minimum(np.arange(n) + .5, n - np.arange(n) - .5) / (BAND * n)     # 0 at the edge -> 1 inside the band
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
w = np.minimum.outer(ramp(H), ramp(W))[..., None]
out = im * w + HAZE * (1 - w)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save('work/tex/p9_aerial_fade.jpg', quality=92)
print('work/tex/p9_aerial_fade.jpg', out.shape)
