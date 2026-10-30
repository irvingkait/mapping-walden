# =====================================================================================================
#  make_lenses.py  --  THE MAIN SCRIPT. This is the one that builds the map.
# =====================================================================================================
#  What it does, in plain words:
#    1. Reads the cleaned text of Walden (clean.txt) and the chapter list (chapters.json).
#    2. For each of four "lenses" (Punctuation, Letter, Word, Sentence) it walks a "turtle" along the text,
#       one character at a time, one meter per character, turning according to that lens's rules.
#    3. Converts each walk from meters into latitude and longitude on the ground at Concord.
#    4. Packs everything (paths, points, turn arrows, colors, the text itself) into one big block of data.
#    5. Writes the results as plain files for the React app to read: walden.json (all the data), basemap.jpg
#       (the 1906 map) and walden.pdf (the source text). The React app itself lives in ../app and is not touched.
#
#  You normally do not run this file directly. Run build_data.py (one folder up), which calls this file with
#  all the right options filled in.
#
#  How to read this file: it runs from top to bottom, like a recipe. Anything after a # sign is a comment
#  for humans; Python ignores it. Words like "def" start a small named recipe (a "function") that is used
#  later. Lines starting with p_ belong to the Punctuation lens, l_ to Letter, w_ to Word, s_ to Sentence.
#
#  Where to tweak (search for these headings in this file):
#    * The rules of a lens        -> its section below, and the small rule files walk_punct.py,
#                                    word_lens.py, sentence_lens.py
#    * The color of each lens in the overlay, and its quote  -> the LENSES list near the bottom
#    * Point thresholds (how long a word or sentence must be to get a point) -> word_lens.py and
#                                    sentence_lens.py (MIN_POINT, MIN_WORDS), and the Letter lens (4 and 3 below)
#  Text between triple quotes below is the original author's description of the file.

"""Build the data files for the React map: every built lens (punctuation, letter, word, sentence).

Each lens is one walk of the same text from the same start at 1 m per character.
Views: one lens at a time, or an overlay of all built lenses.
"""
# ---- Imports: tools borrowed from Python's standard library and from add-on packages ----
#  argparse reads the options typed after the command; base64 turns binary files (fonts, images) into text so
#  they can live inside one HTML file; json writes data in a form web pages can read; re is "regular expressions",
#  a mini-language for finding patterns in text; numpy does fast arithmetic on long lists of numbers.
import argparse
import shutil
import base64
import html
import io
import json
import math
import os
import re
import sys
import unicodedata

import numpy as np
# pyproj converts between coordinate systems: here, between latitude/longitude (degrees) and a flat
#  metric grid (meters) where one step really is one meter.
from pyproj import Transformer

# HERE is the folder this file lives in. The next line lets Python also import our own helper files
#  (ramp.py, walk_punct.py ...) from that folder.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# ramp.py makes the 18 chapter colors (blue to green, from Thoreau's words about the pond).
import ramp  # noqa: E402
# walk_punct.py holds the heading engine (the 8 directions) and the Punctuation lens rules. We call it W.
import walk_punct as W  # noqa: E402

# ---- Options that can be typed after the command (the "arguments") ----
#  Each add_argument line declares one option. Those without -- (text, chapters, out) are required and come
#  in a fixed order. Those with -- are labeled. build_map.py fills in all of these for you.
ap = argparse.ArgumentParser()
ap.add_argument("text")
ap.add_argument("chapters")
ap.add_argument("out")          # a FOLDER: the data files are written into it
ap.add_argument("--title", default="Walden: ")
# --start LAT LON : where the turtle begins (Thoreau's hut). Change these two numbers to start the walk somewhere else.
ap.add_argument("--start", nargs=2, type=float, required=True, metavar=("LAT", "LON"))
ap.add_argument("--start-name", default="start")
# --epsg : the number code of the metric map grid used to measure meters. 26986 is the Massachusetts Mainland grid.
ap.add_argument("--epsg", type=int, required=True)
# --basemap : the 1906 map picture; --basemap-bounds gives its four edges as latitude/longitude.
ap.add_argument("--basemap")
ap.add_argument("--basemap-bounds", nargs=4, type=float, metavar=("S", "W", "N", "E"))
ap.add_argument("--basemap-credit")
ap.add_argument("--basemap-credit-url")
ap.add_argument("--source-pdf")
ap.add_argument("--source-label", default="Source text (PDF)")
# --skip-quote-check : when building a map of a DIFFERENT book, the four overlay quotes about autumn (see LENSES below) are not in that book, so use this to switch the check off.
ap.add_argument("--skip-quote-check", action="store_true")
# From here on, a.text, a.out, a.start and so on hold whatever was typed on the command line.
a = ap.parse_args()

