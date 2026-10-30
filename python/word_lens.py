# =====================================================================================================
#  word_lens.py  --  the WORD lens rules.
# =====================================================================================================
#  THE RULES YOU MAY WANT TO EDIT:
#    * ANGLE      : how far each word type turns the turtle (degrees, clockwise).
#    * POS_TO_TYPE: which spaCy tags count as which type. Remove a line to stop that tag from turning.
#    * MIN_POINT  : the shortest word (in letters) that gets a point on the map.
#  After editing, delete walden_out / data 'word_tags.pkl' only if you changed how words are TAGGED.
#  If you only changed angles or thresholds, you do not need to delete it.

"""Word lens v1 rules (draft).
Step: one character, 1 m, spaces included. A word is a run of letters and apostrophes (hyphens and dashes split words).
Turn: at the first letter of a word, BEFORE its step, the turtle turns clockwise by the angle for the word's type, measured from its current heading:
  adjective 45, adverb 90, conjunction 135, noun 225, pronoun 270, verb 315. Other word types never turn.
Points: a dot at the end of each word of 12+ letters, sized by length (12..17).
Tagging: spaCy en_core_web_sm; a word with several tokens (contractions) takes its first token's tag.
  Proper nouns count as nouns; auxiliaries do not count as verbs; coordinating and subordinating conjunctions both count.
"""
import os, pickle, re, sys, unicodedata
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import walk_punct as W

# Turn for each word type, in degrees. These are all multiples of 45, because the engine only has 8 headings.
ANGLE = {"ADJ": 45, "ADV": 90, "CONJ": 135, "NOUN": 225, "PRON": 270, "VERB": 315}
# spaCy gives every word a 'part of speech' tag such as NOUN, PROPN, VERB, AUX. This table turns the tag into one of
#  our six types. PROPN (proper noun) counts as a noun. AUX (auxiliary verb: is, have, will) is NOT listed,
#  so it does not turn. Both kinds of conjunction (CCONJ and SCONJ) count.
POS_TO_TYPE = {"ADJ": "ADJ", "ADV": "ADV", "CCONJ": "CONJ", "SCONJ": "CONJ", "NOUN": "NOUN", "PROPN": "NOUN", "PRON": "PRON", "VERB": "VERB"}
# What counts as a word: letters, with apostrophes allowed inside (so don't is one word). Hyphens and dashes split words.
WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
# Words of this many letters or more get a point. Raise it for fewer points, lower it for more.
MIN_POINT = 12


# Finds every word and asks spaCy for its type. The first time this runs it takes a few minutes; the answer is
#  saved to the cache file (word_tags.pkl) and reused after that. Each word comes back as
#  (first character, end, number of letters, tag, start of its sentence).
def tag_words(text, cache=None):
    """Return list of (start, end, letters, pos) for every word in text."""
    base = "".join(unicodedata.normalize("NFD", c)[0] for c in text)
    assert len(base) == len(text)
    if cache and os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    import spacy
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    nlp.max_length = 3_000_000
    doc = nlp(text)
    tok_at = np.full(len(text) + 1, -1, dtype=np.int64)
    for i, t in enumerate(doc):
        tok_at[t.idx:t.idx + len(t.text)] = i
    out = []
    for m in WORD_RE.finditer(base):
        s, e = m.start(), m.end()
        i = tok_at[s]
        pos = doc[int(i)].pos_ if i >= 0 else "X"
        out.append((s, e, len(re.sub(r"[^A-Za-z]", "", m.group(0))), pos, doc[int(i)].sent.start_char if i >= 0 else -1))
    if cache:
        pickle.dump(out, open(cache, "wb"))
    return out


# Walks the text with the word rules. turn[s] is set at the FIRST letter of each turning word (the turn comes
#  BEFORE that letter's step). ANGLE // 45 converts degrees into heading units. The rest is the same arithmetic as
#  the other lenses: running total of turns -> heading -> cumulative x and y. Also returns the list of points
#  (last letter of each long word).
def walk_words(text, words):
    n = len(text)
    turn = np.zeros(n, dtype=np.int64)       # in 45 degree units, applied before the step of that character
    for s, e, L, pos, _ in words:
        t = POS_TO_TYPE.get(pos)
        if t:
            turn[s] = ANGLE[t] // 45
    after = np.cumsum(turn) % 8                # heading used by the step of character i (turn at i comes first)
    x = np.concatenate(([0.0], np.cumsum(W.SIN[after])))
    y = np.concatenate(([0.0], np.cumsum(W.COS[after])))
    dots = [(e - 1, L) for s, e, L, pos, _ in words if L >= MIN_POINT]     # index of last letter; point sits at x[e]
    return x, y, dots, turn
