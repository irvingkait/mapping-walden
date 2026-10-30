# =====================================================================================================
#  clean_walden.py  --  turns the raw text pulled out of the Walden PDF into clean.txt and chapters.json.
# =====================================================================================================
#  You do NOT need this to rebuild the map: clean.txt and chapters.json are already provided in data/.
#  Run it only if you start from a different edition. It assumes this specific edition's layout (page numbers,
#  drop caps, headings on their own lines), so a different book or edition will need edits.
#  It keeps only Thoreau's running prose: drops the front matter, the table of contents, chapter headings,
#  page numbers, asterism lines (* * *) and the dotted leaders in the cost tables, and rejoins the drop caps.

"""Clean the Walden PDF text (Internet Bookmobile edition) for the punctuation lens.

Reads raw text from `pdftotext` (plain mode, form feeds kept) and writes:
  clean.txt       prose only, chapters joined by a newline
  chapters.json   [{index, title, start}] with start = offset of each chapter's first character in clean.txt
  cleaning_log.txt  what was removed and why

Usage: python3 -I clean_walden.py raw.txt outdir
"""
import json
import re
import sys

raw_path, outdir = sys.argv[1], sys.argv[2]
lines = open(raw_path, encoding="utf-8").read().split("\n")

# The 18 chapter titles, in order. These are matched against the heading lines in the raw text.
TITLES = [
    "Economy",
    "Where I Lived, and What I Lived For",
    "Reading",
    "Sounds",
    "Solitude",
    "Visitors",
    "The Bean-Field",
    "The Village",
    "The Ponds",
    "Baker Farm",
    "Higher Laws",
    "Brute Neighbors",
    "House-Warming",
    "Former Inhabitants; and Winter Visitors",   # printed on two lines in the PDF
    "Winter Animals",
    "The Pond in Winter",
    "Spring",
    "Conclusion",
]


def first_line_of(title):
    return "Former Inhabitants; and Winter" if title.startswith("Former Inhabitants") else title


# ---- locate chapter headings in order ----
# Find the line number of each chapter heading.
heads = []
pos = 0
for title in TITLES:
    target = first_line_of(title)
    i = next(k for k in range(pos, len(lines)) if lines[k].lstrip("\f").strip() == target
             and lines[k].startswith("\f"))
    heads.append(i)
    pos = i + 1
assert heads == sorted(heads) and len(heads) == 18

# Everything from the line 'THE END' onward is dropped.
end = next(i for i, l in enumerate(lines) if l.strip() == "THE END")
bounds = heads + [end]

log = []
log.append(f"front matter and contents dropped: lines 0..{heads[0] - 1}")
log.append("end matter dropped from 'THE END' on")

page_nums = 0
asterism_runs = 0
leader_runs = 0
dotline_runs = 0
leader_periods = 0
chapters_text = []

# Pattern for the decorative * * * lines.
ASTERISM = re.compile(r"(?:\*[ \t]*){2,}")
# dot leaders in the two account ledgers: periods after a comma, optionally spaced
# Pattern for the dotted fill ('......') in the account ledgers.
LEADER = re.compile(r"(?<=,)[ \t]?(?:\.[ \t\n]?){2,}")
# lines made only of dots (a leader whose value sits on another line)
# Pattern for lines made only of dots.
DOTLINE = re.compile(r"(?m)^[ \t]*(?:\.[ \t]*){5,}$")

# Process one chapter at a time.
for n, title in enumerate(TITLES):
    a, b = bounds[n], bounds[n + 1]
    seg = lines[a:b]
    # skip heading line(s), blank, then drop cap letter, then rest of the first word
    k = 1
    if title.startswith("Former Inhabitants"):
        assert seg[1].strip() == "Visitors"
        k = 2
    while seg[k].strip() == "":
        k += 1
    # The big first letter (drop cap) sits alone on its own line; it is glued back onto its word.
    cap = seg[k].strip()
    assert re.fullmatch(r"[A-Z]", cap), (title, cap)
    k += 1
    while seg[k].strip() == "":
        k += 1
    assert seg[k][0].islower() or seg[k][0] in "aeiou", (title, seg[k][:20])
    # "I" is a whole word when the next token is a full word ("I think"), but a drop cap
    # when the next token is a single letter ("I" + "n October" = "In October").
    first_token = seg[k].split(" ")[0]
    sep = " " if (cap == "I" and len(first_token) > 1) else ""
    out = [cap + sep + seg[k]]
    for l in seg[k + 1:]:
        s = l.replace("\f", "")
        if re.fullmatch(r"\s*\d{1,3}\s*", s):
            page_nums += 1
            continue
        out.append(s)
    t = "\n".join(out)
    asterism_runs += len(ASTERISM.findall(t))
    t = ASTERISM.sub(" ", t)
    for m in DOTLINE.finditer(t):
        dotline_runs += 1
        leader_periods += m.group(0).count(".")
    t = DOTLINE.sub("", t)
    for m in LEADER.finditer(t):
        leader_runs += 1
        leader_periods += m.group(0).count(".")
    t = LEADER.sub(" ", t)
    chapters_text.append(t.strip())

# Join the chapters into one text. starts[] records where each chapter begins.
clean = "\n".join(chapters_text)
starts, off = [], 0
for t in chapters_text:
    starts.append(off)
    off += len(t) + 1
chapters = [{"index": i + 1, "title": TITLES[i], "start": starts[i]} for i in range(18)]
for c in chapters:
    assert clean[c["start"]].isupper(), c

# Write the three output files: the text, the chapter list, and a log of what was removed.
open(f"{outdir}/clean.txt", "w", encoding="utf-8").write(clean)
json.dump(chapters, open(f"{outdir}/chapters.json", "w", encoding="utf-8"), indent=1)

log.append("18 chapter headings removed (titles kept in chapters.json); 18 drop caps rejoined to their words")
log.append(f"page-number lines removed: {page_nums}")
log.append(f"asterism runs removed (* * *, ****): {asterism_runs}")
log.append(f"ledger dot leaders removed: {leader_runs} after-comma runs + {dotline_runs} all-dot lines "
           f"({leader_periods} periods in total); prose ellipses (letter then '. . . .') kept")
log.append(f"clean.txt: {len(clean)} characters, {len(clean.split())} whitespace-separated words")
open(f"{outdir}/cleaning_log.txt", "w", encoding="utf-8").write("\n".join(log) + "\n")
print("\n".join(log))
for c in chapters:
    print(f'{c["index"]:>2} {c["start"]:>7}  {c["title"]:<42} {clean[c["start"]:c["start"] + 40]!r}')
