# =====================================================================================================
#  walk_punct.py  --  the HEADING ENGINE and the PUNCTUATION lens rules.
# =====================================================================================================
#  This file does two jobs for the map:
#    1. It defines the 8 compass headings (N, NE, E ...) as two small lists, SIN and COS, that every lens reuses.
#    2. It holds the Punctuation rules: which marks turn the turtle, and by how much.
#
#  THE RULES YOU MAY WANT TO EDIT are just below, under "rules (edit here)": three sets of characters
#  (LOWER, UPPER, MIDDLE) and the turn each set causes. Move a character from one set to another, or change
#  the numbers 90, -90 and 45, then rebuild the map.
#
#  make_lenses.py uses: normalize_with_map, chapter_of_step, walk, clusters, SIN, COS, TURN and the three sets.
#  The rest (report, plot, write_geojson, selftest, main) is for running this file on its own to make a quick
#  picture or to test it; the map does not need them. Run  python3 walk_punct.py --selftest  to run the tests.

"""Punctuation lens v1.

The walk sees only characters, not words or meaning.
  - Every character (spaces included) is one 1 m step.
  - Order: step first, then turn.
  - Lower marks turn right 90, upper marks turn left 90, middle marks turn right 45.
  - A run of 2+ marks with no space between is a cluster and gets one dot at its end;
    dot size steps up with cluster size (2 marks = small dot, 3 = larger, ...).
  - A spaced ellipsis (". . .", 3+ periods separated by single spaces) is one cluster too.
  - With --chapters, line and dots take one color per chapter.

Usage:
  python walk_punct.py clean.txt --out outdir [--title T] [--chapters chapters.json]
                       [--start LAT LON --epsg N]
  python walk_punct.py --selftest

chapters.json: [{"index": 1, "title": "...", "start": <character offset in the raw text file>}, ...]
"""
import argparse
import json
import math
import re
from collections import Counter

import numpy as np

# ---------------- rules (edit here) ----------------
# Marks that sit low on the line of type. Each turns the turtle 90 degrees to the RIGHT (clockwise).
LOWER = set(",._")                                              # right 90
# Marks that sit high on the line. Each turns the turtle 90 degrees to the LEFT.
UPPER = set("'\"*^`‘’“”")                   # left 90
# Marks that run the full height of the line. Each turns the turtle 45 degrees to the RIGHT.
MIDDLE = set("!@#$%&()<>?|+=-:;/\\[]{}~–—·")     # right 45

# TURN is a lookup table built from the three sets: character -> degrees (negative = left). Any character not in the table never turns.
TURN = {}
for _c in LOWER:
    TURN[_c] = 90
for _c in UPPER:
    TURN[_c] = -90
for _c in MIDDLE:
    TURN[_c] = 45
# PUNCT is the set of all turning marks. PUNCT_CLASS (next line) is the same thing written as a search pattern.
PUNCT = set(TURN)
PUNCT_CLASS = "[" + re.escape("".join(sorted(PUNCT))) + "]"

# The 8 headings. A heading number is degrees divided by 45: 0 = north, 1 = northeast, 2 = east ... 7 = northwest.
#  One step of 1 meter moves SIN[h] meters east and COS[h] meters north. A diagonal step moves 0.707 m (that is
#  sqrt(2)/2) along each axis, so it is still 1 m long.
_S2 = math.sqrt(2) / 2
SIN = np.array([0, _S2, 1, _S2, 0, -_S2, -1, -_S2])   # heading index = degrees / 45, 0 = north
COS = np.array([1, _S2, 0, -_S2, -1, -_S2, 0, _S2])


# Cleans up the text: whitespace runs become one space and the ellipsis character becomes three periods.
def normalize(raw):
    """The ellipsis character becomes three periods; every whitespace run becomes one space."""
    return normalize_with_map(raw, [])[0]


# Same cleanup, but also converts positions (like chapter starts) from the old text to the new text, since characters were added or removed.
def normalize_with_map(raw, offsets):
    """Normalize and also translate character offsets of `raw` into offsets of the result."""
    out, m, n = [], [0] * (len(raw) + 1), 0
    for i, ch in enumerate(raw):
        m[i] = n
        if ch.isspace():
            if n > 0 and out[-1] != " ":
                out.append(" ")
                n += 1
        elif ch == "…":
            out.append("...")
            n += 3
        else:
            out.append(ch)
            n += 1
    text = "".join(out)
    if text.endswith(" "):
        text = text[:-1]
    m[len(raw)] = len(text)
    return text, [min(m[o], max(len(text) - 1, 0)) for o in offsets]