# ---- Step 1: read the text and the chapter list ----
#  raw is the cleaned book as one long string of characters.
raw = open(a.text, encoding="utf-8").read()
# chapters is a list of 18 entries, each with a title and the character offset where the chapter starts.
chapters = json.load(open(a.chapters, encoding="utf-8"))
# Normalizing: every run of spaces or line breaks becomes ONE space and the single ellipsis character
#  becomes three periods. Chapter start positions are translated to match the normalized text.
text, starts = W.normalize_with_map(raw, [c["start"] for c in chapters])
# n is the total number of characters, which is also the total number of steps (1 m each): 578,510.
n = len(text)
# step_ch[i] tells which chapter (0 to 17) character number i belongs to.
step_ch = W.chapter_of_step(n, starts)
# bounds holds the first character of each chapter, plus the end of the text, so chapter i spans bounds[i] to bounds[i+1].
bounds = list(starts) + [n]
bounds[0] = 0
# hexes is the list of 18 chapter colors, as hex codes like #1b315b. The ramp itself is made in ramp.py.
hexes = ramp.thoreau_ramp(len(chapters))        # chapter colors, unchanged: blue to green from Thoreau's words on the pond

# ---- Step 2: set up the ground ----
#  to_proj: degrees -> meters. to_ll: meters -> degrees. always_xy=True means longitude comes first, then latitude.
to_proj = Transformer.from_crs(4326, a.epsg, always_xy=True)
to_ll = Transformer.from_crs(a.epsg, 4326, always_xy=True)
# x0, y0 is the start point (the hut) in meters on the metric grid. Every step is added to this.
x0, y0 = to_proj.transform(a.start[1], a.start[0])


# A path of 578,510 steps would be enormous, but most steps continue straight on. This picks out only the CORNERS:
#  the spots where the direction changes. The positions at i0 and i1 are always kept. (np.diff gives the change from
#  one step to the next; if it differs from the previous change, the turtle has turned.)
def corners(x, y, i0, i1):
    dx = np.round(np.diff(x[i0:i1 + 1]), 6)
    dy = np.round(np.diff(y[i0:i1 + 1]), 6)
    change = np.nonzero((dx[1:] != dx[:-1]) | (dy[1:] != dy[:-1]))[0] + 1
    return np.concatenate(([0], change, [i1 - i0])) + i0


# Cuts one lens's walk (x and y lists, in meters) into 18 chapter paths, keeps only the corners of each,
#  converts them to latitude/longitude, and attaches the chapter color. Returns the paths and the number of
#  corners kept. The assert at the end is a safety check: if we added up the distances between the kept corners
#  and did not get exactly the number of steps, the script would stop with an error rather than draw a wrong map.
def chapter_paths(x, y):
    out, total, length = [], 0, 0.0
    for i, c in enumerate(chapters):
        i0, i1 = bounds[i], bounds[i + 1]
        idx = corners(x, y, i0, i1)
        px, py = x[idx], y[idx]
        length += float(np.hypot(np.diff(px), np.diff(py)).sum())
        lon, lat = to_ll.transform(x0 + px, y0 + py)
        total += len(idx)
        out.append({"color": hexes[i], "steps": i1 - i0,
                    "path": [[round(float(la), 6), round(float(lo), 6)] for la, lo in zip(lat, lon)]})
    assert abs(length - n) < 1e-3 * n, (length, n)     # lossless: corner-to-corner distance equals the number of 1 m steps
    return out, total


# Returns (text before, the marks themselves, text after) for a popup quote: up to 28 characters each side,
#  trimmed so that no word is cut in half.
def context(s, e):
    """Up to 28 characters each side of text[s:e+1], trimmed so no word is cut off."""
    a0 = max(0, s - 28)
    while 0 < a0 < s and text[a0 - 1] != " ":
        a0 += 1
    b0 = min(n, e + 1 + 28)
    while e + 1 < b0 < n and text[b0] != " ":
        b0 -= 1
    return text[a0:s], text[s:e + 1], text[e + 1:b0]


# Builds one row of data for a point on the map: where it sits (latitude, longitude), its size, its chapter,
#  where it starts in the text, the quote around it, and its kind ("p" punctuation, "c" consonant, "v" vowel,
#  "w" word, "s" sentence). The page code (lenses_body.html) reads these rows by position.
def dot_row(x, y, s, e, size, kind):
    lon, lat = to_ll.transform(x0 + x[e + 1], y0 + y[e + 1])
    pre, run, post = context(s, e)
    return [round(float(lat), 6), round(float(lon), 6), size, int(step_ch[e]), s, pre, run, post, kind]


