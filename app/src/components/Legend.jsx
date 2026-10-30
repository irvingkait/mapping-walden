// Legend.jsx: the panel at top right. It has a title, a link to the source PDF, and collapsible sections:
//   One lens mode: "Rules" (how this lens turns) and "Legend" (basemap, points, turns, chapter list)
//   Overlay mode:  "Lenses" (a checkbox per lens) and "Legend" (basemap, points, turns, chapter starts)
import { useState } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { esc, rgba } from "../map/geo.js";
import { FILL, DOT_A, radius, rsize } from "../map/symbols.js";

// A collapsible section. `open` is remembered by the Legend, so it survives switching lenses.
function Section({ name, label, open, setOpen, children }) {
  return (
    <details open={open[name]} onToggle={e => setOpen(name, e.currentTarget.open)}>
      <summary>{label}</summary>
      {children}
    </details>
  );
}

// The little "Point size" key shown inside a lens's Rules: circles of each size with their labels.
function Keys({ lens }) {
  return (
    <div className="keys">
      {lens.keys.map(k => (
        <div className="key" key={k.title}>
          <b>{k.title}</b>
          {k.sizes.map((n, j) => {
            const r = radius(rsize(k.kind, n));
            return (
              <span key={n}>
                <i className="dot" style={{ width: 2 * r, height: 2 * r, background: rgba(FILL[k.kind], DOT_A) }} />
                {k.labels ? k.labels[j] : n}
              </span>
            );
          })}
          <span>{k.unit}</span>
        </div>
      ))}
    </div>
  );
}

// A checkbox row.
function Check({ checked, onChange, children, className = "row" }) {
  return (
    <label className={className}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} /> {children}
    </label>
  );
}

export default function Legend({ D, s, set }) {
  const overlay = s.mode === "overlay";
  // Which sections are open. Starts with Rules and Lenses open, Legend closed.
  const [open, setOpenState] = useState({ rules: true, lenses: true, legend: false });
  const setOpen = (name, value) => setOpenState(o => ({ ...o, [name]: value }));

  const pdf = D.pdfUrl && (
    <p className="src"><a href={D.pdfUrl} target="_blank" rel="noopener">{D.pdfLabel}</a></p>
  );

  // The basemap checkbox and its fade slider (only if the data includes a basemap).
  const basemapRows = D.basemap && (
    <>
      <Check checked={s.base} onChange={v => set({ base: v })}>Basemap</Check>
      <div className="fade">
        <span>fade</span>
        <input type="range" min="15" max="100" value={s.fade} onChange={e => set({ fade: +e.target.value })} />
      </div>
    </>
  );
  const pointRows = (
    <>
      <Check checked={s.dots} onChange={v => set({ dots: v })}>Points</Check>
      <Check checked={s.turns} onChange={v => set({ turns: v })}>Turns <small>(arrows appear when zoomed in close)</small></Check>
    </>
  );

  // ---------------- One lens ----------------
  if (!overlay) {
    const lens = D.lenses.find(l => l.id === s.lens);
    const toggleChapter = (i, v) => set({ chap: s.chap.map((c, k) => (k === i ? v : c)) });
    // lens.rules is HTML written by Python. It contains a marker <!--KEYS--> where the point-size key belongs.
    const rulesHtml = lens.rules.replace("<!--KEYS-->", renderToStaticMarkup(<Keys lens={lens} />));
    return (
      <div className="panel legend">
        <h1>{D.titlePrefix + lens.name}</h1>
        {pdf}
        <div className="orn"><i /></div>
        <Section name="rules" label="Rules" open={open} setOpen={setOpen}>
          <ol dangerouslySetInnerHTML={{ __html: rulesHtml }} />
        </Section>
        <Section name="legend" label="Legend" open={open} setOpen={setOpen}>
          {basemapRows}
          {pointRows}
          <p><b>Chapters</b> &middot;{" "}
            <a href="#" onClick={e => { e.preventDefault(); set({ chap: s.chap.map(() => true) }); }}>all</a> &middot;{" "}
            <a href="#" onClick={e => { e.preventDefault(); set({ chap: s.chap.map(() => false) }); }}>none</a></p>
          {D.chapterTitles.map((t, i) => (
            <Check key={i} checked={s.chap[i]} onChange={v => toggleChapter(i, v)}>
              <span className="sw" style={{ background: lens.chapters[i].color }} />
              {D.chapterIdx[i] + ". " + t}
            </Check>
          ))}
        </Section>
        <div className="orn"><i /></div>
        <p className="colophon">{lens.colophon}</p>
      </div>
    );
  }

  // ---------------- Overlay ----------------
  const square = (l, extra) => <i className="sym" style={{ width: 12, height: 12, background: rgba(l.color, 0.5), border: "1px solid #000", ...extra }} />;
  return (
    <div className="panel legend">
      <h1>{D.titlePrefix + "Overlay"}</h1>
      {pdf}
      <div className="orn"><i /></div>
      <Section name="lenses" label="Lenses" open={open} setOpen={setOpen}>
        {D.lenses.map(l => (
          <label key={l.id} className={"lensrow" + (l.built ? "" : " todo")}>
            <input type="checkbox" className="lensbox" disabled={!l.built} checked={l.built ? !!s.on[l.id] : false}
                   onChange={e => set({ on: { ...s.on, [l.id]: e.target.checked } })} />
            <span className="nm">
              <b>{l.name}</b>
              <span className="sw" style={{ background: l.color }} />
              {l.built && square(l)}
              {/* the Letter lens has a second kind of point: a hollow ring for vowels */}
              {l.built && l.id === "letter" && <i className="sym" style={{ width: 12, height: 12, border: "2.5px solid " + l.color, background: rgba(l.color, 0.12) }} />}
            </span>
            <span className="sees">{l.built ? l.sees : "Not designed yet."}</span>
          </label>
        ))}
      </Section>
      <Section name="legend" label="Legend" open={open} setOpen={setOpen}>
        {basemapRows}
        {pointRows}
        <Check checked={s.starts} onChange={v => set({ starts: v })}>Chapter starts</Check>
      </Section>
      <div className="orn"><i /></div>
      <p className="colophon">{D.overlayColophon}</p>
    </div>
  );
}
