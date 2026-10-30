// Plates.jsx: the bottom row: a north arrow, the plate caption, and the color ramp.
//   The ramp shows the chapter colors (One lens) or the four lens colors (Overlay). Hover a white tick to read the
//   quotation from Walden that the color was taken from.
import { useRef, useState } from "react";
import { esc } from "../map/geo.js";

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"];

export default function Plates({ D, s }) {
  const overlay = s.mode === "overlay";
  const rampBox = useRef(null);
  const [tip, setTip] = useState(null);            // {k, left, bottom} of the tooltip, or null

  // Plate I to IV are the four lenses; the Overlay is Plate V.
  const plate = ROMAN[overlay ? D.lenses.length : D.lenses.findIndex(l => l.id === s.lens)];

  // The marks along the ramp: where each quotation sits, from 0 (left) to 1 (right).
  const anchors = overlay
    ? D.lenses.map((l, k) => ({ hex: l.color, quote: l.quote, source: l.source, label: l.name, pos: k / (D.lenses.length - 1) }))
    : D.anchors;
  const gradient = overlay
    ? "linear-gradient(to right," + anchors.map(a => a.hex + " " + a.pos * 100 + "%").join(",") + ")"
    : "linear-gradient(to right," + D.ramp.join(",") + ")";

  // Show the tooltip above the tick under the mouse. The tooltip uses "fixed" positioning, so these numbers
  // are measured from the browser window (not from the map).
  const showTip = (e, k) => {
    const tick = e.currentTarget.getBoundingClientRect();
    const ramp = rampBox.current.getBoundingClientRect();
    const w = 210;                                                  // the tooltip's width, set in styles.css
    setTip({ k, left: Math.min(Math.max(tick.left + tick.width / 2 - w / 2, 8), window.innerWidth - w - 8), bottom: window.innerHeight - ramp.top + 8 });
  };
  const a = tip && anchors[tip.k];

  return (
    <div className="plates">
      <div className="panel north" style={{ padding: "6px 8px 4px" }}>
        <svg width="20" height="30" viewBox="0 0 20 30">
          <path d="M10 1 L17 27 L10 21 L3 27 Z" fill="#2a2118" stroke="#2a2118" strokeLinejoin="round" />
          <path d="M10 1 L10 21 L3 27 Z" fill="#efe2c1" />
        </svg>N
      </div>
      <div className="panel plate">
        <b>Plate {plate}</b>
        <i>The path of {D.chars.toLocaleString()} characters,<br />one meter to each.</i>
      </div>
      <div className="panel ramp-panel" ref={rampBox}>
        <div className="rbar" style={{ background: gradient }}>
          {anchors.map((an, k) => (
            <i key={k} className="tick" style={{ left: an.pos * 100 + "%" }}
               onMouseEnter={e => showTip(e, k)} onMouseLeave={() => setTip(null)} />
          ))}
        </div>
        <div className="cap">
          {overlay ? (
            <>
              <span>{D.lenses[0].name}</span>
              <em>The colors of autumn, in Thoreau&rsquo;s words</em>
              <span>{D.lenses[D.lenses.length - 1].name}</span>
            </>
          ) : (
            <>
              <span>Chapter 1</span>
              <em>The colors of Walden Pond, in Thoreau&rsquo;s words</em>
              <span>Chapter {D.chapterTitles.length}</span>
            </>
          )}
        </div>
      </div>
      {/* the tooltip itself */}
      {tip && (
        <div className="rp-tip" style={{ display: "block", left: tip.left, bottom: tip.bottom, top: "auto", position: "fixed" }}>
          <code>{a.label ? a.label + " · " : ""}{a.hex}</code>
          <q>{a.quote}</q>
          <small>{a.source}</small>
        </div>
      )}
    </div>
  );
}
