"""Phase 6: tileable surface textures (numpy, periodic FFT noise) -> work/tex/p6_*.jpg
Each tile is seamless; Blender maps it through rastUVmap + Mapping scale (aerial 1233.77 x 826.63 m)/tile."""
import numpy as np, math, os
from PIL import Image, ImageDraw, ImageFilter
os.makedirs('tex', exist_ok=True)
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
def save(name, rgb, q=88):
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(f'tex/{name}.jpg', quality=q, optimize=True)

# --- asphalt: 2048 px over 8 m (3.9 mm/px). Aggregate grain, mottling, sealed cracks, a few stains.
n = 2048; rng = np.random.default_rng(1)
base = np.array([74, 74, 76], np.float32)                      # sRGB, weathered dense-graded asphalt
grain = rng.normal(size=(n, n)); grain = np.sign(grain) * np.abs(grain) ** 1.4
aggr = (rng.random((n, n)) > .985).astype(np.float32) * rng.uniform(25, 60, (n, n))   # light stones
aggr = np.array(Image.fromarray(aggr.astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) * .6
mott = fbm(n, 10, [(200, 1024, 1.0), (40, 200, .5)])
stains = np.clip(pnoise(n, 150, 600, 20) - 1.6, 0, None)
cracks = wrap_lines(n, crack_walks(n, 5, 3), 3, 3)             # crack sealant (dark, slightly glossy)
v = (base[None, None, :] + (grain * 6)[..., None] + aggr[..., None] * .7 + (mott * 3.5)[..., None]
     - (stains * 8)[..., None] - (cracks * 30)[..., None])
save('p6_asphalt', v)

# --- concrete (curb): 1024 px over 3 m. Light grey, pores, soft mottling, weathering stains.
def concrete(seed, base, n=1024, stain=14, pores=True):
    r = np.random.default_rng(seed)
    g = r.normal(size=(n, n)) * 3.5
    m = fbm(n, seed + 1, [(150, 512, 1.0), (30, 150, .45)]) * 5
    s = np.clip(pnoise(n, 120, 512, seed + 5) - 1.2, 0, None) * stain
    p = ((r.random((n, n)) > .996) * r.uniform(15, 35, (n, n))) if pores else 0
    return np.array(base, np.float32)[None, None] + (g + m - s - p)[..., None]
save('p6_concrete_curb', concrete(30, [168, 166, 160]))
# sidewalk: lighter broom-finish concrete (fine streaks along u), 1024 over 3 m
sw = concrete(40, [182, 179, 172], stain=10)
broom = np.repeat(np.random.default_rng(41).normal(size=(n // 2, 1)), 1024, 1)[:1024] * 2.5
save('p6_sidewalk', sw + broom[..., None])
# island / median concrete: slightly darker, more dirt
save('p6_island_conc', concrete(50, [150, 148, 141], stain=20))

# --- grass: 1024 px over 4 m. Green variation with dry/thin patches, blade speckle.
n = 1024; r = np.random.default_rng(60)
gm = fbm(n, 61, [(120, 512, 1.0), (25, 120, .6)])
dry = np.clip(pnoise(n, 100, 512, 66) - .6, 0, None)
spk = r.normal(size=(n, n))
green = np.array([62, 92, 38], np.float32); straw = np.array([128, 122, 74], np.float32)
t = np.clip(dry * .4, 0, .45)[..., None]
g = green * (1 - t) + straw * t
g = g * (1 + .07 * gm[..., None]) + (spk * 9)[..., None] * np.array([.6, 1, .4])
save('p6_grass', g)

# --- pavement paint wear: 512 px over 1.5 m (white and yellow). Paint with worn speckle to asphalt.
n = 512
wear = np.clip(fbm(n, 70, [(40, 256, 1.0), (6, 40, .7)]) * .5 + .15 + np.random.default_rng(71).normal(size=(n, n)) * .25, 0, 1)
wear = np.clip((wear - .72) * 2.0, 0, 1)                           # 0 = intact paint, 1 = asphalt showing
asph = np.array([70, 70, 72], np.float32)
for nm, col in (('p6_paint_white', [226, 226, 220]), ('p6_paint_yellow', [222, 170, 40])):
    c = np.array(col, np.float32)
    v = c * (1 - .55 * wear[..., None]) + asph * (.55 * wear[..., None])
    save(nm, v + np.random.default_rng(72).normal(size=(n, n, 1)) * 4)
for f in sorted(os.listdir('tex')): print(f, os.path.getsize('tex/' + f))
