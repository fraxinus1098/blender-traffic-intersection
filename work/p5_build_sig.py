"""Phase 5a: proposed signal equipment (sheets 26-27; details 28; LMA 67; notes 23) -> mesh JSON for Blender.
Helpers and mounting conventions copied from p4_build_sig.py so existing and proposed match.
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
        'MAT_Lum_Lens', 'MAT_GroundBox_Lid', 'MAT_Retro_Yellow', 'MAT_Radar']
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


objs = []


def emit(name, m, origin, coll, props):
    o = np.array(origin, float)
    V = (np.array(m.v) - o) * FT
    objs.append(dict(name=name, coll=coll, loc=list(o * FT), v=V.round(4).tolist(), f=m.f, mi=m.m, props=props))


def arm_z(s, L): return ARM_Z0 + ARM_RISE * s / L

# =============================================================== Phase 5a additions
FOUND_R = 2.0      # sheet 67: 48-A drilled shaft (48 in.)
PM_HEAD_Z = 15.8   # pole-mounted 5-section head housing centre (keeps backplate clear of the arm at 19.5 ft)
RADAR_POLE_Z = 22.0


def backplate(m, c, f, face_deg, w, h):
    """Black backplate with 2-in. (0.167 ft) yellow retroreflective border on the front (sheet 23 note 2)."""
    c = np.array(c, float)
    m.box(c - f * 0.43, (0.06, w, h), face_deg, 'MAT_SigHead_Black')
    m.box(c - f * 0.396, (0.008, w, h), face_deg, 'MAT_Retro_Yellow')
    m.box(c - f * 0.388, (0.008, w - 0.333, h - 0.333), face_deg, 'MAT_SigHead_Black')


def lens(m, p, f, face_deg, mat, arrow=None):
    """12-in. lens; arrow = unit vector (in the face plane) for an arrow indication."""
    if arrow is None:
        m.disc(p, f, 0.42, mat)
    else:
        m.disc(p, f, 0.42, 'MAT_SigHead_Black')
        q = np.array(p) + f * 0.01; a = np.array(arrow, float)
        m.box(q - a * 0.08, (0.01, 0.42, 0.14) if abs(a[2]) < 0.5 else (0.01, 0.14, 0.42), face_deg, mat) if False else None
        # shaft along a, head triangle at the tip
        side = np.cross(f, [0, 0, 1.0]); side = side / np.linalg.norm(side)
        perp = np.array([0, 0, 1.0]) if abs(np.dot(a, [0, 0, 1])) < 0.5 else side
        s0 = q - a * 0.30; s1 = q + a * 0.05
        w = 0.07
        m.add([s0 + perp * w, s1 + perp * w, s1 - perp * w, s0 - perp * w], [(0, 1, 2, 3), (0, 3, 2, 1)], mat)
        t = q + a * 0.32
        m.tri_plate([t, s1 + perp * 0.2, s1 - perp * 0.2], mat)
    m.box(np.array(p) + f * 0.35 + np.array([0, 0, 0.3]), (0.7, 0.95, 0.05), face_deg, 'MAT_SigHead_Black')  # visor


def head_h3p(m, c, face_deg):
    f = U(face_deg); left_drv = U(face_deg - 90)
    m.box(c, (0.75, 3.1, 1.15), face_deg, 'MAT_SigHead_Black')
    backplate(m, c, f, face_deg, 3.9, 1.95)
    for k, mat in zip((-1, 0, 1), ('MAT_Lens_Red', 'MAT_Lens_Yellow', 'MAT_Lens_Green')):
        lens(m, np.array(c) + f * 0.38 + left_drv * (-k) * 1.0, f, face_deg, mat)


def head_h4p(m, c, face_deg):
    """4-section horizontal flashing-yellow-arrow head: red, yellow, flashing yellow, green left arrows (driver's left to right).
    Sheet 28 labels the lenses <R <R <Y <G; the second <R is taken as a drafting slip for the flashing yellow arrow."""
    f = U(face_deg); left_drv = U(face_deg - 90)
    m.box(c, (0.75, 4.15, 1.15), face_deg, 'MAT_SigHead_Black')
    backplate(m, c, f, face_deg, 4.95, 1.95)
    for k, mat in zip((-1.5, -0.5, 0.5, 1.5), ('MAT_Lens_Red', 'MAT_Lens_Yellow', 'MAT_Lens_Yellow', 'MAT_Lens_Green')):
        lens(m, np.array(c) + f * 0.38 + left_drv * (-k) * 1.0, f, face_deg, mat, arrow=left_drv)


def head_v5p(m, c, face_deg):
    """5-section vertical: R, Y, G, Y right arrow, G right arrow (top to bottom)."""
    f = U(face_deg); right_drv = -U(face_deg - 90)
    m.box(c, (0.75, 1.15, 5.35), face_deg, 'MAT_SigHead_Black')
    backplate(m, c, f, face_deg, 1.95, 6.15)
    for k, mat, arr in zip((2, 1, 0, -1, -2), ('MAT_Lens_Red', 'MAT_Lens_Yellow', 'MAT_Lens_Green', 'MAT_Lens_Yellow', 'MAT_Lens_Green'),
                           (None, None, None, right_drv, right_drv)):
        lens(m, np.array(c) + f * 0.38 + np.array([0, 0, k * 1.04]), f, face_deg, mat, arrow=arr)


def radar_unit(m, c, aim_deg, kind):
    """PR = presence (~11x9x3 in.), ADV = advance (~15x11x4 in.); face towards aim."""
    f = U(aim_deg)
    w, h, d = (0.9, 0.75, 0.25) if kind == 'PR' else (1.25, 0.95, 0.33)
    m.box(c, (d, w, h), aim_deg, 'MAT_Radar')
    m.box(np.array(c) + f * (d / 2 + 0.005), (0.01, w - 0.12, h - 0.12), aim_deg, 'MAT_Cabinet')
    m.box(np.array(c) - f * (d / 2 + 0.12), (0.24, 0.25, 0.25), aim_deg, 'MAT_SigPole_Galv')   # swivel mount


# ----------------------------------------------------------------- data from sheets 26/27 (plan feet)
POLES = {  # pole centre, arm tip, luminaire direction (sunburst symbol), sheet, length label on plan
    'A': dict(sheet=26, xy=(-248.30, 41.46), tip=(-228.28, -9.61), lum=15, Lp=55),
    'B': dict(sheet=26, xy=(-166.00, -90.98), tip=(-112.56, -78.56), lum=120, Lp=55),
    'C': dict(sheet=26, xy=(-86.39, -62.55), tip=(-110.72, -13.39), lum=-179, Lp=55),
    'K': dict(sheet=27, xy=(286.10, -43.65), tip=(267.28, 7.89), lum=-159, Lp=55),
    'L': dict(sheet=27, xy=(206.84, 87.16), tip=(150.00, 68.33), lum=-75, Lp=60),
    'M': dict(sheet=27, xy=(130.99, 62.47), tip=(143.61, 9.06), lum=-71, Lp=55),
}
# head id: (pole, housing centre on plan, facing deg from plan arrow, type, pole-mounted?)
HEADS = {
    'T': ('A', (-236.88, 15.86), 5.9, 'h3', False), 'S': ('A', (-232.94, 4.56), 5.7, 'h3', False), 'R': ('A', (-228.81, -6.90), 5.5, 'h4', False),
    'Q': ('B', (-142.71, -83.80), 122.1, 'h3', False), 'P': ('B', (-129.58, -81.41), 122.2, 'h3', False), 'O': ('B', (-117.04, -78.86), 122.1, 'h3', False),
    'M': ('C', (-99.50, -38.54), -175.2, 'h3', False), 'L': ('C', (-104.82, -26.88), -175.2, 'h3', False), 'K': ('C', (-109.88, -15.57), -175.0, 'h3', False),
    'N': ('C', (-88.84, -61.13), -178.5, 'v5', True),
    'J': ('K', (275.31, -17.38), -175.5, 'h3', False), 'I': ('K', (271.38, -6.73), -175.6, 'h3', False), 'H': ('K', (268.19, 5.04), -174.7, 'h4', False),
    'E': ('L', (152.68, 68.46), -58.9, 'h3', False), 'F': ('L', (163.51, 71.68), -58.9, 'h3', False), 'G': ('L', (175.34, 74.96), -58.8, 'h3', False),
    'C': ('M', (138.36, 37.36), 5.5, 'h3', False), 'B': ('M', (140.58, 26.13), 5.6, 'h3', False), 'A': ('M', (142.80, 14.60), 5.5, 'h3', False),
    'D': ('M', (133.49, 61.64), -3.6, 'v5', True),
}
APPROACH = {'A': 'westbound Spring Cypress (SB feeder intersection)', 'B': 'southbound SH 249 feeder', 'C': 'eastbound Spring Cypress (SB feeder intersection)',
            'K': 'eastbound Spring Cypress (NB feeder intersection)', 'L': 'northbound SH 249 feeder', 'M': 'westbound Spring Cypress (NB feeder intersection)'}
# arm signs: id, pole, plan symbol centre, kind
ARMSIGNS = [('S2', 'A', (-239.81, 26.53)), ('S3', 'A', (-230.20, -0.90)), ('S1', 'B', (-151.34, -85.41)),
            ('S2', 'C', (-95.14, -49.44)), ('S4', 'C', (-102.24, -34.80)),
            ('S2', 'K', (277.43, -27.22)), ('S3', 'K', (269.00, -1.25)), ('S1', 'L', (192.01, 80.03)),
            ('S2', 'M', (137.12, 48.09)), ('S4', 'M', (139.79, 33.41))]
SIGNSPEC = {'S1': (8.0, 1.5, 'Spring Cypress Rd', 'S1 street name sign "Spring Cypress Rd", 96 x 18 in., white on green, 1.5-in. radius, 0.5-in. border (sheet 28).'),
            'S2': (4.0, 1.5, 'SH 249', 'S2 street name sign "SH 249", 48 x 18 in., white on green, 1.5-in. radius, 0.5-in. border (sheet 28).'),
            'S3': (3.0, 1.0, 'R6-1L', 'S3 R6-1L ONE WAY (left arrow), 36 x 12 in. (sheet 28).'),
            'S4': (3.0, 1.0, 'R6-1R', 'S4 R6-1R ONE WAY (right arrow), 36 x 12 in. (sheet 28).')}
# radar: id, pole, plan body centre, mount ('pole' or 'arm'), aim deg, schedule text
RADARS = [
    ('PR1', 'A', (-245.29, 42.47), 'pole', None, 'Designated for presence of southbound vehicles (SH 249)(feeder rd).'),
    ('PR2', 'B', (-167.90, -88.33), 'pole', None, 'Designated for presence of eastbound vehicles (Spring Cypress Rd).'),
    ('PR3', 'C', (-106.61, -20.78), 'arm', 57.0, 'Designated for presence of westbound vehicles (Spring Cypress Rd). Aim set toward the scheduled stop-bar zone (plan symbol shows no aim).'),
    ('ADV1', 'B', (-136.00, -79.80), 'arm', 122.1, 'Designated for southbound approaching vehicles (SH 249)(feeder rd).'),
    ('ADV2', 'C', (-106.10, -31.50), 'arm', -175.2, 'Designated for eastbound approaching vehicles (Spring Cypress Rd).'),
    ('PR4', 'M', (141.16, 21.31), 'arm', -114.0, 'Designated for presence of eastbound vehicles (Spring Cypress Rd). Aim set toward the scheduled stop-bar zone (plan symbol shows no aim).'),
    ('PR5', 'L', (208.57, 84.36), 'pole', None, 'Designated for presence of westbound vehicles (Spring Cypress Rd).'),
    ('PR6', 'K', (283.99, -45.93), 'pole', None, 'Designated for presence of northbound vehicles (SH 249)(feeder rd).'),
    ('ADV3', 'M', (142.50, 30.40), 'arm', 5.5, 'Designated for westbound approaching vehicles (Spring Cypress Rd). Callout M lists only a presence radar; ADV3 is kept on arm M as drawn on sheet 27 (it is in the radar schedule).'),
    ('ADV4', 'L', (170.50, 71.50), 'arm', -58.9, 'Designated for northbound approaching vehicles (SH 249)(feeder rd).'),
]
# APS pedestal poles: sheet, xy, [(ped head id, partner pole)], push button (id, sign type L/R/D)
PEDPOLES = {
    'D': (26, (-169.7, 53.3), [('P1', 'E')], ('PB1', 'L')), 'E': (26, (-233.8, 49.2), [('P2', 'D')], ('PB2', 'R')),
    'F': (26, (-240.8, 39.6), [('P3', 'G')], ('PB3', 'L')), 'G': (26, (-219.0, -8.1), [('P4a', 'F'), ('P4b', 'H')], ('PB4', 'D')),
    'H': (26, (-185.2, -77.6), [('P5', 'G')], ('PB5', 'R')), 'I': (26, (-173.9, -84.2), [('P6', 'J')], ('PB6', 'L')),
    'J': (26, (-95.8, -75.4), [('P7', 'I')], ('PB7', 'R')),
    'N': (27, (194.0, -56.0), [('P8', 'O')], ('PB8', 'L')), 'O': (27, (272.2, -51.2), [('P9', 'N')], ('PB9', 'R')),
    'P': (27, (279.3, -41.4), [('P10', 'Q')], ('PB10', 'L')), 'Q': (27, (259.8, 7.8), [('P11a', 'P'), ('P11b', 'R')], ('PB11', 'D')),
    'R': (27, (231.3, 76.5), [('P12', 'Q')], ('PB12', 'R')), 'S': (27, (217.8, 82.7), [('P13', 'T')], ('PB13', 'L')),
    'T': (27, (141.9, 63.5), [('P14', 'S')], ('PB14', 'L')),
}
TXT = {
    'A': 'Prop. 55 ft. mast arm pole with luminaire, street sign, and presence radar detector.',
    'B': 'Prop. 55 ft. mast arm pole with luminaire, street sign, presence radar detector and advance radar detector.',
    'C': 'Prop. 55 ft. mast arm pole with luminaire, street sign, pole-mounted signal head, presence radar detector and advance radar detector.',
    'K': 'Prop. 55 ft. mast arm pole with luminaire, street sign, and presence radar detector.',
    'L': 'Prop. 60 ft. mast arm pole with luminaire, street sign, presence radar detector and advance radar detector.',
    'M': 'Prop. 55 ft. mast arm pole with luminaire, street sign, pole-mounted signal head and presence radar detector.',
    'PED1': 'Prop. pedestal pole with pedestrian signal head, sign and push button (APS unit).',
    'PED2': 'Prop. pedestal pole with pedestrian signal heads (2 ea), sign and push button (APS unit).',
    'U': 'Prop. full-actuated controller w/cabinet, GPS module and battery back-up (BBU).',
    'V': 'Prop. electrical service pole Type D with meter, service (120/240 volt) and service disconnect. Elec serv ty D (120/240)060(NS)SS(E)SP(O) (sheet 28).',
}
HTYPE = {'h3': ('3sec', '3-section horizontal R-Y-G'), 'h4': ('4sec', '4-section horizontal flashing-yellow-arrow left-turn head (red, yellow, flashing yellow, green arrows)'),
         'v5': ('5secV', '5-section vertical R-Y-G with yellow and green right-turn arrows')}
COLL = 'P_Signals'
BASE = dict(sh249_status='new', sh249_phase='proposed')

for P, d in POLES.items():     # arm geometry
    x, y = d['xy']; tx, ty = d['tip']
    d['ad'] = math.degrees(math.atan2(ty - y, tx - x)); d['L'] = math.hypot(tx - x, ty - y)


def arm_pt(P, xy, drop):
    """Project plan xy onto the arm; return (point at arm centreline minus drop, s)."""
    d = POLES[P]; u = U(d['ad']); x, y = d['xy']
    s = (xy[0] - x) * u[0] + (xy[1] - y) * u[1]
    return np.array([x, y, 0]) + u * s + np.array([0, 0, arm_z(s, d['L']) - drop]), s


# ---- mast-arm poles with luminaire
for P, d in POLES.items():
    m = Mesh(); x, y = d['xy']; ad, L = d['ad'], d['L']; u = U(ad)
    foundation(m, d['xy'], FOUND_R)
    m.tube((x, y, ZB + 0.15), (x, y, ZB + POLE_H), 0.58, 0.42, 'MAT_SigPole_Galv', n=16)
    m.box((x, y, ZB + 0.35), (1.6, 1.6, 0.2), 0, 'MAT_SigPole_Galv')
    m.disc((x, y, ZB + POLE_H + 0.01), (0, 0, 1), 0.44, 'MAT_SigPole_Galv', n=16)
    p0 = np.array([x, y, ARM_Z0]) + u * 0.45; p1 = np.array([d['tip'][0], d['tip'][1], ARM_Z0 + ARM_RISE])
    m.tube(p0, p1, 0.5, 0.25, 'MAT_SigPole_Galv', n=12)
    m.box(np.array([x, y, ARM_Z0]) + u * 0.5, (0.15, 1.5, 1.8), ad, 'MAT_SigPole_Galv')
    lu = U(d['lum']); top = np.array([x, y, ZB + POLE_H - 0.6])
    mid = top + lu * 4.0 + np.array([0, 0, 1.2]); end = top + lu * LUM_ARM + np.array([0, 0, 1.6])
    m.tube(top, mid, 0.17, 0.14, 'MAT_SigPole_Galv', n=8); m.tube(mid, end, 0.14, 0.12, 'MAT_SigPole_Galv', n=8)
    lc = end + lu * 1.1 + np.array([0, 0, -0.1])
    m.box(lc, (2.4, 1.1, 0.55), d['lum'], 'MAT_SigPole_Galv'); m.box(lc + np.array([0, 0, -0.3]), (2.0, 0.9, 0.06), d['lum'], 'MAT_Lum_Lens')
    emit('P_MA_%s_%dft' % (P, d['Lp']), m, (x, y, ZB), COLL, dict(BASE, sh249_callout=P, sh249_sheet=d['sheet'],
         sh249_type='mast arm pole (30 ft pole with luminaire, %dL / %dIV fixed-mount arm, 8 ft luminaire arm; sheet 67)' % (d['Lp'], d['Lp']),
         sh249_arm_ft='%.1f' % L, sh249_note=TXT[P]))

# ---- vehicle heads
for hid, (P, bc, face, typ, pm) in HEADS.items():
    d = POLES[P]; x, y = d['xy']; m = Mesh()
    if pm:
        u = np.array([bc[0] - x, bc[1] - y, 0]); u /= np.linalg.norm(u)
        c = np.array([x, y, 0]) + u * 1.9 + np.array([0, 0, PM_HEAD_Z])
        head_v5p(m, c, face)
        for zz in (PM_HEAD_Z - 2.0, PM_HEAD_Z + 2.0):
            m.tube(np.array([x, y, zz]) + u * 0.5, np.array([c[0], c[1], zz]) - U(face) * 0.45, 0.08, 0.08, 'MAT_SigHead_Black', n=6)
        where = 'pole-mounted on mast arm pole %s, housing centred at 15.8 ft so the backplate clears the arm (plans give no height for pole-mounted heads)' % P
    else:
        ap, s = arm_pt(P, bc, 0.0)
        c = np.array([ap[0], ap[1], HEAD_BOT + 0.575])
        (head_h4p if typ == 'h4' else head_h3p)(m, c, face)
        m.tube(c + np.array([0, 0, 0.55]), ap, 0.09, 0.09, 'MAT_SigHead_Black', n=6)
        where = 'on mast arm %s, %.1f ft from the pole, bottom of housing 17 ft-6 in. above pavement' % (P, s)
    tn, tt = HTYPE[typ]
    if typ == 'h4': where += '; sheet 28 labels the lenses <R <R <Y <G, modeled as the standard FYA sequence (second <R taken as a drafting slip)'
    emit('P_HEAD_%s_%s' % (hid, tn), m, c, COLL, dict(BASE, sh249_callout=P, sh249_head=hid, sh249_sheet=d['sheet'],
         sh249_type='vehicle signal head, %s' % tt,
         sh249_note='Proposed signal head %s: %s, black housing, black backplate with 2-in. yellow retroreflective border (sheets 23, 28); %s; serves %s.' % (hid, tt, where, APPROACH[P])))

# ---- arm-mounted signs
signs_meta = []
for sid, P, sxy in ARMSIGNS:
    d = POLES[P]; w, h, legend, note = SIGNSPEC[sid]
    face = [hd[2] for hd in HEADS.values() if hd[0] == P and not hd[4]][0]
    ap, s = arm_pt(P, sxy, 0.5 + 0.1 + h / 2)
    m = Mesh(); f = U(face)
    if sid in ('S1', 'S2'):
        plate(m, ap, face, w, h, 0.08, 'MAT_Sign_Green', border='MAT_Sign_White')
    else:   # R6-1: black plate, white arrow
        plate(m, ap, face, w, h, 0.06, 'MAT_Sign_Black')
        sgn = -1 if sid == 'S3' else 1; rgt = -U(face - 90); q = ap + f * 0.05
        m.box(q + rgt * (-0.25 * sgn), (0.02, 2.05, 0.5), face, 'MAT_Sign_White')
        tip = q + rgt * (1.35 * sgn); b = q + rgt * (0.75 * sgn)
        m.tri_plate([tip, b + np.array([0, 0, 0.38]), b - np.array([0, 0, 0.38])], 'MAT_Sign_White')
    m.tube(ap + np.array([0, 0, h / 2]), ap + np.array([0, 0, h / 2 + 0.6]), 0.06, 0.06, 'MAT_SigPole_Galv', n=6)
    nm = 'P_SIGN_%s_%s' % (sid, P) if sid in ('S1', 'S2') else 'P_SIGN_%s_%s_%s' % (sid, P, legend)
    emit(nm, m, ap, COLL, dict(BASE, sh249_callout=sid, sh249_pole=P, sh249_sheet=d['sheet'],
         sh249_type='street name sign on mast arm' if sid in ('S1', 'S2') else 'regulatory sign on mast arm (R6-1)',
         sh249_note=note + ' On mast arm %s, %.1f ft from the pole.' % (P, s)))
    signs_meta.append(dict(name=nm, sid=sid, legend=legend, face=face, w=w, h=h, c=list(np.array(ap) * FT), t=0.08 if sid in ('S1', 'S2') else 0.06))

# ---- radar
for rid, P, bxy, mount, aim, sched in RADARS:
    d = POLES[P]; x, y = d['xy']; m = Mesh()
    if mount == 'pole':
        aim = math.degrees(math.atan2(bxy[1] - y, bxy[0] - x)); u = U(aim)
        c = np.array([x, y, RADAR_POLE_Z]) + u * 1.35
        radar_unit(m, c, aim, rid[:2] if rid.startswith('PR') else 'ADV')
        m.tube(np.array([x, y, RADAR_POLE_Z]) + u * 0.45, c - u * 0.25, 0.07, 0.07, 'MAT_SigPole_Galv', n=6)
        where = 'pole-mounted on mast arm pole %s at %.0f ft' % (P, RADAR_POLE_Z)
    else:
        ap, s = arm_pt(P, bxy, 0.0)
        c = ap + np.array([0, 0, -1.1])
        radar_unit(m, c, aim, 'PR' if rid.startswith('PR') else 'ADV')
        m.tube(c + np.array([0, 0, 0.4]), ap, 0.06, 0.06, 'MAT_SigPole_Galv', n=6)
        where = 'on mast arm %s, %.1f ft from the pole' % (P, s)
    kind = 'presence radar detector' if rid.startswith('PR') else 'advance radar detector'
    emit('P_RADAR_%s' % rid, m, c, COLL, dict(BASE, sh249_callout=rid, sh249_pole=P, sh249_sheet=d['sheet'], sh249_type=kind,
         sh249_aim_deg=round(aim, 1), sh249_note='Proposed %s %s (sheet 28 radar schedule): %s Mounted %s.' % (kind, rid, sched, where)))

# ---- APS pedestal poles
for P, (sh, xy, heads, (pbid, pbt)) in PEDPOLES.items():
    m = Mesh(); x, y = xy
    foundation(m, xy, 0.9)
    m.box((x, y, ZB + 0.15 + 0.6), (1.2, 1.2, 1.2), 45, 'MAT_SigPole_Galv')
    m.tube((x, y, ZB + 1.35), (x, y, ZB + PED_POLE_H), 0.19, 0.19, 'MAT_SigPole_Galv', n=10)
    m.disc((x, y, ZB + PED_POLE_H + 0.01), (0, 0, 1), 0.2, 'MAT_SigPole_Galv', n=10)
    faces = []
    for hid, partner in heads:
        px, py = PEDPOLES[partner][1]; fd = math.degrees(math.atan2(py - y, px - x)); faces.append(fd)
        ped_head(m, xy, ZB, 0.19, fd)
    c = faces[0]; pbf = c + 90 if pbt in ('L', 'D') else c - 90
    push_button(m, xy, ZB, 0.2, pbf)
    signt = {'L': 'R10-3eL', 'R': 'R10-3eR', 'D': 'R10-3eD'}[pbt]
    hd = ', '.join('%s facing %s' % (h, p) for h, p in heads)
    emit('P_PED_%s' % P, m, (x, y, ZB), COLL, dict(BASE, sh249_callout=P, sh249_sheet=sh,
         sh249_type='APS pedestal pole with countdown ped head(s) and push button',
         sh249_ped_heads=', '.join(h for h, _ in heads), sh249_push_button='%s (%s)' % (pbid, signt),
         sh249_note=(TXT['PED2'] if len(heads) == 2 else TXT['PED1']) + ' Ped head(s) %s across the crosswalk; push button %s with %s sign (sheet 28).' % (hd, pbid, signt)))

# ---- controller cabinet U (+ BBU)
x, y = 24.72, 59.78
m = Mesh()
m.box((x, y, ZB + 0.25), (6.0, 6.0, 0.5), 0, 'MAT_Concrete')
m.box((x, 58.78, ZB + 0.5 + 0.75), (3.8, 1.9, 1.5), 0, 'MAT_Concrete')          # 18-in. base (sheet 23 note 8)
m.box((x, 58.78, ZB + 2.0 + 2.6), (4.0, 2.0, 5.2), 0, 'MAT_Cabinet')
m.box((x, 58.78, ZB + 2.0 + 5.26), (4.3, 2.3, 0.12), 0, 'MAT_Cabinet')
m.box((x, 58.78 - 1.005, ZB + 4.6), (3.6, 0.01, 4.6), 0, 'MAT_GroundBox_Lid')   # door outline tone
emit('P_CTRL_U', m, (x, y, ZB), COLL, dict(BASE, sh249_callout='U', sh249_sheet=27, sh249_type='traffic signal controller cabinet',
     sh249_note=TXT['U'] + ' Cabinet on an 18-in. base (sheet 23 note 8).'))
m = Mesh()
m.box((x + 2.0 + 0.75, 58.78, ZB + 2.0 + 1.9), (1.5, 1.6, 3.4), 0, 'MAT_Cabinet')
m.box((x + 2.0 + 0.75, 58.78, ZB + 2.0 + 3.65), (1.7, 1.8, 0.1), 0, 'MAT_Cabinet')
emit('P_CTRL_U_BBU', m, (x + 2.75, 58.78, ZB + 2.0), COLL, dict(BASE, sh249_callout='U', sh249_sheet=27,
     sh249_type='battery back-up (BBU) cabinet', sh249_note='Battery back-up (BBU) cabinet, part of callout U: ' + TXT['U']))

# ---- electrical service pole V (Type D)
m = Mesh(); x, y = 195.70, 106.70
foundation(m, (x, y), 0.8)
m.tube((x, y, ZB + 0.15), (x, y, ZB + 16.0), 0.25, 0.22, 'MAT_SigPole_Galv', n=10)
m.box((x, y - 0.45, ZB + 5.0), (1.2, 0.5, 1.6), 0, 'MAT_Cabinet')
m.box((x + 0.9, y - 0.45, ZB + 4.6), (0.9, 0.45, 1.3), 0, 'MAT_Cabinet')
m.tube((x, y - 0.45, ZB + 5.8), (x, y - 0.45, ZB + 15.0), 0.06, 0.06, 'MAT_SigPole_Galv', n=6)
m.tube((x, y - 0.45, ZB + 15.0), (x, y - 0.45, ZB + 15.4), 0.12, 0.05, 'MAT_SigHead_Black', n=6)
emit('P_ELECSVC_V', m, (x, y, ZB), COLL, dict(BASE, sh249_callout='V', sh249_sheet=27, sh249_type='electrical service pole Type D',
     sh249_note=TXT['V']))

# ---- S5 R3-8L, ground-mounted
x, y, face = 245.47, 1.48, 180.0
m = Mesh()
m.box((x, y, ZB + 4.25), (0.2, 0.2, 8.5 + 0.6), face, 'MAT_SigPole_Galv')
c = np.array([x, y, ZB + 7.0 + 1.25]) + U(face) * 0.15; f = U(face); rgt = -U(face - 90)
plate(m, c, face, 2.5, 2.5, 0.06, 'MAT_Sign_White', border='MAT_Sign_Black')
q = c + f * 0.03
# left-turn-only arrow (left half): shaft up, then left, head pointing left
m.box(q + rgt * -0.45 + np.array([0, 0, -0.15]), (0.02, 0.14, 1.1), face, 'MAT_Sign_Black')
m.box(q + rgt * -0.65 + np.array([0, 0, 0.35]), (0.02, 0.45, 0.14), face, 'MAT_Sign_Black')
t = q + rgt * -1.0 + np.array([0, 0, 0.35]); b = q + rgt * -0.82 + np.array([0, 0, 0.35])
m.tri_plate([t, b + np.array([0, 0, 0.2]), b - np.array([0, 0, 0.2])], 'MAT_Sign_Black')
# through + left arrow (right half)
m.box(q + rgt * 0.55 + np.array([0, 0, -0.05]), (0.02, 0.14, 1.6), face, 'MAT_Sign_Black')
t = q + rgt * 0.55 + np.array([0, 0, 0.98]); b = q + rgt * 0.55 + np.array([0, 0, 0.75])
m.tri_plate([t, b + rgt * 0.2, b - rgt * 0.2], 'MAT_Sign_Black')
m.box(q + rgt * 0.38 + np.array([0, 0, 0.3]), (0.02, 0.35, 0.14), face, 'MAT_Sign_Black')
t = q + rgt * 0.08 + np.array([0, 0, 0.3]); b = q + rgt * 0.22 + np.array([0, 0, 0.3])
m.tri_plate([t, b + np.array([0, 0, 0.18]), b - np.array([0, 0, 0.18])], 'MAT_Sign_Black')
m.box(q + np.array([0, 0, 0]), (0.02, 0.05, 2.2), face, 'MAT_Sign_Black')   # divider line
emit('P_SIGN_S5_R3-8L', m, (x, y, ZB), COLL, dict(BASE, sh249_callout='S5', sh249_sheet=27, sh249_type='ground-mounted lane-use sign R3-8L',
     sh249_note='Proposed S5 R3-8L lane-use sign, 30 x 30 in. (sheets 27, 28). Detail 7 labels it S6; S5 is used per the main plan and sheet 28 (S6 is the R1-5BL on sheets 40-41). Ground-mounted on the median island east of the NB feeder intersection, facing eastbound traffic.'))
signs_meta.append(dict(name='P_SIGN_S5_R3-8L', sid='S5', legend='ONLY', face=face, w=2.5, h=2.5,
                       c=list((c + f * 0.03 + rgt * -0.62 + np.array([0, 0, -0.75])) * FT), t=0.06))

json.dump(dict(mats=MATS, objs=objs, signs=signs_meta), open('work/p5_proposed_signals.json', 'w'))
print(len(objs), 'objects;', sum(len(o['f']) for o in objs), 'faces')
for o in objs: print(o['name'], len(o['f']))
