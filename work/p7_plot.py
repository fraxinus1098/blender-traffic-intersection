"""Phase 7 (container): overview plot of p7_data.json on the NAIP aerial (scene frame)."""
import json, sys, numpy as np, cv2, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, 'work'); import p6_common as C
D = json.load(open(sys.argv[1])); x0, x1, y0, y1 = [float(a) for a in sys.argv[2:6]]; out = sys.argv[6]
img = cv2.imread(C.U + 'imagery/SH249_SpringCypress_NAIP2022_60cm.tif')[:, :, ::-1]
res = 1.0; xs = np.arange(x0, x1, res); ys = np.arange(y1, y0, -res); X, Y = np.meshgrid(xs, ys)
r, c = C.scene_ft_to_aerial_px(X, Y)
A = cv2.remap(img, c.astype(np.float32), r.astype(np.float32), cv2.INTER_LINEAR)
fig, ax = plt.subplots(figsize=(14, 14 * (y1 - y0) / (x1 - x0)))
ax.imshow(A, extent=(x0, x1, y0, y1))
ax.plot([C.X0, C.X1, C.X1, C.X0, C.X0], [C.Y0, C.Y0, C.Y1, C.Y1, C.Y0], 'w--', lw=.8)
for z in D['zones']:
    col = 'cyan' if z['kind'] == 'PR' else 'magenta'
    for p in z['polys']: p = np.array(p); ax.fill(p[:, 0], p[:, 1], color=col, alpha=.35); ax.plot(p[:, 0], p[:, 1], color=col, lw=.8)
    ax.text(*z['label_xy'], z['id'], color='w', fontsize=8, ha='center', weight='bold')
    o = np.array(z['radar_xy']); a = np.radians(z['aim_deg']); ax.plot(*o, 'y^', ms=5)
    ax.plot([o[0], o[0] + 60 * np.cos(a)], [o[1], o[1] + 60 * np.sin(a)], 'y-', lw=.7)
for a in D['approaches']:
    for l in a['lanes']: ax.plot(*l['eye'], 'ro', ms=4); ax.plot(*l['bar_edge'], 'r.', ms=3)
    e = np.array(a['bar_ends']); ax.plot(e[:, 0], e[:, 1], 'r-', lw=1)
for cw in D['crosswalks']:
    p = np.array(cw['cam']); t = np.array(cw['target']); ax.plot(*p, 'gs', ms=5); ax.annotate('', t, p, arrowprops=dict(arrowstyle='->', color='lime', lw=.8))
    ax.text(p[0], p[1] - 6, cw['key'], color='lime', fontsize=7)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
plt.savefig(out, dpi=80, bbox_inches='tight')