# Lists any character that is not a letter, digit, space or known mark, so nothing unexpected sneaks in.
def census(text):
    """Characters that are not letters, digits, spaces or covered by a rule."""
    return Counter(ch for ch in text if not ch.isalnum() and ch != " " and ch not in PUNCT)


# THE WALK. turns[i] is how much character i turns the turtle (0 for most characters).
#  before[i] is the total of all turns BEFORE character i, which is the heading character i's step uses
#  (step first, then turn). idx converts that to one of the 8 headings. The cumulative sums of SIN and COS give
#  the position after every step. Returns x, y (meters from the start) and the final heading in degrees.
def walk(text):
    """Return x, y (meters from start, length len(text)+1) and the final heading in degrees."""
    turns = np.fromiter((TURN.get(c, 0) for c in text), dtype=np.int64, count=len(text))
    before = np.concatenate(([0], np.cumsum(turns)[:-1]))     # heading each step uses
    idx = (before % 360) // 45
    x = np.concatenate(([0.0], np.cumsum(SIN[idx])))
    y = np.concatenate(([0.0], np.cumsum(COS[idx])))
    return x, y, int(turns.sum() % 360)


# Finds the clusters that become points: runs of 2 or more marks with no space between them, plus the 'spaced
#  ellipsis' (three or more periods separated by single spaces), which counts as one run. Returns (start, end, size).
def clusters(text):
    """List of (start, end, size): index of first and last mark, and number of marks."""
    iv = [[m.start(), m.end() - 1] for m in re.finditer(PUNCT_CLASS + "+", text)]
    iv += [[m.start(), m.end() - 1] for m in re.finditer(r"\.(?: \.){2,}", text)]
    iv.sort()
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out = []
    for a, b in merged:
        size = sum(1 for c in text[a:b + 1] if c in PUNCT)
        if size >= 2:
            out.append((a, b, size))
    return out


# An independent second count of the clusters, used by the tests to make sure the first count is right.
def cluster_check(text):
    """Independent count: close up spaced ellipses, then count plain adjacent runs."""
    t = re.sub(r"\.(?: \.){2,}", lambda m: m.group(0).replace(" ", ""), text)
    return Counter(len(m.group(0)) for m in re.finditer(PUNCT_CLASS + "{2,}", t))


# Counts the marks to predict the final heading, as a cross-check on walk().
def expected_heading(text):
    low = sum(text.count(c) for c in LOWER)
    up = sum(text.count(c) for c in UPPER)
    mid = sum(text.count(c) for c in MIDDLE)
    return (90 * low - 90 * up + 45 * mid) % 360


# For each step, which chapter (0-based) it falls in. searchsorted finds where each step sits among the chapter start positions.
def chapter_of_step(n_steps, starts):
    """Chapter number (0-based) for each step i = character i."""
    return np.clip(np.searchsorted(np.array(starts), np.arange(n_steps), side="right") - 1, 0, None)


# Prints statistics when this file is run on its own.
def report(text, x, y, heading, cl, chapters=None, starts=None):
    print(f"characters (= steps): {len(text)}   path points: {len(x)}")
    print(f"final heading: walk {heading}  counted {expected_heading(text)}")
    sizes = Counter(s for _, _, s in cl)
    print(f"clusters: {len(cl)}  by size {dict(sorted(sizes.items()))}")
    chk = cluster_check(text)
    print(f"cluster cross-check: {dict(sorted(chk.items()))}  match={chk == sizes}")
    print(f"marks: lower {sum(text.count(c) for c in LOWER)}  upper {sum(text.count(c) for c in UPPER)}  "
          f"middle {sum(text.count(c) for c in MIDDLE)}")
    print(f"extent east {x.min():.0f}..{x.max():.0f}  north {y.min():.0f}..{y.max():.0f}  "
          f"end ({x[-1]:.0f}, {y[-1]:.0f})")
    cz = census(text)
    print("unclassified characters:", dict(cz) if cz else "none")
    if chapters:
        bounds = list(starts) + [len(text)]
        assert sum(bounds[i + 1] - bounds[i] for i in range(len(starts))) == len(text) - starts[0]
        per = Counter(int(chapter_of_step(len(text), starts)[b]) for _, b, _ in cl)
        print("chapter  chars    clusters  title")
        for i, c in enumerate(chapters):
            print(f"{c['index']:>5} {bounds[i + 1] - bounds[i]:>8} {per.get(i, 0):>9}  {c['title']}")


