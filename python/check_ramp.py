# =====================================================================================================
#  check_ramp.py  --  tests whether the chapter colors are readable. Run:  python3 check_ramp.py
# =====================================================================================================
#  It prints, for each of the 18 colors: its lightness, its contrast against a bright and a yellowed page
#  (the target is at least 3.0), and how different it is from the next color for normal vision and for two kinds
#  of red-green color blindness (simulated). Run it after editing ramp.py.

"""Check the chapter ramp: contrast against two page colors, lightness order, neighbor separation
(normal vision and simulated protan/deutan, Machado 2009 severity 1.0), and end-to-end separation.

Usage: python3 check_ramp.py [k]   (default 18)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramp as R

# The two page colors the lines must stand out against.
PAGES = {"bright page": "#f4f1ea", "yellowed page": "#e9dcc0"}
# Matrices that simulate deuteranopia and protanopia (two kinds of red-green color blindness).
M = {"deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
     "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]}


def rgb(h): return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def enc(x): return 12.92 * x if x <= 0.0031308 else 1.055 * max(x, 0) ** (1 / 2.4) - 0.055
def lum(h): r, g, b = map(lin, rgb(h)); return 0.2126 * r + 0.7152 * g + 0.0722 * b
# Contrast ratio between two colors (the standard web accessibility formula).
def contrast(a, b): ya, yb = lum(a), lum(b); return (max(ya, yb) + 0.05) / (min(ya, yb) + 0.05)


# Converts a hex color to OKLab, where distance between numbers matches how different two colors look.
def oklab(h):
    r, g, b = map(lin, rgb(h))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


# Color difference: distance in OKLab, times 100. Bigger means easier to tell apart.
def de(a, b): return 100 * math.dist(oklab(a), oklab(b))


# Simulates how a color looks to someone with the given color blindness.
def sim(h, kind):
    v = [lin(x) for x in rgb(h)]
    o = [min(1, max(0, enc(sum(M[kind][i][j] * v[j] for j in range(3))))) for i in range(3)]
    return "#%02x%02x%02x" % tuple(round(255 * x) for x in o)


# How many colors to test (18 chapters by default).
k = int(sys.argv[1]) if len(sys.argv) > 1 else 18
cols = R.thoreau_ramp(k)
print(cols)
print("\n  #  hex       L      contrast (bright / yellowed)   dE to next: normal  deutan  protan")
for i, c in enumerate(cols):
    nxt = ""
    if i < k - 1:
        n = cols[i + 1]
        nxt = f"{de(c, n):6.1f} {de(sim(c, 'deutan'), sim(n, 'deutan')):7.1f} {de(sim(c, 'protan'), sim(n, 'protan')):7.1f}"
    print(f"{i + 1:>3}  {c}  {oklab(c)[0]:.3f}   {contrast(c, '#f4f1ea'):5.2f} / {contrast(c, '#e9dcc0'):5.2f}"
          f"{'':>14}{nxt}")
adj = [de(a, b) for a, b in zip(cols, cols[1:])]
adj_d = [de(sim(a, "deutan"), sim(b, "deutan")) for a, b in zip(cols, cols[1:])]
adj_p = [de(sim(a, "protan"), sim(b, "protan")) for a, b in zip(cols, cols[1:])]
print(f"\nmin contrast: bright {min(contrast(c, PAGES['bright page']) for c in cols):.2f}, "
      f"yellowed {min(contrast(c, PAGES['yellowed page']) for c in cols):.2f}  (target >= 3.0)")
print("lightness never decreases:", all(oklab(a)[0] <= oklab(b)[0] + 1e-9 for a, b in zip(cols, cols[1:])))
print(f"neighbor dE: normal min {min(adj):.1f} / mean {sum(adj) / len(adj):.1f}; "
      f"deutan min {min(adj_d):.1f}; protan min {min(adj_p):.1f}")
print(f"first vs last: normal {de(cols[0], cols[-1]):.1f}, deutan {de(sim(cols[0], 'deutan'), sim(cols[-1], 'deutan')):.1f}, "
      f"protan {de(sim(cols[0], 'protan'), sim(cols[-1], 'protan')):.1f}")
