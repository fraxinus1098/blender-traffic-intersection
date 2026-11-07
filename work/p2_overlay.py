import numpy as np, sys, math
from PIL import Image
from scipy.ndimage import map_coordinates
U = ''
RES = 0.25; X0, X1, Y0, Y1 = -170.0, 200.0, -90.0, 90.0
OE, ON = 250132.603, 3323063.683          # georef origin (current guess)
UL_E, UL_N, PX = 249515.695, 3323477.014, 1233.771728515625 / 2000
aer = np.array(Image.open(U + 'imagery/SH249_SpringCypress_NAIP2022_60cm.tif')).astype(np.float32)

def aerial_on_grid(dx=0, dy=0, rot_deg=0):
    """Sample aerial at plan-grid points after placing plans with rotation about origin then translation (dx,dy) metres."""
    plan = np.load('plan_grid.npy'); NY, NX = plan.shape
    gx = X0 + (np.arange(NX) + .5) * RES; gy = Y1 - (np.arange(NY) + .5) * RES
    GX, GY = np.meshgrid(gx, gy)
    t = math.radians(rot_deg); c, s = math.cos(t), math.sin(t)
    WX = c * GX - s * GY + dx; WY = s * GX + c * GY + dy
    col = (OE + WX - UL_E) / PX - .5; row = (UL_N - (ON + WY)) / PX - .5
    out = np.stack([map_coordinates(aer[..., k], [row, col], order=1) for k in range(3)], -1)
    return out, plan

if __name__ == '__main__':
    dx, dy, rot = map(float, sys.argv[1:4]); name = sys.argv[4]
    img, plan = aerial_on_grid(dx, dy, rot)
    o = img.copy()
    m = plan > .3
    o[m] = [255, 0, 255]
    Image.fromarray(o.clip(0, 255).astype(np.uint8)).save(name)