# An older color scheme used by the quick picture; the map uses ramp.py instead.
def chapter_palette(k):
    """k saturated colors: hues stepped by the golden ratio so neighbors differ,
    with alternating darkness; none pale enough to vanish on the beige background."""
    import colorsys
    cols = [colorsys.hsv_to_rgb((i * 0.61803398875 + 0.58) % 1.0, 0.85, 0.62 if i % 2 else 0.84)
            for i in range(k)]
    return np.array([(r, g, b, 1.0) for r, g, b in cols])


# Draws a quick PNG picture of the walk (not used by the interactive map).
def plot(x, y, cl, title, path, chapters=None, starts=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D

    n = len(x) - 1
    extras = []
    pts = np.column_stack([x, y]).reshape(-1, 1, 2)
    segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
    fig, ax = plt.subplots(figsize=(10, 9))

    if chapters:
        ccol = chapter_palette(len(chapters))
        step_ch = chapter_of_step(n, starts)
        ax.add_collection(LineCollection(segs, colors=ccol[step_ch], linewidths=0.9))
        dot_face = "#888888"
    else:
        lc = LineCollection(segs, array=np.linspace(0, 1, len(segs)), cmap="viridis", linewidths=1.0)
        ax.add_collection(lc)
        dot_face = "#d1495b"

    if cl:
        ends = np.array([b + 1 for _, b, _ in cl])
        sizes = np.array([s for _, _, s in cl])
        # diameter steps up by 5 pt per extra mark (2 marks = 6 pt, 3 = 11, 4 = 16, ...), capped at 40 pt
        diam = np.minimum(6 + 5 * (sizes - 2), 40)
        face = ccol[step_ch[ends - 1]] if chapters else dot_face
        ax.scatter(x[ends], y[ends], s=diam ** 2, c=face, edgecolors="black" if chapters else "white",
                   linewidths=0.7 if chapters else 0.6, zorder=3)
        shown = sorted(set(sizes.tolist()))
        dot_handles = [Line2D([0], [0], marker="o", color="none", mfc="#bbbbbb", mec="black",
                              ms=min(6 + 5 * (k - 2), 40), label=f"{k} marks in a row") for k in shown]
        dot_legend = ax.legend(handles=dot_handles, title="dot = cluster of marks", loc="upper center",
                               bbox_to_anchor=(0.5, -0.1), ncol=len(dot_handles), frameon=False,
                               columnspacing=2.0, handletextpad=0.8)
        ax.add_artist(dot_legend)
        extras.append(dot_legend)

    ax.plot(0, 0, "o", color="green", ms=9, mec="white", zorder=5)
    ax.plot(x[-1], y[-1], "s", color="firebrick", ms=9, mec="white", zorder=5)
    ax.autoscale()
    ax.margins(0.06)
    ax.set_aspect("equal")
    ax.set_facecolor("#f4f1ea")
    ax.grid(alpha=0.3)
    ax.set_xlabel("east (m)")
    ax.set_ylabel("north (m)")
    ax.set_title(title)
    if chapters:
        handles = [Line2D([0], [0], color=ccol[i], lw=3, label=f"{c['index']}. {c['title']}")
                   for i, c in enumerate(chapters)]
        handles += [Line2D([0], [0], marker="o", color="none", mfc="green", mec="white", ms=9, label="start"),
                    Line2D([0], [0], marker="s", color="none", mfc="firebrick", mec="white", ms=9, label="end")]
        extras.append(ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5),
                                fontsize=8, frameon=False, title="chapter (line and dot color)"))
    else:
        cb = fig.colorbar(lc, ax=ax, fraction=0.035, pad=0.02, ticks=[0, 1])
        cb.ax.set_yticklabels(["start of text", "end of text"])
        cb.set_label("line color = position in the text")
    fig.savefig(path, dpi=170, bbox_inches="tight", bbox_extra_artists=extras)
    plt.close(fig)


