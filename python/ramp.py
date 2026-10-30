# =====================================================================================================
#  ramp.py  --  the CHAPTER COLORS (blue to green), computed from Thoreau's words about the pond.
# =====================================================================================================
#  You can change the colors by editing the ANCHORS table below (and the matching QUOTES). Each anchor is
#  (position along the ramp from 0 to 1, Lightness, Chroma, Hue, a phrase). These numbers are in OKLCH:
#    Lightness 0 (black) to 1 (white); Chroma = how colorful; Hue = the color's angle on a wheel
#    (about 260 is blue, 140 is green). OKLCH is used because equal changes in its numbers look like equal changes
#    to the eye. Keep Lightness between about 0.32 and 0.57 so the lines stay visible on the old paper.
#  After editing, run  python3 check_ramp.py  to see whether the new ramp is still readable.

"""Chapter color ramp from Thoreau's own words about the color of Walden Pond.

Colors are interpolated in OKLCH between the anchors below, so steps are even to the eye, then
converted to sRGB (chroma is reduced if a color falls outside the sRGB gamut).
Lightness is kept between 0.38 and 0.57 on purpose: every step stays at least 3:1 against both a
bright page (#f4f1ea) and a yellowed one (#e9dcc0), and the slow rise in lightness gives readers who
cannot separate blue from green a second cue for the order.
"""
import math

# (position, L, C, hue in degrees, Thoreau's words from "The Ponds", "Solitude" and "Winter Animals")
# The seven anchor colors. The ramp blends smoothly between neighboring anchors.
ANCHORS = [
    (0.00, 0.32, 0.080, 262, "a darker blue than the sky itself; in stormy weather a dark slate color"),
    (0.20, 0.44, 0.120, 248, "the azure tint of its waters"),
    (0.40, 0.52, 0.125, 232, "more cerulean than the sky itself"),
    (0.58, 0.54, 0.105, 205, "a vitreous greenish blue"),
    (0.76, 0.55, 0.090, 180, "a misty bluish-green or glaucous color"),
    (0.88, 0.56, 0.125, 158, "the pure sea-green Walden water"),
    (1.00, 0.57, 0.145, 140, "a vivid green next the shore"),
]


# Exact words from the text (checked against clean.txt) for each anchor, with where they come from.
# Thoreau's exact words for each anchor, with where they come from. Shown when you hover the color bar.
QUOTES = [
    ("a darker blue than the sky itself", "The Ponds, of Walden; the dark end also draws on \u201ca dark slate color\u201d, said of ponds in stormy weather"),
    ("the azure tint of its waters", "Solitude, of Walden Pond"),
    ("more cerulean than the sky itself", "The Ponds, of Walden"),
    ("a vitreous greenish blue", "The Ponds, of Walden"),
    ("a misty bluish-green or glaucous color", "The Ponds, of White Pond"),
    ("the pure sea-green Walden water", "The Pond in Winter"),
    ("of a vivid green next the shore", "The Ponds, of Walden"),
]


# Converts an OKLCH color to the red/green/blue used by screens. Some OKLCH colors cannot be shown on a screen
#  ('out of gamut'); in that case the chroma is reduced a little at a time until the color fits, without changing
#  hue or lightness. (The long decimal numbers are the standard OKLab conversion matrix.)
def oklch_to_srgb(L, C, h):
    """Return (r, g, b) in 0..1, reducing chroma until the color is inside the sRGB gamut."""
    def conv(c):
        a, b = c * math.cos(math.radians(h)), c * math.sin(math.radians(h))
        l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        return (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
                -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
                -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    c = C
    rgb = conv(c)
    while c > 0 and any(v < -1e-6 or v > 1 + 1e-6 for v in rgb):
        c -= 0.002
        rgb = conv(c)
    enc = lambda v: 12.92 * v if v <= 0.0031308 else 1.055 * max(v, 0) ** (1 / 2.4) - 0.055
    return tuple(min(1.0, max(0.0, enc(v))) for v in rgb)


# Finds the blended color at any position t between 0 and 1 on the ramp.
def _lch_at(t):
    for (t0, L0, C0, h0, _), (t1, L1, C1, h1, _) in zip(ANCHORS, ANCHORS[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            return L0 + u * (L1 - L0), C0 + u * (C1 - C0), h0 + u * (h1 - h0)
    return ANCHORS[-1][1:4]


# Returns k hex colors. They are spaced by equal PERCEIVED distance along the ramp, not by equal position, because
#  spacing by position would make several chapters look the same around the 'glaucous' anchor.
def thoreau_ramp(k):
    """k hex colors, first = blue end, last = green end, spaced so that every step is the same
    perceived distance (equal OKLab distance along the anchor path). Without this the ramp stalls
    around the 'glaucous' anchor, where hue and lightness barely change."""
    n = 2000
    pts, dist = [], [0.0]
    for j in range(n + 1):
        L, C, h = _lch_at(j / n)
        pts.append((L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h))))
        if j:
            dist.append(dist[-1] + math.dist(pts[j], pts[j - 1]))
    out = []
    for i in range(k):
        target = dist[-1] * (i / (k - 1) if k > 1 else 0.0)
        j = next((q for q in range(n + 1) if dist[q] >= target), n)
        r, g, b = oklch_to_srgb(*_lch_at(j / n))
        out.append("#%02x%02x%02x" % (round(255 * r), round(255 * g), round(255 * b)))
    return out


# The anchors as the page needs them: hex color, position on the bar, quote and source.
def anchor_info():
    """For each anchor: hex color, position along the ramp (0..1, by equal perceived distance, so it lines up
    with where the chapters sit), and the quote with its source."""
    n = 2000
    dist, prev = [0.0], None
    for j in range(n + 1):
        L, C, h = _lch_at(j / n)
        pt = (L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))
        if prev is not None:
            dist.append(dist[-1] + math.dist(pt, prev))
        prev = pt
    out = []
    for (t, L, C, h, _), (quote, source) in zip(ANCHORS, QUOTES):
        r, g, b = oklch_to_srgb(L, C, h)
        out.append({"hex": "#%02x%02x%02x" % (round(255 * r), round(255 * g), round(255 * b)),
                    "pos": round(dist[round(t * n)] / dist[-1], 4), "quote": quote, "source": source})
    return out


if __name__ == "__main__":
    print(thoreau_ramp(18))
