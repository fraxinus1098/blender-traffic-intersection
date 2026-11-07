import numpy as np
from scipy.ndimage import label, find_objects
from PIL import Image
p=np.load('plan_grid.npy')>.3
lab,n=label(p,structure=np.ones((3,3)))
keep=np.zeros_like(p)
for i,sl in enumerate(find_objects(lab),1):
    h=(sl[0].stop-sl[0].start); w=(sl[1].stop-sl[1].start)
    area=(lab[sl]==i).sum()
    diag=np.hypot(h,w)*0.25
    # long and thin: big extent, low fill
    if diag>18 and area/(h*w)<0.25: keep[sl]|=(lab[sl]==i)
np.save('plan_long.npy',keep.astype(np.float32))
Image.fromarray((255-keep*255).astype(np.uint8)).save('plan_long.png')
print(n,keep.sum(),p.sum())
