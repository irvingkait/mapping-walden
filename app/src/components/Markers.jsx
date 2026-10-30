// Markers.jsx: the Incipit marker (where the text begins) and one Finis marker per lens (where it ends).
//
// They are ordinary page elements, not map shapes: the SDK would draw their labels in Esri's fonts, and we want Cardo.
// So we keep each one pinned to its spot on the map: whenever the view moves, we ask the view for the screen position
// and move the element there.
import { useEffect, useRef } from "react";
import * as reactiveUtils from "@arcgis/core/core/reactiveUtils.js";
import { mx, my, WM, esc } from "../map/geo.js";

export default function Markers({ map, D, s, onHover }) {
  const overlay = s.mode === "overlay";
  const lenses = D.lenses.filter(l => l.built);
  const els = useRef({});                  // the DOM elements, by key
  const where = useRef({});                // the latest screen position of each, by key

  // The list of markers: Incipit first, then a Finis for each lens.
  const items = [
    { key: "start", lat: D.start[0], lon: D.start[1], cls: "st", label: "Incipit", color: "#1a8a2e", shown: true,
      popup: esc(D.startName), w: 210 },
    ...lenses.map(l => {
      const active = overlay ? s.on[l.id] : s.lens === l.id;
      return { key: "end-" + l.id, lat: l.end[0], lon: l.end[1], cls: "", label: "Finis", shown: active,
        color: overlay ? l.color : undefined, fill: overlay ? l.color : undefined,
        popup: "Last character of the text" + (overlay ? "<br><small>" + esc(l.name) + " lens</small>" : ""), w: 170 };
    })
  ];

  // Move every marker to where its map position is on screen. Runs on every pan and zoom.
  useEffect(() => {
    const place = () => {
      items.forEach(it => {
        const el = els.current[it.key];
        if (!el) return;
        const p = map.view.toScreen({ type: "point", x: mx(it.lon), y: my(it.lat), spatialReference: WM });
        where.current[it.key] = p;
        el.style.transform = "translate(" + (p.x - 7) + "px," + (p.y - 7) + "px)";
      });
    };
    place();
    const handle = reactiveUtils.watch(() => [map.view.center.x, map.view.center.y, map.view.scale], place);
    return () => handle.remove();
  });

  return (
    <>
      {items.map(it => (
        <div key={it.key} className="lab" ref={el => { els.current[it.key] = el; }}
             style={{ display: it.shown ? "" : "none" }}
             onMouseOver={() => { const p = where.current[it.key]; if (p) onHover({ html: it.popup, x: p.x, y: p.y, rad: 8, w: it.w }); }}
             onMouseOut={() => onHover(null)}>
          <div className={"sq " + it.cls} style={it.fill ? { background: it.fill } : undefined}>
            <span style={it.color ? { color: it.color } : undefined}>{it.label}</span>
          </div>
        </div>
      ))}
    </>
  );
}