# Ramer-Douglas-Peucker line simplification: reduces a path to the fewest points that still look like the same
#  shape. Only used for the small outline pictures on the lens buttons.
def rdp(pts, eps):
    pts = np.asarray(pts, float)
    keep = np.zeros(len(pts), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        p, q = pts[i], pts[j]
        d = q - p
        L = math.hypot(*d)
        seg = pts[i + 1:j]
        dist = np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / L if L else np.hypot(*(seg - p).T)
        k = int(np.argmax(dist))
        if dist[k] > eps:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return pts[keep]


# Makes the tiny outline of a whole lens path shown on its button (about 70 points, as an SVG polyline).
def thumb(x, y, target=70):
    """A 64 x 32 outline of the whole path for the lens button."""
    w, h = x.max() - x.min(), y.max() - y.min()
    s = min(60 / w, 28 / h)
    X = 32 + s * (x - (x.min() + x.max()) / 2)
    Y = 16 - s * (y - (y.min() + y.max()) / 2)
    idx = corners(X, Y, 0, n)
    pts = np.column_stack([X[idx], Y[idx]])
    lo, hi = 0.0, 40.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if len(rdp(pts, mid)) > target:
            lo = mid
        else:
            hi = mid
    return " ".join("%.1f,%.1f" % tuple(p) for p in rdp(pts, hi))


# Packs every TURN of a lens for the close-up arrow layer. Positions are stored as whole numbers of millionths of a
#  degree away from the hut, which keeps the file small. 'code' squeezes two facts into one number:
#  kind * 8 + heading  (the page unpacks it with >> 3 for the kind and & 7 for the heading).
def pack_turns(x, y, pos, offs, kinds, heads, labels):
    """Every turn of a lens for the close-up arrow layer: where it happens, the heading it sets, its kind, and the text that caused it.
    Positions are integer millionths of a degree from the hut."""
    lon, lat = to_ll.transform(x0 + x[pos], y0 + y[pos])
    return {"lat": [int(round((v - a.start[0]) * 1e6)) for v in lat], "lon": [int(round((v - a.start[1]) * 1e6)) for v in lon],
            "code": [int(k) * 8 + int(h) for k, h in zip(kinds, heads)], "off": [int(o) for o in offs], "word": list(labels)}


# ---------------- lens 1: punctuation ----------------
# ---- LENS 1: PUNCTUATION (Plate I) ----
#  W.walk walks the whole text with the punctuation rules and returns the x and y position (meters) after every
#  step. The rules themselves (which marks turn which way) are at the top of walk_punct.py.
px, py, heading = W.walk(text)
# A 'cluster' is a run of 2 or more marks with no space between them. Each becomes one point. Returns (start, end, size).
cl = W.clusters(text)
# p_ch: the 18 chapter paths for this lens. p_vert: how many corners were kept in total.
p_ch, p_vert = chapter_paths(px, py)
# One data row per point.
p_dots = [dot_row(px, py, s, e, size, "p") for s, e, size in cl]
# The three mark classes, written out as text for the Rules panel in the legend.
RULES = {"lower": ", . _", "upper": "' \" * ^ ` ‘ ’ “ ”",
         "middle": "! @ # $ % & ( ) < > ? | + = - : ; / \\ [ ] { } ~ – — ·"}
# These three asserts compare the panel text with the real rules in walk_punct.py, so the legend can never drift out of date.
assert set(RULES["lower"].replace(" ", "")) == W.LOWER
assert set(RULES["upper"].replace(" ", "")) == W.UPPER
assert set(RULES["middle"].replace(" ", "")) == W.MIDDLE
# Makes text safe to place inside HTML (turns < into &lt; and so on).
e_ = html.escape
# The rules shown in the legend panel, as HTML list items. <b>...</b> is bold; <!--KEYS--> marks where the size key goes.
p_rules = (
    "<li><b>Step:</b> 1 meter per character, spaces included</li>"
    f"<li><b>Right turn:</b> lower marks <code>{e_(RULES['lower'])}</code></li>"
    f"<li><b>Left turn:</b> upper marks <code>{e_(RULES['upper'])}</code></li>"
    f"<li><b>Diagonal turn:</b> middle and full height marks <code>{e_(RULES['middle'])}</code></li>"
    "<li><b>Point placement:</b> each instance of 2 or more marks in a row<!--KEYS--></li>")
p_sizes = sorted({s for _, _, s in cl})
# The size key under the rules: which point sizes exist (2, 3, 4 marks).
p_keys = [{"title": "Point size", "kind": "p", "sizes": [k for k in (2, 3, 4) if k in p_sizes], "unit": "marks"}]
# Where the last character lands (the 'Finis' marker).
p_end = to_ll.transform(x0 + px[-1], y0 + py[-1])
# _pt: for every character, how many degrees it turns (0 for letters, spaces and digits).
_pt = np.fromiter((W.TURN.get(c, 0) for c in text), dtype=np.int64, count=n)
# _pi: the positions of only the characters that actually turn the turtle.
_pi = np.nonzero(_pt)[0]
# _pk: which class each turning mark belongs to: 0 lower, 1 upper, 2 middle.
_pk = [0 if text[i] in W.LOWER else 1 if text[i] in W.UPPER else 2 for i in _pi]
# The turn data for the arrow layer. The turtle's heading after each mark is (running total of turns mod 360) / 45.
p_turns = pack_turns(px, py, _pi + 1, _pi, _pk, (np.cumsum(_pt) % 360)[_pi] // 45, [text[i] for i in _pi])
# The wording for each class in the arrow popups.
p_kinds = [["a lower mark", "turn right 90&deg;"], ["an upper mark", "turn left 90&deg;"], ["a middle mark", "turn right 45&deg;"]]

# ---------------- lens 2: letter ----------------
# Accented letters count as their base letter. The text is not changed, only how each character is classified.
# ---- LENS 2: LETTER (Plate II) ----
#  Accented letters count as their base letter (an accented E is treated as E). The text is not changed, only
#  how each character is classified. (unicodedata.normalize splits an accented letter into a base plus a mark;
#  [0] keeps the base.)
base = "".join(unicodedata.normalize("NFD", c)[0] for c in text)
assert len(base) == n
# GROUP maps each capital-letter range to a group number: A-G = 0, H-M = 1, N-S = 2, T-Z = 3.
#  To change the ranges, edit the four letter pairs in the tuple on the next line.
GROUP = {}
for gi, (lo_, hi_) in enumerate((("A", "G"), ("H", "M"), ("N", "S"), ("T", "Z"))):
    for o in range(ord(lo_), ord(hi_) + 1):
        GROUP[chr(o)] = gi
assert len(GROUP) == 26
# For every character: if it is a capital letter, turn by (group*2 + 1) units of 45 degrees, which gives
#  45, 135, 225, 315 degrees. Everything else is 0 (no turn). Change the formula here to change the angles.
turn_steps = np.fromiter((GROUP[c] * 2 + 1 if c in GROUP else 0 for c in base), dtype=np.int64, count=n)   # 45, 135, 225, 315 degrees in 45 degree units
# Heading used by each step. The step comes BEFORE the turn, so each step uses the total of all the turns before it.
before = np.concatenate(([0], np.cumsum(turn_steps)[:-1])) % 8          # heading each step uses: the step comes before the turn
# lx, ly: x and y position (meters) after every step. SIN and COS turn a heading into east and north movement.
lx = np.concatenate(([0.0], np.cumsum(W.SIN[before])))
ly = np.concatenate(([0.0], np.cumsum(W.COS[before])))
# Chapter paths for the Letter lens.
l_ch, l_vert = chapter_paths(lx, ly)
# Points for the Letter lens: runs of consonants or vowels. cons_n and vow_n count how many of each size.
l_dots, cons_n, vow_n = [], {}, {}
# Go through every word (a run of letters). Inside it, find runs of vowels (a e i o u) of 3 or more, and runs
#  of non-vowels (consonants, so y counts as one) of 4 or more. To change the thresholds, edit the 3 and the 4 below.
for m in re.finditer(r"[A-Za-z]+", base):
    w = m.group(0).lower()
    for r in re.finditer(r"[aeiou]+", w):
        if len(r.group(0)) >= 3:
            s, e = m.start() + r.start(), m.start() + r.end() - 1
            l_dots.append(dot_row(lx, ly, s, e, e - s + 1, "v"))
            vow_n[e - s + 1] = vow_n.get(e - s + 1, 0) + 1
    for r in re.finditer(r"[^aeiou]+", w):
        if len(r.group(0)) >= 4:
            s, e = m.start() + r.start(), m.start() + r.end() - 1
            l_dots.append(dot_row(lx, ly, s, e, e - s + 1, "c"))
            cons_n[e - s + 1] = cons_n.get(e - s + 1, 0) + 1
# Sort by position in the text so the page draws them in order.
l_dots.sort(key=lambda d: d[4])
# How many capital letters turn the turtle (printed at the end of the build).
n_turns = int((turn_steps > 0).sum())
l_end = to_ll.transform(x0 + lx[-1], y0 + ly[-1])
# Positions of the turning capitals, then their headings and arrow data, as for Punctuation.
_li = np.nonzero(turn_steps)[0]
_lh = np.cumsum(turn_steps) % 8
# Arrow data for the Letter lens. The 'kind' is which of the four ranges the capital belongs to.
l_turns = pack_turns(lx, ly, _li + 1, _li, [(turn_steps[i] - 1) // 2 for i in _li], _lh[_li], [text[i] for i in _li])
# Pattern for 'part of a word': letters, apostrophes and hyphens.
_wc = re.compile(r"[^\W\d_]|['\u2019-]")          # letters, apostrophes and hyphens belong to a word
# Finds the whole word around a capital letter and returns a quote around it that never cuts a word.
def _word_ctx(i):
    s_, e_ = i, i
    while s_ > 0 and _wc.match(text[s_ - 1]):
        s_ -= 1
    while e_ + 1 < n and _wc.match(text[e_ + 1]):
        e_ += 1
    return list(context(s_, e_))                      # up to 28 characters each side, never cutting a word
# Attach the quote to each turn so the popup can show the word the capital is in.
l_turns["ctx"] = [_word_ctx(int(i)) for i in _li]
# Wording for the four turn kinds in the arrow popups.
l_kinds = [["a capital in A-G", "turn 45&deg;"], ["a capital in H-M", "turn 135&deg;"], ["a capital in N-S", "turn 225&deg;"], ["a capital in T-Z", "turn 315&deg;"]]
# A small unused helper that draws a dial (kept in case you want a different legend picture).
def _dial(deg):
    import math as _m
    r = _m.radians(deg)
    return (f'<svg width="34" height="34" viewBox="-17 -17 34 34" aria-hidden="true"><circle r="14.5" fill="none" stroke="#2a2118" stroke-width="1"/>'
            f'<path d="M0 0L{11 * _m.sin(r):.1f} {-11 * _m.cos(r):.1f}" stroke="#5b4a33" stroke-width="1" stroke-linecap="round"/>'
            f'<circle r="1.6" fill="#5b4a33"/></svg>')
# Angle -> label for the Word wheel in the legend. Also the default for the wheel function.
WORD_SPOKES = {45: "adjective", 90: "adverb", 135: "conjunction", 225: "noun", 270: "pronoun", 315: "verb"}


# Draws the circular 'wheel' diagram in the legend as an SVG picture: a circle, with one spoke per kind,
#  each labeled with its name and angle. 0 degrees is straight ahead (up). Pass a dictionary of angle -> label to draw
#  a different wheel (the Letter and Sentence lenses do this).
def _wheel(names=None):
    """One circle, one spoke per kind: each tied to its direction (0 = straight ahead, up), with its degrees."""
    cx, cy, r = 150, 78, 46
    names = names or WORD_SPOKES
    out = [f'<svg class="wheel" viewBox="0 0 300 146" width="100%" role="img" aria-label="Turn for each word type, clockwise from straight ahead">',
           f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2a2118" stroke-width="1"/>']
    out.append(f'<path d="M{cx} {cy - r - 7}l-3 6h6z" fill="#5b4a33"/><text x="{cx}" y="{cy - r - 10}" text-anchor="middle" font-size="11" font-style="italic" fill="#5b4a33">ahead (0&deg;)</text>')
    for deg, nm in names.items():
        t = math.radians(deg)
        sx, sy = math.sin(t), -math.cos(t)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + r * sx:.1f}" y2="{cy + r * sy:.1f}" stroke="#5b4a33" stroke-width="1" stroke-linecap="round"/>')
        lx_, ly_ = cx + (r + 8) * sx, cy + (r + 8) * sy
        anchor = "start" if sx > 0.1 else "end" if sx < -0.1 else "middle"
        y1 = ly_ - 9 if sy < -0.1 else ly_ + 9 if sy > 0.1 else ly_ + 0
        out.append(f'<text x="{lx_:.1f}" y="{y1:.1f}" text-anchor="{anchor}" font-size="12.5" fill="#2a2118">{nm}</text>'
                   f'<text x="{lx_:.1f}" y="{y1 + 13:.1f}" text-anchor="{anchor}" font-size="12" fill="#5b4a33">{deg}&deg;</text>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="1.8" fill="#5b4a33"/></svg>')
    return "".join(out)


# The Letter rules panel text. + _wheel({...}) inserts the wheel picture.
l_rules = (
    "<li><b>Step:</b> 1 meter per character, spaces included</li>"
    "<li><b>Turns:</b> at each capital letter, after its step, clockwise from the turtle&rsquo;s heading"
    + _wheel({45: "A-G", 135: "H-M", 225: "N-S", 315: "T-Z"}) + "</li>"
    "<li><b>Point placement:</b> each run of 4 or more consonants or 3 or more vowels (<code>a e i o u</code>)<!--KEYS--></li>")
# The size key for consonant and vowel points.
l_keys = [{"title": "Consonants", "kind": "c", "sizes": [k for k in (4, 5, 6) if k in cons_n] or [4], "unit": "in a row"},
          {"title": "Vowels", "kind": "v", "sizes": [k for k in (3, 4) if k in vow_n] or [3], "unit": "in a row"}]

# ---------------- lens 3: word ----------------
# A word's type is read by spaCy (en_core_web_sm). Proper nouns count as nouns, auxiliaries are not verbs, both kinds of
# conjunction count, a contraction is one word, and hyphens or dashes split words. Turn: first letter of the word, before its step.
# ---- LENS 3: WORD (Plate III) ----
#  A word's type (noun, verb ...) is decided by a language tool called spaCy, in word_lens.py. That is slow
#  (a few minutes), so the result is saved in word_tags.pkl and reused. Delete that file to force a re-tag.
import word_lens as WL  # noqa: E402
# words: a list with one entry per word: (first character, end, number of letters, type, sentence start).
words = WL.tag_words(text, os.path.join(os.path.dirname(os.path.abspath(a.text)), "word_tags.pkl"))
assert words[-1][1] <= n
# Walk the text with the word rules. Here the turn happens at a word's FIRST letter, BEFORE its step (unlike the other lenses).
wx, wy, _, w_turn = WL.walk_words(text, words)
# Chapter paths for the Word lens.
w_ch, w_vert = chapter_paths(wx, wy)
# A point for every word of MIN_POINT letters or more (12). w_len counts how many of each length.
w_dots, w_len = [], {}
for s_, e_end, L_, pos_, _ in words:
    if L_ >= WL.MIN_POINT:
        w_dots.append(dot_row(wx, wy, s_, e_end - 1, L_, "w"))
        w_len[L_] = w_len.get(L_, 0) + 1
w_dots.sort(key=lambda d: d[4])
# Where the last character lands.
w_end = to_ll.transform(x0 + wx[-1], y0 + wy[-1])
# How many words are of a turning type (adjective, adverb, conjunction, noun, pronoun, verb).
w_turning = sum(1 for w_ in words if w_[3] in WL.POS_TO_TYPE)
# Every turn, for the close-up arrow layer: where it happens (before the step of the word's first letter), the heading it sets,
# the word type that dictated it, and the word. Positions are stored as integer millionths of a degree from the hut.
# The six word types that turn the turtle, in a fixed order. The order matters: the page refers to them by number.
TYPES = ["ADJ", "ADV", "CONJ", "NOUN", "PRON", "VERB"]
# Heading (0 to 7) after each word.
w_head = np.cumsum(w_turn) % 8
# t_idx: the words that turn, in order. t_s: where each one starts.
t_idx = [i for i, w_ in enumerate(words) if w_[3] in WL.POS_TO_TYPE]
t_s = np.array([words[i][0] for i in t_idx])
t_lon, t_lat = to_ll.transform(x0 + wx[t_s], y0 + wy[t_s])
# Arrow data for the Word lens.
w_turns = pack_turns(wx, wy, t_s, t_s, [TYPES.index(WL.POS_TO_TYPE[words[i][3]]) for i in t_idx], w_head[t_s],
                     [text[words[i][0]:words[i][1]] for i in t_idx])
# Wording for the six word types in the arrow popups ('an adjective', 'a noun' ...).
w_kinds = [[("an " if k < 2 else "a ") + nm, "turn %d&deg;" % deg] for k, (nm, deg) in
           enumerate((("adjective", 45), ("adverb", 90), ("conjunction", 135), ("noun", 225), ("pronoun", 270), ("verb", 315)))]


# The Word rules panel text, with the wheel for the six word types.
w_rules = (
    "<li><b>Step:</b> 1 meter per character, spaces included</li>"
    "<li><b>Turns:</b> at the first letter of each word, before its step, clockwise from the turtle&rsquo;s heading"
    + _wheel() + "Other word types go straight.</li>"
    "<li><b>Point placement:</b> each word of 12 or more letters<!--KEYS--></li>")
# The size key for word points (letters).
w_keys = [{"title": "Letters", "kind": "w", "sizes": sorted(w_len), "unit": ""}]

# ---------------- lens 4: sentence ----------------
# ---- LENS 4: SENTENCE (Plate IV) ----
#  Sentences and verb tenses are found by spaCy in sentence_lens.py (cached in sent_tense.pkl).
import sentence_lens as SL  # noqa: E402
# srows: one row per sentence: (first character, last character, tense class, the words that gave the tense).
srows = SL.classify(text, os.path.join(os.path.dirname(os.path.abspath(a.text)), "sent_tense.pkl"))
# s_turn: for every character, the turn in 45-degree units. Only the LAST character of each sentence turns.
s_turn = np.zeros(n, dtype=np.int64)
# For each sentence that has a tensed verb, put its turn on its last character. SL.ANGLE holds the angles: present 135, past 315, future 45, past+present 225.
for s_, k_, c_, _h in srows:
    if c_ != "none":
        s_turn[k_] = SL.ANGLE[c_] // 45
# Heading used by each step (step first, then turn, as in Punctuation and Letter).
s_before = np.concatenate(([0], np.cumsum(s_turn)[:-1])) % 8
# sx, sy: x and y position (meters) after every step.
sx = np.concatenate(([0.0], np.cumsum(W.SIN[s_before])))
sy = np.concatenate(([0.0], np.cumsum(W.COS[s_before])))
# Chapter paths for the Sentence lens.
s_ch, s_vert = chapter_paths(sx, sy)


# Small helpers that cut a short piece from the start or end of a long sentence without cutting a word.
def _snippet_head(s_, limit=64):
    if n - s_ <= limit:
        return text[s_:]
    cut = text[s_:s_ + limit]
    return cut if text[s_ + limit] == " " else cut[:cut.rfind(" ")]


def _snippet_tail(s_, k_, limit=64):
    if k_ + 1 - s_ <= limit:
        return text[s_:k_ + 1]
    j = k_ + 1 - limit
    return text[j:k_ + 1] if text[j - 1] == " " else text[j:k_ + 1].split(" ", 1)[1]


# A point for every sentence of 50 or more words. SL.band() sorts them into size bands (50, 60, 70, 80, 100+).
s_dots, s_bands = [], {}
for s_, k_, c_, _h in srows:
    cnt = SL.word_count(text, s_, k_)
    b_ = SL.band(cnt)
    if b_:
        d_ = dot_row(sx, sy, s_, k_, b_, "s")
        d_[5], d_[6], d_[7] = str(cnt), "", str(k_)      # word count, (the page reads the sentence from the text), last character
        d_[4] = s_
        s_dots.append(d_)
        s_bands[b_] = s_bands.get(b_, 0) + 1
s_dots.sort(key=lambda d: d[4])
# Where the last character lands.
s_end = to_ll.transform(x0 + sx[-1], y0 + sy[-1])
# _si: the sentences that turn (those with a tensed verb).
_si = [(s_, k_, c_, h_) for s_, k_, c_, h_ in srows if c_ != "none"]
_sk = np.array([k_ for _, k_, _, _ in _si])
_sh = np.cumsum(s_turn) % 8
# Arrow data for the Sentence lens. 'sent' is where each sentence starts and 'hl' holds the offsets of the tense words, so the popup can bold them.
s_turns = pack_turns(sx, sy, _sk + 1, _sk, [SL.KINDS.index(c_) for _, _, c_, _ in _si], _sh[_sk],
                     [{"present": "present tense", "past": "past tense", "future": "future tense", "shift": "past and present"}[c_] for _, _, c_, _ in _si])
s_turns["sent"] = [s_ for s_, _, _, _ in _si]                    # where each sentence begins
s_turns["hl"] = [[v for ab in h_ for v in ab] for _, _, _, h_ in _si]        # offsets of the words that gave the tense
# Wording for the four tenses in the arrow popups.
s_kinds = [["a present-tense sentence", "turn 135&deg;"], ["a past-tense sentence", "turn 315&deg;"],
           ["a future-tense sentence", "turn 45&deg;"], ["a sentence in past and present", "turn 225&deg;"]]
# The Sentence rules panel text, with its wheel.
s_rules = (
    "<li><b>Step:</b> 1 meter per character, spaces included</li>"
    "<li><b>Turns:</b> at the end of each sentence, after its last step, by the tense of its verbs, clockwise from the turtle&rsquo;s heading"
    + _wheel({135: "present", 315: "past", 45: "future", 225: "past + present"}) +
    "A sentence with no tensed verb goes straight.</li>"
    "<li><b>Point placement:</b> each sentence of 50 or more words<!--KEYS--></li>")
# The size key for sentence points (words per sentence).
s_keys = [{"title": "Words", "kind": "s", "sizes": sorted(s_bands), "labels": ["50", "60", "70", "80", "100+"][:len(s_bands)], "unit": ""}]
# How many sentences of each tense (printed at the end of the build).
s_count = {c_: sum(1 for r_ in srows if r_[2] == c_) for c_ in ("present", "past", "shift", "future", "none")}

# ---------------- lenses ----------------
# One color per lens for the overlay, each with Thoreau's own words (checked against the text). Lens order: built lenses first.
# The autumn colors, as first chosen, minus the November one. Only punctuation and letter pass the color-vision check together;
# word and sentence are chosen for Thoreau's words, so each lens also has its own symbol in the legend.
# ---- The four lenses, packaged for the page ----
#  Each entry is one lens: its name, its OVERLAY color and a quote from Walden for that color (shown when you
#  hover the color bar), its one-line description, its paths ('chapters'), points ('dots'), arrow data ('turns'),
#  and the zoom level at which its arrows first appear ('turnZoom': bigger number = you must zoom in closer).
#  To change a lens color in the Overlay, change the "color" hex AND the "quote" (the quote is checked against the book
#  below, so it must be Thoreau's exact words).
LENSES = [
    {"id": "punct", "name": "Punctuation", "built": True, "color": "#d0401f",
     "quote": "two or three small maples turned scarlet", "source": "House-Warming, of the first of September",
     "sees": "Sees how the sentences are punctuated: every pause, quotation and break turns the turtle, and clusters of marks become points.",
     "colophon": "Set in Cardo. Drawn by a turtle that reads punctuation.",
     "chapters": p_ch, "dots": p_dots, "end": [round(p_end[1], 6), round(p_end[0], 6)], "rules": p_rules, "keys": p_keys,
     "turns": p_turns, "turnKinds": p_kinds, "turnAt": "at", "turnZoom": 18,
     "thumb": thumb(px, py)},
    {"id": "letter", "name": "Letter", "built": True, "color": "#b98a0a",
     "quote": "a maturer golden and autumnal tint", "source": "Reading, of the literature of Greece",
     "sees": "Sees the shape of the words: each capital letter steers the turtle, and clumps of consonants or vowels become points.",
     "colophon": "Set in Cardo. Drawn by a turtle that reads letters.",
     "chapters": l_ch, "dots": l_dots, "end": [round(l_end[1], 6), round(l_end[0], 6)], "rules": l_rules, "keys": l_keys,
     "turns": l_turns, "turnKinds": l_kinds, "turnAt": "at", "turnZoom": 17.5,
     "thumb": thumb(lx, ly)},
    {"id": "word", "name": "Word", "built": True, "color": "#7a4a28",
     "quote": "a rich bronze color", "source": "The Ponds, of the perch in the green water",
     "sees": "Sees what kind of word is being said: nouns, verbs, pronouns and their kin each steer the turtle a set way, and the longest words become points.",
     "colophon": "Set in Cardo. Drawn by a turtle that reads words.",
     "turns": w_turns, "turnKinds": w_kinds, "turnAt": "beginning at", "turnZoom": 20,
     "chapters": w_ch, "dots": w_dots, "end": [round(w_end[1], 6), round(w_end[0], 6)], "rules": w_rules, "keys": w_keys,
     "thumb": thumb(wx, wy)},
    {"id": "sentence", "name": "Sentence", "built": True, "color": "#8e1b3a",
     "quote": "their bright velvety crimson hue", "source": "Sounds, of the sumach",
     "sees": "Sees the tense of each sentence: present, past, future, or a shift from one to the other turns the turtle, and the longest sentences become points.",
     "colophon": "Set in Cardo. Drawn by a turtle that reads sentences.",
     "turns": s_turns, "turnKinds": s_kinds, "turnAt": "at", "turnZoom": 16,
     "chapters": s_ch, "dots": s_dots, "end": [round(s_end[1], 6), round(s_end[0], 6)], "rules": s_rules, "keys": s_keys,
     "thumb": thumb(sx, sy)},
]
# Safety check: every quote must appear word for word in the book, or the script stops.
for L_ in LENSES:      # the quotes must be word for word in the book
    q = re.sub(r"\s+", " ", L_["quote"])
    assert a.skip_quote_check or q in re.sub(r"\s+", " ", raw), q

# (Unused leftover.)
end_pt = {"start": [a.start[0], a.start[1]]}
# ---- Everything the page needs, in one dictionary ----
#  This becomes a block of JavaScript data inside the page (the name D in lenses_body.html).
#  It includes the text itself so the page can build quotations and sentence popups on the fly.
data = {"title": a.title, "titlePrefix": a.title, "start": [a.start[0], a.start[1]], "startName": a.start_name,
        "chars": n, "text": text, "chBounds": [int(b_) for b_ in bounds], "chapterTitles": [c["title"] for c in chapters], "chapterIdx": [c["index"] for c in chapters],
        "lenses": LENSES, "pdfLabel": a.source_label,
        "credit": a.basemap_credit, "creditUrl": a.basemap_credit_url,
        "creditShort": "Basemap: [Gleason, Map of Concord (1906)], Lincoln Town Archives" if a.basemap_credit else "",
        "overlayColophon": "Set in Cardo. Drawn by a turtle that reads Walden more than one way.",
        "ramp": [hexes[round(i * (len(hexes) - 1) / 59)] for i in range(60)] if len(hexes) > 1 else hexes,
        "anchors": ramp.anchor_info(),
        "basemap": ({"bounds": [[a.basemap_bounds[0], a.basemap_bounds[1]], [a.basemap_bounds[2], a.basemap_bounds[3]]]} if a.basemap else None)}
# ---- Writing the files the React app reads ----
#  Unlike the single-file versions, nothing is pasted into a web page. The app loads these files when it starts:
#    <out>/walden.json     everything in the dictionary above (paths, points, turn arrows, colors, legend text, the book's text)
#    <out>/basemap.jpg     the 1906 map picture (shrunk to at most 4000 px)
#    <out>/walden.pdf      the source text, offered as a link in the legend
os.makedirs(a.out, exist_ok=True)

if a.source_pdf:
    shutil.copyfile(a.source_pdf, os.path.join(a.out, "walden.pdf"))
    data["pdfUrl"] = "data/walden.pdf"

if a.basemap:
    from PIL import Image
    assert a.basemap_bounds, "--basemap needs --basemap-bounds"
    im = Image.open(a.basemap).convert("RGB")
    im.thumbnail((4000, 4000))
    im.save(os.path.join(a.out, "basemap.jpg"), "JPEG", quality=82)
    data["basemap"]["url"] = "data/basemap.jpg"

json_path = os.path.join(a.out, "walden.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))     # separators: no extra spaces, so the file is smaller

# A summary printed in the terminal so you can see the numbers each lens produced.
print(f"punctuation: vertices {p_vert:,}  points {len(p_dots)}")
print(f"letter: turns {n_turns:,}  vertices {l_vert:,}  consonant points {sum(cons_n.values())} {dict(sorted(cons_n.items()))}  "
      f"vowel points {sum(vow_n.values())} {dict(sorted(vow_n.items()))}")
print(f"word: words {len(words):,}  turning {w_turning:,}  vertices {w_vert:,}  points {len(w_dots)} {dict(sorted(w_len.items()))}")
print(f"sentence reach {np.hypot(sx, sy).max() / 1000:.1f} km, end ({sx[-1] / 1000:.1f}, {sy[-1] / 1000:.1f}) km")
print(f"sentence: {len(srows):,} sentences {s_count}  vertices {s_vert:,}  points {len(s_dots)} by band {dict(sorted(s_bands.items()))}")
print(f"wrote {json_path}  {os.path.getsize(json_path) / 1e6:.2f} MB")