# Exports the path and points as GeoJSON files for use in GIS software such as ArcGIS Pro or QGIS.
def write_geojson(text, x, y, cl, start, epsg, outdir, chapters=None, starts=None):
    from pyproj import Transformer
    to_proj = Transformer.from_crs(4326, epsg, always_xy=True)
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    x0, y0 = to_proj.transform(start[1], start[0])
    lon, lat = to_ll.transform(x0 + x, y0 + y)

    def coords(a, b):
        return [[round(float(p), 7), round(float(q), 7)] for p, q in zip(lon[a:b + 1], lat[a:b + 1])]

    lines = []
    if chapters:
        bounds = list(starts) + [len(text)]
        for i, c in enumerate(chapters):
            a = bounds[i] if i else 0
            lines.append({"type": "Feature",
                          "properties": {"chapter": c["index"], "title": c["title"],
                                         "steps": bounds[i + 1] - a},
                          "geometry": {"type": "LineString", "coordinates": coords(a, bounds[i + 1])}})
        step_ch = chapter_of_step(len(text), starts)
    else:
        lines.append({"type": "Feature", "properties": {"steps": len(text)},
                      "geometry": {"type": "LineString", "coordinates": coords(0, len(text))}})
    feats = []
    for a, b, size in cl:
        props = {"size": size, "offset": a, "context": text[max(0, a - 12):b + 13]}
        if chapters:
            k = int(step_ch[b])
            props.update(chapter=chapters[k]["index"], chapter_title=chapters[k]["title"])
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": "Point",
                                   "coordinates": [round(float(lon[b + 1]), 7), round(float(lat[b + 1]), 7)]}})
    json.dump({"type": "FeatureCollection", "features": lines}, open(f"{outdir}/punct_path.geojson", "w"))
    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{outdir}/punct_clusters.geojson", "w"))


# A set of small checks with known answers. If any fails, Python stops and shows which. Run: python3 walk_punct.py --selftest
def selftest():
    def sizes(t):
        return [s for _, _, s in clusters(t)]

    assert normalize("a  b\n c…") == "a b c..."
    x, y, h = walk("aa.aa")
    assert (round(x[-1], 6), round(y[-1], 6)) == (2.0, 3.0) and h == 90, (x[-1], y[-1], h)
    x, y, h = walk("a-aa")
    assert abs(x[-1] - 2 * _S2) < 1e-9 and abs(y[-1] - (2 + 2 * _S2)) < 1e-9 and h == 45
    assert walk("don't")[2] == 270
    assert walk('He said, "No."')[2] == 0                      # , " . " cancel out
    assert sizes('He said, "No."') == [2]
    assert sizes("Wait . . . what") == [3]                     # spaced ellipsis
    assert sizes("Wait . what") == [] and sizes("Wait . . what") == []
    assert sizes('He said . . ." Go') == [4]                   # spaced ellipsis plus closing quote
    assert sizes("wait... what") == [3] and sizes("wait...!") == [4]
    assert sizes('He said. "Go."') == [2]                      # '. "' is not adjacent
    assert sizes("(see below).") == [2]
    for t in ('He said, "No."', "Wait . . . what", 'He said . . ." Go', "wait...!", "(see below)."):
        assert cluster_check(t) == Counter(sizes(t)), t
    assert walk("a b")[0].shape[0] == 4                        # spaces are steps
    # offsets survive normalization: chapter starts land on the same characters
    raw = "  One\n\ntwo  three… four\n\nFive six"
    text, new = normalize_with_map(raw, [raw.index("One"), raw.index("three"), raw.index("Five")])
    assert text == normalize(raw) == "One two three... four Five six"
    assert [text[i] for i in new] == ["O", "t", "F"], new
    assert list(chapter_of_step(8, [0, 3, 6])) == [0, 0, 0, 1, 1, 1, 2, 2]
    print("selftest ok")


# What happens when this file is run on its own from the command line.
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?")
    ap.add_argument("--out", default=".")
    ap.add_argument("--title", default="Punctuation lens")
    ap.add_argument("--chapters")
    ap.add_argument("--start", nargs=2, type=float, metavar=("LAT", "LON"))
    ap.add_argument("--epsg", type=int)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    raw = open(a.text, encoding="utf-8").read()
    chapters = starts = None
    if a.chapters:
        chapters = json.load(open(a.chapters, encoding="utf-8"))
        text, starts = normalize_with_map(raw, [c["start"] for c in chapters])
    else:
        text = normalize(raw)
    x, y, heading = walk(text)
    cl = clusters(text)
    report(text, x, y, heading, cl, chapters, starts)
    plot(x, y, cl, a.title, f"{a.out}/punct_path.png", chapters, starts)
    if a.start and a.epsg:
        write_geojson(text, x, y, cl, a.start, a.epsg, a.out, chapters, starts)
        print("wrote geojson")


if __name__ == "__main__":
    main()
