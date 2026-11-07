"""Phase 4: existing signal equipment (sheets 24-25) -> mesh JSON for Blender.
All plan coordinates in feet (scene frame). Output vertices in metres."""
import json, math
import numpy as np

FT = 0.3048
ZB = 0.5           # raised ground (curb/island/roadside top), ft
ARM_Z0 = 19.5      # arm centreline above pavement at the pole, ft
ARM_RISE = 1.0     # arm rise pole->tip, ft
HEAD_BOT = 17.5    # bottom of horizontal head housing above pavement (sheet 23 note 1)
POLE_H = 30.0      # mast-arm pole shaft (sheet 67 "30' poles with luminaire")
LUM_ARM = 8.0      # luminaire arm (sheet 67 parts list)
PED_POLE_H = 10.0
PB_Z = 3.75        # APS 3'-6"..4'-0" (sheet 23)

MATS = ['MAT_SigPole_Galv', 'MAT_SigHead_Black', 'MAT_Lens_Red', 'MAT_Lens_Yellow', 'MAT_Lens_Green',
        'MAT_PedLens', 'MAT_Sign_Green', 'MAT_Sign_White', 'MAT_Sign_Black', 'MAT_Cabinet', 'MAT_Concrete',
        'MAT_Lum_Lens', 'MAT_GroundBox_Lid']
MI = {m: i for i, m in enumerate(MATS)}


