// Walden.jsx: the whole map screen. Read this file first to see how the pieces fit together.
//
// THE IDEA
//   * The state (which lens, which chapters, basemap on or off ...) lives here, in one object called `s`.
//   * The controls (buttons, legend, ramp) are React components that read `s` and call `set(...)` to change it.
//   * The map itself is a WaldenMap object (src/map/WaldenMap.js). Small "effects" below copy the state into it.
//
// So: click a button -> set(...) changes `s` -> React redraws the controls -> an effect tells the map.
import { useEffect, useRef, useState } from "react";
import { WaldenMap } from "./map/WaldenMap.js";
import ModeBar from "./components/ModeBar.jsx";
import ZoomBar from "./components/ZoomBar.jsx";
import Legend from "./components/Legend.jsx";
import Plates from "./components/Plates.jsx";
import Footer from "./components/Footer.jsx";
import Markers from "./components/Markers.jsx";
import Popup from "./components/Popup.jsx";

export default function Walden({ D }) {
  const builtLenses = D.lenses.filter(l => l.built);

  // ---- the state: everything the controls can change ----
  const [s, setS] = useState(() => ({
    mode: "one",                                          // "one" (a single lens) or "overlay" (all lenses)
    lens: builtLenses[0].id,                              // which lens One lens mode shows
    on: Object.fromEntries(builtLenses.map(l => [l.id, true])),    // which lenses the Overlay shows
    dots: true, turns: true, starts: true,                // the Points, Turns and Chapter starts checkboxes
    base: false, fade: 15,                                // 1906 basemap: off at first, and how strong it is (percent)
    chap: D.chapterTitles.map(() => true)                 // one true/false per chapter
  }));
  const set = patch => setS(prev => ({ ...prev, ...patch }));       // change some fields, keep the rest

  const [map, setMap] = useState(null);                   // the WaldenMap, once it is ready
  const [popup, setPopup] = useState(null);               // the hover popup {html, x, y, rad, w}, or null
  const viewBox = useRef(null);                           // the empty <div> the ArcGIS view draws into
  const sNow = useRef(s); sNow.current = s;               // always the latest state, for use inside the setup effect
  const fitKey = useRef("");                              // remembers which view we last zoomed to fit

  // ---- create the map once, when the screen first appears ----
  useEffect(() => {
    const m = new WaldenMap(viewBox.current, D, { onHover: setPopup });
    let stopped = false;
    m.ready.then(async () => {
      if (stopped) return;
      m.apply(sNow.current);
      m.setBase(sNow.current.base, sNow.current.fade);
      fitKey.current = sNow.current.mode + sNow.current.lens;
      await m.fit(sNow.current, false);                    // zoom to the paths (no animation the first time)
      window.waldenMap = m;                               // handy for experiments: type waldenMap.view in the browser's console (F12)
      if (!stopped) setMap(m);
    });
    return () => { stopped = true; m.destroy(); setMap(null); };      // clean up if the screen goes away
  }, [D]);

  // ---- copy the state into the map whenever it changes ----
  useEffect(() => { if (map) map.apply(s); }, [map, s.mode, s.lens, s.on, s.dots, s.turns, s.starts, s.chap]);
  useEffect(() => { if (map) map.setBase(s.base, s.fade); }, [map, s.base, s.fade]);
  useEffect(() => {                                        // zoom to fit when the lens or the view mode changes
    const key = s.mode + s.lens;
    if (!map || fitKey.current === key) return;
    fitKey.current = key;
    map.fit(s, true);
  }, [map, s.mode, s.lens]);

  return (
    <div id="map">
      <div className="view" ref={viewBox} />               {/* the ArcGIS map is drawn in here */}
      <div id="aging" />                                   {/* the paper grain and darkened edges, over the map */}
      {map && <Markers map={map} D={D} s={s} onHover={setPopup} />}

      <div className="ctl tl">
        <ModeBar D={D} s={s} set={set} />
        <ZoomBar map={map} />
      </div>
      <div className="ctl tr">
        <Legend D={D} s={s} set={set} />
      </div>
      <div className="ctl bl">
        <Plates D={D} s={s} />
      </div>
      <Footer D={D} map={map} />
      <Popup popup={popup} map={map} />
    </div>
  );
}
