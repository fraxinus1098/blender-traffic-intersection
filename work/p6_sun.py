"""Phase 6: solar position (NOAA algorithm) for ORIGIN_SC at the chosen render time -> scene sun vector."""
import math, datetime as dt
LAT, LON = 30.0130799, -95.5906606
WHEN = dt.datetime(2026, 4, 15, 15, 0, tzinfo=dt.timezone.utc)   # 10:00 CDT (UTC-5)
SCENE_Y_BEARING = 1.670                                           # scene +Y true bearing (deg)
def solar(lat, lon, t):
    jd = t.timestamp() / 86400 + 2440587.5; T = (jd - 2451545) / 36525
    L0 = (280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T); e = 0.016708634 - T * (0.000042037 + 1.267e-7 * T)
    Mr = math.radians(M)
    C = math.sin(Mr) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(2 * Mr) * (0.019993 - 0.000101 * T) + math.sin(3 * Mr) * 0.000289
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * T))
    eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60
    eps = eps0 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * T))
    dec = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam))))
    y = math.tan(math.radians(eps / 2)) ** 2
    L0r = math.radians(L0)
    eqt = 4 * math.degrees(y * math.sin(2 * L0r) - 2 * e * math.sin(Mr) + 4 * e * y * math.sin(Mr) * math.cos(2 * L0r)
                           - 0.5 * y * y * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * Mr))
    mins = t.hour * 60 + t.minute + t.second / 60
    tst = (mins + eqt + 4 * lon) % 1440
    ha = tst / 4 - 180
    lr, dr, hr = map(math.radians, (lat, dec, ha))
    cz = math.sin(lr) * math.sin(dr) + math.cos(lr) * math.cos(dr) * math.cos(hr)
    zen = math.degrees(math.acos(cz))
    az = math.degrees(math.atan2(math.sin(hr), math.cos(hr) * math.sin(lr) - math.tan(dr) * math.cos(lr))) + 180
    return 90 - zen, az % 360
el, az = solar(LAT, LON, WHEN)
az_s = az - SCENE_Y_BEARING                       # azimuth from scene +Y, clockwise
a = math.radians(az_s); e = math.radians(el)
to_sun = (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))
print(dict(elev=round(el, 2), az_true=round(az, 2), az_scene=round(az_s, 2), to_sun=[round(v, 4) for v in to_sun]))
