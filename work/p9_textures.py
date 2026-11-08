"""Phase 9A.3: jointed concrete pavement texture -> work/tex/p9_concrete_pave.jpg
Run from the repo root:  .venv/bin/python work/p9_textures.py
Tile: 2048 x 2048 px = 30 ft along the road (u) x 24 ft across (v), i.e. transverse sawn joints every 15 ft and
longitudinal joints every 12 ft (lane width). Blender maps it through the 'paveUV' layer (u = along / 30 ft,
v = across / 24 ft), so no Mapping node is needed. Same generator style as p6_textures.py (periodic FFT noise)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# --- helpers copied from p6_textures.py (that script writes its textures on import)
def pnoise(n, lo, hi, seed, power=1.0):
    """Periodic band-limited noise, wavelengths lo..hi pixels, normalised to sd 1."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    f = np.sqrt(f); f[0, 0] = 1e-9
    w = 1 / f
    amp = ((w >= lo) & (w <= hi)) * f ** (-power)
    z = np.fft.ifft2(np.fft.fft2(rng.normal(size=(n, n))) * amp).real
    return (z - z.mean()) / (z.std() + 1e-9)
def fbm(n, seed, scales):
    return sum(a * pnoise(n, lo, hi, seed + i) for i, (lo, hi, a) in enumerate(scales))
def wrap_lines(n, lines, width, seed):
    im = Image.new('L', (n, n), 0); dr = ImageDraw.Draw(im)
    for pts in lines:
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                dr.line([(x + ox, y + oy) for x, y in pts], fill=255, width=width)
    return np.array(im.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
def crack_walks(n, k, seed, steps=(60, 160), step=6):
    rng = np.random.default_rng(seed); out = []
    for _ in range(k):
        x, y = rng.uniform(0, n, 2); a = rng.uniform(0, 2 * math.pi); pts = [(x, y)]
        for _ in range(rng.integers(*steps)):
            a += rng.normal(0, .35); x += step * math.cos(a); y += step * math.sin(a); pts.append((x, y))
        out.append(pts)
    return out

n = 2048
PX_U = n / 30.0                      # px per ft along
PX_V = n / 24.0                      # px per ft across
r = np.random.default_rng(91)
base = np.array([124, 122, 116], np.float32)          # weathered PCC, from the 2026 dashcam frames (sRGB)
grain = r.normal(size=(n, n)) * 4.0
mott = fbm(n, 92, [(250, 1024, 1.0), (40, 250, .5)]) * 3.5
pores = (r.random((n, n)) > .995) * r.uniform(12, 30, (n, n))
# per-panel tone (2 x 2 panels per tile; image rows = v across, columns = u along)
panel = np.zeros((n, n), np.float32)
for i in range(2):
    for j in range(2):
        panel[i * n // 2:(i + 1) * n // 2, j * n // 2:(j + 1) * n // 2] = r.normal(0, 4.5)
# wheel paths: darker bands 3 ft and 9 ft from each longitudinal joint, oil-drip line between them (lane centre)
vv = (np.arange(n) / PX_V) % 12.0
wheel = np.exp(-((vv - 3.0) / 1.1) ** 2) + np.exp(-((vv - 9.0) / 1.1) ** 2)
drip = np.exp(-((vv - 6.0) / 0.9) ** 2)
lane = (wheel * 13 + drip * 6)[:, None] * (0.7 + 0.3 * (fbm(n, 93, [(200, 1024, 1.0)]) * .5 + .5))
stains = np.clip(pnoise(n, 150, 700, 94) - 1.4, 0, None) * 10
# sawn joints: dark sealant lines (transverse every 15 ft = columns 0, 1024; longitudinal every 12 ft = rows 0, 1024)
joints = np.zeros((n, n), np.float32)
for c in (0, n // 2):
    for w, a in ((2, 1.0), (5, .35)):
        joints[:, max(0, c - w):c + w] = np.maximum(joints[:, max(0, c - w):c + w], a)
        joints[max(0, c - w):c + w, :] = np.maximum(joints[max(0, c - w):c + w, :], a)
joints[:, n - 5:] = np.maximum(joints[:, n - 5:], .35); joints[n - 5:, :] = np.maximum(joints[n - 5:, :], .35)
joints = np.array(Image.fromarray((joints * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
cracks = wrap_lines(n, crack_walks(n, 3, 95, steps=(40, 90)), 2, 95)
# two patch repairs (darker, smoother rectangles inside panels)
patch = np.zeros((n, n), np.float32)
for (u0, v0, du, dv) in ((300, 1300, 380, 260), (1400, 300, 300, 420)):
    patch[v0:v0 + dv, u0:u0 + du] = 1
patch = np.array(Image.fromarray((patch * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
v = (base[None, None, :] + (grain + mott + panel - pores - lane - stains)[..., None]
     - (joints * 55)[..., None] - (cracks * 35)[..., None] - (patch * 14)[..., None])
os.makedirs('work/tex', exist_ok=True)
Image.fromarray(np.clip(v, 0, 255).astype(np.uint8)).save('work/tex/p9_concrete_pave.jpg', quality=88, optimize=True)
print('work/tex/p9_concrete_pave.jpg', os.path.getsize('work/tex/p9_concrete_pave.jpg'))
