# =====================================================================================================
#  prep_basemap.py  --  turns the georeferenced 1906 map (a .tif) into a web-sized JPEG, and prints its edges.
# =====================================================================================================
#  You only need this if you change the basemap picture. Run it once:
#    python3 prep_basemap.py walden_geo.tif concord.jpg --crop 264 264 4085 4060 --quality 78
#  It prints a line starting --basemap-bounds with four numbers. Those four numbers are the picture's south,
#  west, north and east edges; paste them into build_map.py (BASEMAP_BOUNDS). Needs the 'rasterio' package.
#  --crop trims the scan to the map frame (pixel numbers: left, top, right, bottom).

"""Turn a georeferenced GeoTIFF into a web-sized JPEG and print its lat/lon edges for make_map.py.

Usage: python3 prep_basemap.py in.tif out.jpg [--crop X0 Y0 X1 Y1] [--quality 80]
The GeoTIFF must be north-up (no rotation) and in Web Mercator (EPSG:3857), which the ArcGIS SDK can place exactly.
--crop is in image pixels; the printed bounds are for the cropped area.
"""
import argparse

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer

ap = argparse.ArgumentParser()
ap.add_argument("tif")
ap.add_argument("out")
ap.add_argument("--crop", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"))
ap.add_argument("--quality", type=int, default=80)
a = ap.parse_args()

# Open the georeferenced image.
r = rasterio.open(a.tif)
# Safety checks: the image must be in Web Mercator (EPSG:3857) and not rotated, or it cannot be laid on the map without warping.
assert r.crs.to_epsg() == 3857, f"expected EPSG:3857, got {r.crs}"
tf = r.transform
assert tf.b == 0 and tf.d == 0, "image is rotated; this script handles north-up images only"
# The crop window in image pixels (the whole image if --crop is not given).
x0, y0, x1, y1 = a.crop or (0, 0, r.width, r.height)
# Read just the cropped pixels.
arr = r.read(window=((y0, y1), (x0, x1)))
img = np.clip(np.moveaxis(arr, 0, 2), 0, 255).astype("uint8")
# Save them as a JPEG at the chosen quality.
Image.fromarray(img).save(a.out, quality=a.quality, optimize=True)

# Convert the crop's corner positions from Web Mercator meters to latitude and longitude.
to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
west, north = to_ll.transform(tf.c + x0 * tf.a, tf.f + y0 * tf.e)
east, south = to_ll.transform(tf.c + x1 * tf.a, tf.f + y1 * tf.e)
print(f"wrote {a.out}  {img.shape[1]} x {img.shape[0]} px")
# The four edge values the map build needs.
print(f"--basemap-bounds {south:.6f} {west:.6f} {north:.6f} {east:.6f}")
