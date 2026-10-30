// Footer.jsx: the thin bar at the bottom. Scale line on the left; on the right, the basemap credit and "Powered by Esri".
import { useEffect, useRef, useState } from "react";
import Attribution from "@arcgis/core/widgets/Attribution.js";
import * as reactiveUtils from "@arcgis/core/core/reactiveUtils.js";
import { D2R } from "../map/geo.js";

// Round a distance to a "nice" number: 1, 2, 3, 5, 10, 20, 30, 50, 100 ...
function niceNum(n) {
  const p = Math.pow(10, Math.floor(n).toString().length - 1), d = n / p;
  return p * (d >= 10 ? 10 : d >= 5 ? 5 : d >= 3 ? 3 : d >= 2 ? 2 : 1);
}

export default function Footer({ D, map }) {
  const attrBox = useRef(null);
  const [metersPerPixel, setMpp] = useState(null);

  // Keep metersPerPixel up to date as the view zooms or moves.
  useEffect(() => {
    if (!map) return;
    const update = () => setMpp(map.view.resolution * Math.cos(map.view.center.latitude * D2R));     // ground meters per screen pixel
    update();
    const h = reactiveUtils.watch(() => [map.view.resolution, map.view.center.latitude], update);
    return () => h.remove();
  }, [map]);

  // Esri's attribution widget. Esri requires "Powered by Esri" to stay visible.
  useEffect(() => {
    if (!map || !attrBox.current) return;
    const widget = new Attribution({ view: map.view, container: attrBox.current });
    return () => widget.destroy();
  }, [map]);

  // The scale line: the longest "nice" distance that fits in about 100 pixels.
  let scale = null;
  if (metersPerPixel) {
    const maxM = metersPerPixel * 100;
    const m = maxM < 1000 ? niceNum(maxM) : niceNum(maxM / 1000) * 1000;
    scale = { width: Math.round(m / metersPerPixel), label: m >= 1000 ? m / 1000 + " km" : m + " m" };
  }

  // creditShort looks like "Basemap: [Gleason, Map of Concord (1906)], Lincoln Town Archives". The part in [ ] becomes a link.
  const credit = D.credit && (() => {
    const m = D.creditShort.match(/^(.*?)\[(.+?)\](.*)$/);
    if (!m) return D.creditShort;
    return <>{m[1]}{D.creditUrl ? <a href={D.creditUrl} target="_blank" rel="noopener">{m[2]}</a> : m[2]}{m[3]}</>;
  })();

  return (
    <div className="footer">
      <div className="fl">{scale && <div className="scaleline" style={{ width: scale.width }}>{scale.label}</div>}</div>
      <div className="fr">
        {credit && <span className="bc">{credit}</span>}
        <div className="attr" ref={attrBox} />
      </div>
    </div>
  );
}