class Mesh:
    def __init__(s): s.v = []; s.f = []; s.m = []

    def add(s, verts, faces, mat):
        o = len(s.v); s.v += [list(map(float, p)) for p in verts]
        for f in faces: s.f.append([i + o for i in f]); s.m.append(MI[mat])

    def box(s, c, size, yaw_deg, mat, pitch_axis=None):
        """Box centred at c (ft), size (sx along local x, sy, sz), yaw about Z (deg)."""
        sx, sy, sz = [a / 2 for a in size]
        a = math.radians(yaw_deg); ca, sa = math.cos(a), math.sin(a)
        V = []
        for dz in (-sz, sz):
            for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                V.append((c[0] + dx * ca - dy * sa, c[1] + dx * sa + dy * ca, c[2] + dz))
        F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        s.add(V, F, mat)

    def tube(s, p0, p1, r0, r1, mat, n=12, caps=True):
        p0 = np.array(p0, float); p1 = np.array(p1, float); d = p1 - p0; L = np.linalg.norm(d); d /= L
        up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(d, up); u /= np.linalg.norm(u); w = np.cross(d, u)
        V = []
        for p, r in ((p0, r0), (p1, r1)):
            for k in range(n):
                t = 2 * math.pi * k / n; V.append(p + r * (math.cos(t) * u + math.sin(t) * w))
        F = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
        if caps:
            F.append(tuple(range(n - 1, -1, -1))); F.append(tuple(range(n, 2 * n)))
        s.add(V, F, mat)

    def disc(s, c, normal, r, mat, n=12):
        c = np.array(c, float); nn = np.array(normal, float); nn /= np.linalg.norm(nn)
        up = np.array([0, 0, 1.0]) if abs(nn[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(nn, up); u /= np.linalg.norm(u); w = np.cross(nn, u)
        V = [c + r * (math.cos(2 * math.pi * k / n) * u + math.sin(2 * math.pi * k / n) * w) for k in range(n)]
        s.add(V, [tuple(range(n))[::-1] if np.dot(np.cross(V[1] - V[0], V[2] - V[0]), nn) < 0 else tuple(range(n))], mat)

    def tri_plate(s, pts3, mat):
        s.add(pts3, [(0, 1, 2), (0, 2, 1)], mat)


def U(deg): a = math.radians(deg); return np.array([math.cos(a), math.sin(a), 0.0])


def plate(m, c, face_deg, w, h, t, mat_face, mat_back='MAT_Sign_Black', border=None):
    """Flat sign plate centred at c, face normal = face_deg."""
    m.box(c, (t, w, h), face_deg, mat_back)
    f = U(face_deg)
    if border:
        m.box(np.array(c) + f * (t / 2 + 0.005), (0.01, w, h), face_deg, border)
        m.box(np.array(c) + f * (t / 2 + 0.012), (0.01, w - 0.17, h - 0.17), face_deg, mat_face)
    else:
        m.box(np.array(c) + f * (t / 2 + 0.005), (0.01, w, h), face_deg, mat_face)


def head_h3(m, c, face_deg, one_way=None):
    """3-section horizontal head (12" lenses), housing centre c; R on driver's left."""
    f = U(face_deg); left_drv = U(face_deg - 90)   # driver looks along -f; driver's left = rot(-f, +90) = rot(f, -90)
    m.box(c, (0.75, 3.1, 1.15), face_deg, 'MAT_SigHead_Black')                     # housing
    m.box(np.array(c) - f * 0.42, (0.06, 3.9, 1.95), face_deg, 'MAT_SigHead_Black')  # backplate
    for k, mat in zip((-1, 0, 1), ('MAT_Lens_Red', 'MAT_Lens_Yellow', 'MAT_Lens_Green')):
        p = np.array(c) + f * 0.38 + left_drv * (-k) * 1.0
        m.disc(p, f, 0.42, mat)
        m.box(p + f * 0.35 + np.array([0, 0, 0.3]), (0.7, 0.95, 0.05), face_deg, 'MAT_SigHead_Black')  # visor top
    if one_way:   # R6-1 36x12 below the head; arrow direction from driver's view
        sc = np.array(c) + np.array([0, 0, -1.55]) - f * 0.3
        plate(m, sc, face_deg, 3.0, 1.0, 0.06, 'MAT_Sign_Black')
        sgn = -1 if one_way == 'L' else 1           # +1 = driver's right
        rgt = -left_drv
        a0 = sc + f * 0.05 + rgt * (-1.1 * sgn); a1 = sc + f * 0.05 + rgt * (0.9 * sgn)
        m.box((a0 + a1) / 2, (0.02, 1.6, 0.16), face_deg, 'MAT_Sign_White')
        tip = a1 + rgt * 0.3 * sgn
        m.tri_plate([tip, a1 + np.array([0, 0, 0.32]), a1 - np.array([0, 0, 0.32])], 'MAT_Sign_White')


def head_v4(m, c, face_deg):
    f = U(face_deg)
    m.box(c, (0.75, 1.15, 4.3), face_deg, 'MAT_SigHead_Black')
    m.box(np.array(c) - f * 0.42, (0.06, 1.95, 5.1), face_deg, 'MAT_SigHead_Black')
    for k, mat in zip((1.5, 0.5, -0.5, -1.5), ('MAT_Lens_Red', 'MAT_Lens_Yellow', 'MAT_Lens_Yellow', 'MAT_Lens_Green')):
        p = np.array(c) + f * 0.38 + np.array([0, 0, k * 1.0])
        m.disc(p, f, 0.42, mat)
        m.box(p + f * 0.35 + np.array([0, 0, 0.3]), (0.7, 0.95, 0.05), face_deg, 'MAT_SigHead_Black')


def ped_head(m, pole_xy, z_base, pole_r, face_deg):
    f = U(face_deg); c = np.array([pole_xy[0], pole_xy[1], z_base + 8.25]) + f * (pole_r + 0.5)
    m.box(c, (0.8, 1.5, 1.5), face_deg, 'MAT_SigHead_Black')
    m.box(c + f * 0.41, (0.02, 1.25, 1.25), face_deg, 'MAT_PedLens')
    m.box(c + f * 0.55 + np.array([0, 0, 0.6]), (0.3, 1.5, 0.05), face_deg, 'MAT_SigHead_Black')
    m.tube(c - f * 0.4, c - f * (0.4 + 0.1) - f * (pole_r * 0.0), 0.08, 0.08, 'MAT_SigHead_Black', n=6)


def push_button(m, pole_xy, z_base, pole_r, face_deg):
    f = U(face_deg); c = np.array([pole_xy[0], pole_xy[1], z_base + PB_Z]) + f * (pole_r + 0.12)
    m.box(c, (0.25, 0.42, 0.6), face_deg, 'MAT_SigHead_Black')
    m.disc(c + f * 0.13 + np.array([0, 0, 0.05]), f, 0.1, 'MAT_Lens_Yellow', n=8)
    plate(m, c + np.array([0, 0, 1.2]) - f * 0.05, face_deg, 0.75, 1.25, 0.04, 'MAT_Sign_White')   # R10-3e 9x15


def foundation(m, xy, r):
    m.tube((xy[0], xy[1], ZB - 0.3), (xy[0], xy[1], ZB + 0.15), r, r, 'MAT_Concrete', n=16)


# ----------------------------------------------------------------- data from sheets 24/25
POLES = {  # pole centre (ft), arms [(tip_x, tip_y)], luminaire direction deg, sheet
    'C': dict(sheet=24, xy=(-210.95, -10.30), arms=[(-156.22, -6.28), (-215.56, 21.39)], lum=None, dual=True),
    'E': dict(sheet=24, xy=(-99.50, -67.00), arms=[(-101.72, -23.17)], lum=90, dual=False),
    'K': dict(sheet=25, xy=(145.10, 65.60), arms=[(147.72, 21.78)], lum=-88, dual=False),
    'H': dict(sheet=25, xy=(252.45, 7.15), arms=[(198.72, -3.89), (257.78, -24.44)], lum=-88, dual=True),
}
# head letter: (pole, arm index or None for pole-mounted, bar centre, facing deg, type)
HEADS = {
    'P': ('C', 1, (-214.39, 21.45), -0.5, 'h3_oneway_L'),
    'N': ('C', 1, (-212.50, 9.20), -0.2, 'h3'),
    'M': ('C', None, (-209.07, -7.19), 22.5, 'v4'),
    'L': ('C', 0, (-177.00, -6.58), 111.5, 'h3'),
    'K': ('C', 0, (-159.18, -5.39), 110.4, 'h3'),
    'J': ('E', 0, (-102.56, -25.21), -176.4, 'h3_oneway_R'),
    'H': ('E', 0, (-102.56, -42.53), -176.2, 'h3'),
    'A': ('K', 0, (147.81, 42.16), -0.3, 'h3'),
    'B': ('K', 0, (148.63, 24.33), 0.0, 'h3_oneway_R'),
    'C': ('H', 0, (201.83, -4.32), -60.3, 'h3'),
    'D': ('H', 0, (221.33, -0.50), -60.3, 'h3'),
    'E': ('H', None, (251.03, 4.28), -146.6, 'v4'),
    'F': ('H', 1, (254.00, -9.59), 179.8, 'h3'),
    'G': ('H', 1, (256.73, -22.92), 179.8, 'h3_oneway_L'),
}
SNS = {'C': [(0, (-192.4, -7.15)), (1, (-211.25, 1.5))], 'E': [(0, (-102.18, -51.72))],
       'K': [(0, (147.64, 49.35))], 'H': [(0, (235.82, 2.0)), (1, (252.67, -2.7))]}
PEDHEADS = {  # pole letter -> ped head facing directions (deg); same count of push buttons
    'A': [180], 'B': [0, -52], 'D': [112, 23], 'C': [96, -52], 'E': [-177],
    'F': [4], 'G': [180, 120], 'J': [-62, -152], 'K': [25], 'H': [-86, 124]}
PEDPOLES = {'A': (24, (-161.63, 43.59)), 'B': (24, (-242.60, 42.70)), 'D': (24, (-174.83, -84.53)),
            'F': (25, (194.47, -51.59)), 'G': (25, (277.50, -49.50)), 'J': (25, (208.80, 91.60))}

CALLOUT_TXT = {
    'A': 'Existing pedestal pole with pedestrian signal head, pedestrian push button, pedestrian sign (to be removed).',
    'B': 'Existing pedestal pole with pedestrian signal head (2 ea), pedestrian push button (2 ea), pedestrian sign (2 ea) (to be removed).',
    'C': 'Existing dual mast arm pole with luminaire, signal head, street name sign, pedestrian signal head (2 ea), pedestrian push button, pedestrian sign (to be removed).',
    'D': 'Existing pedestal pole with pedestrian signal head (2 ea), pedestrian push button (2 ea), pedestrian sign (2 ea) (to be removed).',
    'E': 'Existing mast arm pole with luminaire, signal head, street name sign, pedestrian signal head, pedestrian push button, pedestrian sign (to be removed).',
    'F': 'Existing pedestal pole with pedestrian signal head, pedestrian push button, pedestrian sign (to be removed).',
    'G': 'Existing pedestal pole with pedestrian signal head (2 ea), pedestrian push button (2 ea), pedestrian sign (2 ea) (to be removed).',
    'H': 'Existing dual mast arm pole with luminaire, signal head, street name sign, pedestrian signal head (2 ea), pedestrian push button, pedestrian sign (to be removed).',
    'J': 'Existing pedestal pole with pedestrian signal head (2 ea), pedestrian push button (2 ea), pedestrian sign (2 ea) (to be removed).',
    'K': 'Existing mast arm pole with luminaire, signal head, street name sign, pedestrian signal head, pedestrian push button, pedestrian sign (to be removed).',
    'L': 'Existing signal controller (to be removed).',
    'M': 'Existing electrical service pole (verify and removed if not in service).',
}
HEAD_TYPE_TXT = {'h3': '3-section horizontal R-Y-G', 'h3_oneway_L': '3-section horizontal R-Y-G with ONE WAY (left) sign',
                 'h3_oneway_R': '3-section horizontal R-Y-G with ONE WAY (right) sign', 'v4': '4-section vertical'}

objs = []


def emit(name, m, origin, coll, props):
    o = np.array(origin, float)
    V = (np.array(m.v) - o) * FT
    objs.append(dict(name=name, coll=coll, loc=list(o * FT), v=V.round(4).tolist(), f=m.f, mi=m.m, props=props))


def arm_z(s, L): return ARM_Z0 + ARM_RISE * s / L


# ---- mast-arm poles
for P, d in POLES.items():
    m = Mesh(); x, y = d['xy']
    foundation(m, d['xy'], 1.5)
    m.tube((x, y, ZB + 0.15), (x, y, ZB + POLE_H), 0.58, 0.42, 'MAT_SigPole_Galv', n=16)
    m.box((x, y, ZB + 0.35), (1.6, 1.6, 0.2), 0, 'MAT_SigPole_Galv')
    m.disc((x, y, ZB + POLE_H + 0.01), (0, 0, 1), 0.44, 'MAT_SigPole_Galv', n=16)
    arm_dirs = []
    for i, (tx, ty) in enumerate(d['arms']):
        dx, dy = tx - x, ty - y; L = math.hypot(dx, dy); ad = math.degrees(math.atan2(dy, dx)); arm_dirs.append((ad, L))
        u = U(ad)
        zz = ARM_Z0 + (0.6 if i == 1 else 0.0)   # second arm of a dual sits slightly higher (clamp clearance)
        p0 = np.array([x, y, zz]) + u * 0.45
        p1 = np.array([tx, ty, zz + ARM_RISE])
        m.tube(p0, p1, 0.5, 0.25, 'MAT_SigPole_Galv', n=12)
        m.box(np.array([x, y, zz]) + u * 0.5, (0.15, 1.5, 1.8), ad, 'MAT_SigPole_Galv')   # arm flange plate
    lum = d['lum'] if d['lum'] is not None else arm_dirs[0][0]
    u = U(lum); top = np.array([x, y, ZB + POLE_H - 0.6])
    mid = top + u * 4.0 + np.array([0, 0, 1.2]); end = top + u * LUM_ARM + np.array([0, 0, 1.6])
    m.tube(top, mid, 0.17, 0.14, 'MAT_SigPole_Galv', n=8); m.tube(mid, end, 0.14, 0.12, 'MAT_SigPole_Galv', n=8)
    lc = end + u * 1.1 + np.array([0, 0, -0.1])
    m.box(lc, (2.4, 1.1, 0.55), lum, 'MAT_SigPole_Galv')
    m.box(lc + np.array([0, 0, -0.3]), (2.0, 0.9, 0.06), lum, 'MAT_Lum_Lens')
    # street-name signs on the arms (face = facing of heads on that arm)
    for ai, (sx, sy) in SNS[P]:
        ad, L = arm_dirs[ai]; u = U(ad)
        s = (sx - x) * u[0] + (sy - y) * u[1]
        hf = [h[3] for k, h in HEADS.items() if h[0] == P and h[1] == ai]
        face = hf[0] if hf else ad + 90
        zz = arm_z(s, L) + (0.6 if ai == 1 else 0.0)
        c = np.array([x, y, 0]) + u * s + np.array([0, 0, zz - 0.5 - 0.85])
        plate(m, c, face, 6.0, 1.5, 0.08, 'MAT_Sign_Green', border='MAT_Sign_White')
        m.tube(c + np.array([0, 0, 0.75]), c + np.array([0, 0, 1.35]), 0.06, 0.06, 'MAT_SigPole_Galv', n=6)
    # ped heads + push buttons on the pole
    for fd in PEDHEADS[P]:
        ped_head(m, d['xy'], ZB, 0.55, fd); push_button(m, d['xy'], ZB, 0.56, fd)
    nm = 'E_MA_%s_%s' % (P, ('Dual%dx%dft' % tuple(round(a[1]) for a in arm_dirs)) if d['dual'] else '%dft' % round(arm_dirs[0][1]))
    emit(nm, m, (x, y, ZB), 'E_Signals', dict(sh249_status='remove', sh249_phase='existing', sh249_callout=P,
         sh249_sheet=d['sheet'], sh249_type='dual mast arm pole' if d['dual'] else 'mast arm pole',
         sh249_arm_ft=', '.join('%.1f' % a[1] for a in arm_dirs), sh249_note=CALLOUT_TXT[P]))
    POLES[P]['arm_dirs'] = arm_dirs

# ---- vehicle heads
for hl, (P, ai, bc, face, typ) in HEADS.items():
    d = POLES[P]; x, y = d['xy']; m = Mesh()
    if ai is None:   # pole-mounted vertical head on a side bracket
        u = np.array([bc[0] - x, bc[1] - y, 0]); u /= np.linalg.norm(u)
        c = np.array([x, y, 0]) + u * 1.6 + np.array([0, 0, 16.6])
        head_v4(m, c, face)
        for zz in (14.8, 18.4):
            m.tube(np.array([x, y, zz]) + u * 0.5, np.array([c[0], c[1], zz]) - U(face) * 0.4, 0.08, 0.08, 'MAT_SigHead_Black', n=6)
    else:
        ad, L = d['arm_dirs'][ai]; u = U(ad)
        s = (bc[0] - x) * u[0] + (bc[1] - y) * u[1]
        zz = arm_z(s, L) + (0.6 if ai == 1 else 0.0)
        c = np.array([x, y, 0]) + u * s + np.array([0, 0, HEAD_BOT + 0.575])
        head_h3(m, c, face, one_way=('L' if typ.endswith('_L') else 'R') if 'oneway' in typ else None)
        m.tube(c + np.array([0, 0, 0.55]), np.array([c[0], c[1], zz]), 0.09, 0.09, 'MAT_SigHead_Black', n=6)
    tname = {'h3': '3sec', 'h3_oneway_L': '3sec_OneWay', 'h3_oneway_R': '3sec_OneWay', 'v4': '4secV'}[typ]
    emit('E_HEAD_%s_%s' % (hl, tname), m, c, 'E_Signals', dict(sh249_status='remove', sh249_phase='existing',
         sh249_callout=P, sh249_head=hl, sh249_sheet=d['sheet'], sh249_type='vehicle signal head',
         sh249_note='Existing signal head %s (%s) on pole %s (to be removed).' % (hl, HEAD_TYPE_TXT[typ], P)))

# ---- pedestal ped poles
for P, (sh, xy) in PEDPOLES.items():
    m = Mesh(); x, y = xy
    foundation(m, xy, 0.9)
    m.box((x, y, ZB + 0.15 + 0.6), (1.2, 1.2, 1.2), 45, 'MAT_SigPole_Galv')          # transformer base
    m.tube((x, y, ZB + 1.35), (x, y, ZB + PED_POLE_H), 0.19, 0.19, 'MAT_SigPole_Galv', n=10)
    m.disc((x, y, ZB + PED_POLE_H + 0.01), (0, 0, 1), 0.2, 'MAT_SigPole_Galv', n=10)
    for fd in PEDHEADS[P]:
        ped_head(m, xy, ZB, 0.19, fd); push_button(m, xy, ZB, 0.2, fd)
    emit('E_PED_%s' % P, m, (x, y, ZB), 'E_Signals', dict(sh249_status='remove', sh249_phase='existing', sh249_callout=P,
         sh249_sheet=sh, sh249_type='pedestal pole with ped head(s), push button(s)', sh249_note=CALLOUT_TXT[P]))

# ---- controller L
m = Mesh(); x, y = 8.11, 59.0
m.box((x, y, ZB + 0.25), (6.0, 6.0, 0.5), 0, 'MAT_Concrete')
m.box((8.11, 58.0, ZB + 0.5 + 2.75), (4.0, 2.0, 5.5), 0, 'MAT_Cabinet')
m.box((8.11, 58.0, ZB + 0.5 + 5.55), (4.3, 2.3, 0.12), 0, 'MAT_Cabinet')
emit('E_CTRL_L', m, (x, y, ZB), 'E_Signals', dict(sh249_status='remove', sh249_phase='existing', sh249_callout='L', sh249_sheet=25,
     sh249_type='signal controller cabinet', sh249_note=CALLOUT_TXT['L']))

# ---- electrical service poles M (two on sheet 25)
for i, xy in enumerate([(203.06, 98.58), (243.47, 75.81)], 1):
    m = Mesh(); x, y = xy
    foundation(m, xy, 0.8)
    m.tube((x, y, ZB + 0.15), (x, y, ZB + 16.0), 0.25, 0.22, 'MAT_SigPole_Galv', n=10)
    m.box((x, y - 0.45, ZB + 5.0), (1.2, 0.5, 1.6), 0, 'MAT_Cabinet')        # meter/disconnect
    m.tube((x, y - 0.45, ZB + 5.8), (x, y - 0.45, ZB + 15.0), 0.06, 0.06, 'MAT_SigPole_Galv', n=6)   # riser
    m.tube((x, y - 0.45, ZB + 15.0), (x, y - 0.45, ZB + 15.4), 0.12, 0.05, 'MAT_SigHead_Black', n=6)  # weatherhead
    emit('E_ELECSVC_M%d' % i, m, (x, y, ZB), 'E_Signals', dict(sh249_status='remove', sh249_phase='existing', sh249_callout='M',
         sh249_sheet=25, sh249_type='electrical service pole', sh249_note=CALLOUT_TXT['M']))

# ---- items that remain
REMAIN = 'E_Signals_Remain'
SIGNS = [  # name, sheet, xy (leader arrowhead), face deg, w, h
    ('E_SIGN_R3-8_UMS_SB', 24, (-179.13, 57.39), 111.0, 3.0, 2.5, 'Existing R3-8 UMS (to remain).'),
    ('E_SIGN_R3-8L_W', 24, (-207.85, -2.13), 180.0, 2.5, 2.5, 'Existing R3-8L (to remain).'),
    ('E_SIGN_R3-8L_CtrMedW', 24, (-79.06, -3.44), 0.0, 2.5, 2.5, 'Existing R3-8L (to remain).'),
    ('E_SIGN_R3-8R', 24, (-206.28, -75.13), 180.0, 2.5, 2.5, 'Existing R3-8R (to remain).'),
    ('E_SIGN_R3-8L_CtrMedE', 25, (147.78, 6.00), 180.0, 2.5, 2.5, 'Existing R3-8L (to remain).'),
    ('E_SIGN_R3-8_UMS_NB', 25, (203.00, -60.06), -60.3, 3.0, 2.5, 'Existing R3-8 UMS (to remain).'),
]
for nm, sh, xy, face, w, h, note in SIGNS:
    m = Mesh(); x, y = xy
    m.box((x, y, ZB + 4.25), (0.2, 0.2, 8.5 + 0.6), face, 'MAT_SigPole_Galv')
    plate(m, (x, y, ZB + 7.0 + h / 2) + U(face) * 0.15, face, w, h, 0.06, 'MAT_Sign_White', border='MAT_Sign_Black')
    emit(nm, m, (x, y, ZB), REMAIN, dict(sh249_status='remain', sh249_phase='existing', sh249_sheet=sh,
         sh249_type='ground-mounted regulatory sign', sh249_note=note))

ITS = [(24, (-155.88, 43.90), (3.17, 4.5)), (24, (-82.94, -69.62), (4.5, 3.17)), (24, (-42.98, -64.85), (4.5, 3.17)),
       (25, (15.73, 52.44), (4.5, 3.17)), (25, (33.91, -60.51), (4.5, 3.17)), (25, (102.57, -56.68), (4.5, 3.17)),
       (25, (128.84, 66.43), (4.5, 3.17))]
for i, (sh, xy, sz) in enumerate(ITS, 1):
    m = Mesh(); x, y = xy
    m.box((x, y, ZB - 0.2), (sz[0], sz[1], 0.5), 0, 'MAT_Concrete')
    m.box((x, y, ZB + 0.06), (sz[0] - 0.4, sz[1] - 0.4, 0.03), 0, 'MAT_GroundBox_Lid')
    emit('E_ITSGB_%d' % i, m, (x, y, ZB), REMAIN, dict(sh249_status='remain', sh249_phase='existing', sh249_sheet=sh,
         sh249_type='ITS ground box', sh249_note='Existing ITS ground box (to remain).'))

m = Mesh(); x, y = 89.28, -53.17
m.box((x, y, ZB + 0.25), (6.0, 6.0, 0.5), 0, 'MAT_Concrete')
m.box((x, y, ZB + 0.5 + 3.0), (4.0, 3.0, 6.0), 0, 'MAT_Cabinet')
m.box((x, y, ZB + 0.5 + 6.05), (4.3, 3.3, 0.12), 0, 'MAT_Cabinet')
emit('E_CTMS_Hub', m, (x, y, ZB), REMAIN, dict(sh249_status='remain', sh249_phase='existing', sh249_sheet=25,
     sh249_type='CTMS hub cabinet', sh249_note='Existing CTMS hub (to remain).'))

json.dump(dict(mats=MATS, objs=objs), open('work/p4_existing_signals.json', 'w'))
print(len(objs), 'objects;', sum(len(o['f']) for o in objs), 'faces')
for o in objs: print(o['name'], len(o['f']))
