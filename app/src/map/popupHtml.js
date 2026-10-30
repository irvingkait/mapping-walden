// popupHtml.js: the words in the hover popups. Each function returns a small piece of HTML (as text).
//
// The book's own text is run through esc() first, so a "<" or "&" in it cannot break the page.

import { esc } from "./geo.js";

const WORD = { p: "marks", c: "consonants", v: "vowels" };     // what a point counts, by kind

// Pass in the data D once; get back the popup writers.
export function makePopupWriters(D) {
  // In the Overlay a popup also says which lens it belongs to.
  const lensTag = (lens, overlay) => overlay ? "<br><small>" + esc(lens.name) + " lens</small>" : "";

  // Which chapter a character position falls in (0 = the first chapter).
  const chapOfOffset = o => { let c = 0; while (c + 1 < D.chapterTitles.length && o >= D.chBounds[c + 1]) c++; return c; };

  // A snippet of the book around positions s..e, cut at word boundaries: [before, the part to bold, after].
  function ctxOf(s, e) {
    const t = D.text, n = t.length;
    let a0 = Math.max(0, s - 28);
    while (a0 > 0 && a0 < s && t[a0 - 1] !== " ") a0++;
    let b0 = Math.min(n, e + 29);
    while (e + 1 < b0 && b0 < n && t[b0] !== " ") b0--;
    return [t.slice(a0, s), t.slice(s, e + 1), t.slice(e + 1, b0)];
  }
  const quote = c => "<br>&hellip;" + esc(c[0]) + "<b>" + esc(c[1]) + "</b>" + esc(c[2]) + (c[3] ? "" : "&hellip;");

  const chapterLine = ch => '<b class="ch">' + esc(D.chapterIdx[ch] + ". " + D.chapterTitles[ch]) + "</b>";

  // Hovering a chapter-start diamond.
  const startHtml = (lens, i, overlay) =>
    '<div class="tt"><b class="ch">Start chapter ' + D.chapterIdx[i] + "</b><br>" + esc(D.chapterTitles[i]) + lensTag(lens, overlay) + "</div>";

  // Hovering a sentence (a Sentence-lens point, or a Sentence-lens turn arrow): shows the sentence with its verbs in bold.
  function sentHtml(lens, s, overlay) {
    if (!lens._sd) {          // build two lookup tables the first time, then reuse them
      lens._sd = new Map(lens.dots.map(d => [d[4], d]));
      lens._st = new Map(lens.turns.sent.map((v, i) => [v, i]));
    }
    const d = lens._sd.get(s), ti = lens._st.get(s), T = lens.turns, t = D.text;
    const k = d ? +d[7] : T.off[ti], ch = chapOfOffset(s);
    const hl = ti !== undefined ? T.hl[ti] : [];
    let h = '<div class="tt">' + chapterLine(ch);
    if (d) h += "<br>" + d[5] + "-word sentence, beginning at character " + s.toLocaleString();
    if (ti !== undefined) {
      const lab = T.word[ti];
      h += "<br>" + lab.charAt(0).toUpperCase() + lab.slice(1) + ": " + lens.turnKinds[T.code[ti] >> 3][1] + " at character " + k.toLocaleString();
    } else h += "<br>No tensed verb: the turtle goes straight at character " + k.toLocaleString();
    let a = s, b = k + 1, pre = "", post = "";
    if (!d && b - a > 360) {      // a very long sentence is shortened around its first verb
      a = Math.max(s, (hl.length ? hl[0] : s) - 100); b = Math.min(k + 1, a + 360);
      if (a > s) { while (a < b && t[a - 1] !== " ") a++; pre = "&hellip;"; }
      if (b < k + 1) { while (b > a && t[b] !== " ") b--; post = "&hellip;"; }
    }
    let body = "", pos = a;
    for (let j = 0; j < hl.length; j += 2) {      // hl holds pairs: where each highlighted verb starts and ends
      if (hl[j] < a || hl[j + 1] > b) continue;
      body += esc(t.slice(pos, hl[j])) + "<b>" + esc(t.slice(hl[j], hl[j + 1])) + "</b>";
      pos = hl[j + 1];
    }
    body += esc(t.slice(pos, b));
    return h + "<br>&ldquo;" + pre + body + post + "&rdquo;" + lensTag(lens, overlay) + "</div>";
  }

  // Hovering a point (a run of marks, letters, a long word).
  function dotHtml(lens, item, overlay) {
    const [, , size, ch, off, pre, run, post, kind] = item.d;
    if (kind === "s") return sentHtml(lens, off, overlay);
    return '<div class="tt">' + chapterLine(ch) + "<br>" +
      (kind === "w" ? size + "-letter word, beginning at character " : size + " " + WORD[kind] + " in a row, beginning at character ") + off.toLocaleString() +
      "<br>&hellip;" + esc(pre) + "<b>" + esc(run) + "</b>" + esc(post) + "&hellip;" + lensTag(lens, overlay) + "</div>";
  }

  // Hovering a turn arrow: what dictated the turn.
  function turnHtml(lens, i, ch, overlay) {
    if (lens.id === "sentence") return sentHtml(lens, lens.turns.sent[i], overlay);
    const T = lens.turns, kind = lens.turnKinds[T.code[i] >> 3];
    return '<div class="tt">' + chapterLine(ch) + "<br>" +
      (lens.id !== "word"
        ? "&ldquo;<b>" + esc(T.word[i]) + "</b>&rdquo;: " + kind[1] + " at character " + T.off[i].toLocaleString() + (T.ctx ? quote(T.ctx[i]) : "")
        : "&ldquo;<b>" + esc(T.word[i]) + "</b>&rdquo; is " + kind[0] + ": " + kind[1] + ", " + lens.turnAt + " character " + T.off[i].toLocaleString() +
          quote(ctxOf(T.off[i], T.off[i] + T.word[i].length - 1))) +
      lensTag(lens, overlay) + "</div>";
  }

  return { startHtml, dotHtml, turnHtml, lensTag };
}
