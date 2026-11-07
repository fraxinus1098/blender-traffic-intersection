import json, numpy as np
from PIL import Image, ImageDraw
import sys; sys.path.insert(0,'.')
from p6_common import *
im = Image.open('p6_aerial_scene.png').convert('RGB'); dr = ImageDraw.Draw(im)
px = lambda X, Y: (X - CX0, CY1 - Y)
for b in json.load(open('p6_osm_buildings.json')):
    dr.polygon([px(*p) for p in b['ring']], outline=(255, 0, 0))
dr.rectangle([px(X0, Y1), px(X1, Y0)], outline=(0, 120, 255))
im.save('p6_bldg_overlay.png')
