# =====================================================================================================
#  sentence_lens.py  --  the SENTENCE lens rules.
# =====================================================================================================
#  THE RULES YOU MAY WANT TO EDIT:
#    * ANGLE   : the turn for each tense (degrees, clockwise).
#    * MIN_WORDS / BANDS : sentences of MIN_WORDS words or more get a point; BANDS are the lower edges of the
#      size groups (50, 60, 70, 80, 100+).
#  Changing ANGLE, MIN_WORDS or BANDS does not need a re-tag. Changing HOW tense is detected (the classify
#  function) does: delete sent_tense.pkl first.

"""Sentence lens v1 (draft).
Step: one character, 1 m, spaces included (step first, then turn, as in the punctuation and letter lenses).
Turn: at the end of each sentence, by the tense of its verbs, clockwise from the turtle's heading:
  present only 135, past only 315, future (will or shall, and neither past nor present) 45, past and present together 225.
  All four are oblique, like the letter lens.
  A sentence with no tensed verb goes straight. Other modal verbs (would, can, may...) are ignored.
Points: a dot at the end of each sentence of 50 or more words, sized in bands (50, 60, 70, 80, 100+).
Sentences and verb tenses are read by spaCy (en_core_web_sm).
"""
import os, pickle, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import word_lens as WL

# Turn for each tense, in degrees clockwise. 'shift' means a sentence with both past and present verbs.
ANGLE = {"present": 135, "past": 315, "future": 45, "shift": 225}
# The order of the kinds. The page refers to them by number, so keep this order.
KINDS = ["present", "past", "future", "shift"]
# A sentence needs at least this many words to get a point.
MIN_WORDS = 50
# Lower edge of each point-size group.
BANDS = [50, 60, 70, 80, 100]          # lower edge of each size band


# Reads the whole text with spaCy and, for every sentence, decides its tense class. The first run takes a few
#  minutes; the answer is cached in sent_tense.pkl. Returns one row per sentence:
#  (first character, last character, class, the words that gave the tense).
def classify(text, cache=None):
    """List of (start, last_char_index, tense_class, spans) for every sentence; spans are the (start, end) offsets of the words
    that gave the sentence its tense."""
    if cache and os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    import spacy
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    nlp.max_length = 3_000_000
    rows = []
    # Loop over every sentence spaCy found.
    for sent in nlp(text).sents:
        ts, sp = set(), {"future": [], "past": [], "present": []}
        # Loop over every word (token) t in the sentence, looking only at verbs.
        for t in sent:
            # Only verbs and auxiliary verbs (is, was, will ...) can carry tense.
            if t.pos_ in ("VERB", "AUX"):
                m, tn = t.morph.get("VerbForm"), t.morph.get("Tense")
                # WILL or SHALL (modal verbs) means future. Other modals (would, can, may) are ignored.
                if t.tag_ == "MD" and t.lower_ in ("will", "shall", "'ll"):
                    ts.add("future")
                    sp["future"].append((t.idx, t.idx + len(t.text)))
                    if t.head is not t and t.head.pos_ in ("VERB", "AUX") and t.head.i > t.i:
                        sp["future"].append((t.head.idx, t.head.idx + len(t.head.text)))
                # A finite verb (one that has a tense, not an infinitive or participle) marked Past.
                elif "Fin" in m and "Past" in tn:
                    ts.add("past")
                    sp["past"].append((t.idx, t.idx + len(t.text)))
                # A finite verb marked Present.
                elif "Fin" in m and "Pres" in tn:
                    ts.add("present")
                    sp["present"].append((t.idx, t.idx + len(t.text)))
        # Decide the sentence's class: both past and present -> 'shift'; else any future -> 'future'; else past; else
        #  present; else 'none' (no tensed verb, so the turtle goes straight).
        cls = ("shift" if {"past", "present"} <= ts else "future" if "future" in ts else "past" if "past" in ts
               else "present" if "present" in ts else "none")
        # k is the last real character of the sentence (trailing spaces are skipped).
        k = sent.end_char - 1
        while k > sent.start_char and text[k] == " ":
            k -= 1
        # The offsets of the words that gave the sentence its tense, so the popup can show them in bold.
        spans = sorted(set(sp["past"] + sp["present"])) if cls == "shift" else sorted(set(sp[cls])) if cls != "none" else []
        rows.append((sent.start_char, k, cls, spans))
    if cache:
        pickle.dump(rows, open(cache, "wb"))
    return rows


# Counts the words in a sentence.
def word_count(text, s, k):
    return len(WL.WORD_RE.findall(text[s:k + 1]))


# Turns a word count into a point size group, or None if the sentence is too short to get a point.
def band(count):
    """Size 2.. for the point of a sentence of `count` words (None below the minimum)."""
    if count < MIN_WORDS:
        return None
    return 2 + max(i for i, b in enumerate(BANDS) if count >= b)
