"""Phase 6 shared helpers: scene <-> aerial / UTM / WGS84 mappings (from Phase 2)."""
import math, numpy as np
FT = 0.3048
U = ''
OE, ON = 250132.603, 3323063.683          # O_guess (UTM 15N)
DX, DY = -5.9, -2.1                       # fitted shift (m)
ROT = math.radians(-2.9668)               # plan -> UTM rotation
E0, N0 = OE + DX, ON + DY                 # ORIGIN_SC in UTM
UL_E, UL_N, PX = 249515.695, 3323477.014, 1233.771728515625 / 2000
# model extent (ft) and context margin
X0, X1, Y0, Y1 = -400, 560, -240, 210
MARGIN = 200
CX0, CX1, CY0, CY1 = X0 - MARGIN, X1 + MARGIN, Y0 - MARGIN, Y1 + MARGIN

def scene_ft_to_utm(X, Y):
    x, y = np.asarray(X) * FT, np.asarray(Y) * FT
    c, s = math.cos(ROT), math.sin(ROT)
    return E0 + c * x - s * y, N0 + s * x + c * y

def utm_to_scene_ft(E, N):
    e, n = np.asarray(E) - E0, np.asarray(N) - N0
    c, s = math.cos(-ROT), math.sin(-ROT)        # rotate by +2.9668 deg
    return (c * e - s * n) / FT, (s * e + c * n) / FT

def scene_ft_to_aerial_px(X, Y):
    E, N = scene_ft_to_utm(X, Y)
    return (UL_N - N) / PX - .5, (E - UL_E) / PX - .5     # row, col

def mask_class(F, X, Y, RES=0.25):
    """p3_rd_masks 'final' class at scene ft (vectorised); -1 outside extent."""
    X = np.asarray(X); Y = np.asarray(Y)
    r = ((Y1 - Y) / RES).astype(int); c = ((X - X0) / RES).astype(int)
    ok = (r >= 0) & (r < F.shape[0]) & (c >= 0) & (c < F.shape[1])
    out = np.full(X.shape, -1, np.int16)
    out[ok] = F[r[ok], c[ok]]
    return out
