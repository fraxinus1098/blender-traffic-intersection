"""Phase 7: stamp a legend on the change-view renders. Usage: python3 p7_legend.py <png> [...] (edits in place)."""
import sys
from PIL import Image, ImageDraw, ImageFont
ITEMS = [((217, 30, 24), 'Removed (existing, to be removed)'), ((40, 180, 50), 'New (proposed)'),
         ((150, 150, 150), 'Unchanged (remaining equipment, roadway, context)')]
for p in sys.argv[1:]:
    im = Image.open(p).convert('RGB'); W, H = im.size; s = W / 2400
    try: f = ImageFont.truetype('DejaVuSans.ttf', int(30 * s)); fb = ImageFont.truetype('DejaVuSans-Bold.ttf', int(32 * s))
    except OSError: f = fb = ImageFont.load_default()
    d = ImageDraw.Draw(im, 'RGBA'); x0, y0 = int(30 * s), H - int(290 * s)
    d.rectangle([x0, y0, x0 + int(1000 * s), H - int(30 * s)], fill=(255, 255, 255, 215), outline=(60, 60, 60, 255))
    d.text((x0 + int(20 * s), y0 + int(14 * s)), 'Change view - SH 249 at Spring Cypress', font=fb, fill=(20, 20, 20))
    for i, (c, t) in enumerate(ITEMS):
        y = y0 + int((66 + i * 46) * s)
        d.rectangle([x0 + int(20 * s), y, x0 + int(56 * s), y + int(32 * s)], fill=c, outline=(40, 40, 40))
        d.text((x0 + int(72 * s), y - int(2 * s)), t, font=f, fill=(20, 20, 20))
    d.text((x0 + int(20 * s), y0 + int(210 * s)), 'For illustration only - not for construction', font=f, fill=(90, 90, 90))
    im.save(p)
    print(p, im.size)
