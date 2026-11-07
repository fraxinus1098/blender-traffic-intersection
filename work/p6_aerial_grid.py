"""Resample NAIP into the scene frame (1 ft/px) over the context extent -> p6_aerial_scene.npz"""
import sys, numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
sys.path.insert(0, '.')
from p6_common import *
img = np.array(Image.open(U + 'imagery/SH249_SpringCypress_NAIP2022_60cm.tif').convert('RGB')).astype(np.float32)
R = 1.0
xs = np.arange(CX0, CX1, R) + R / 2; ys = np.arange(CY1, CY0, -R) - R / 2
GX, GY = np.meshgrid(xs, ys)
row, col = scene_ft_to_aerial_px(GX, GY)
rgb = np.stack([map_coordinates(img[..., k], [row, col], order=1) for k in range(3)], -1)
np.savez_compressed('p6_aerial_scene.npz', rgb=rgb.astype(np.uint8), x0=CX0, y1=CY1, res=R)
Image.fromarray(rgb.astype(np.uint8)).save('p6_aerial_scene.png')
print(rgb.shape)
