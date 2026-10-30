// Popup.jsx: the small box that appears when you point at a dot, a chapter start, a turn arrow or a marker.
// It is placed above the thing pointed at, or below it if there is no room, and kept inside the map.
import { useLayoutEffect, useRef, useState } from "react";

export default function Popup({ popup, map }) {
  const box = useRef(null);
  const [pos, setPos] = useState({ left: 0, top: 0 });

  // useLayoutEffect runs after the box is drawn but before the screen updates, so we can measure its height.
  useLayoutEffect(() => {
    if (!popup || !map || !box.current) return;
    const { width, height } = map.view;
    const h = box.current.offsetHeight, w = popup.w;
    const left = Math.min(Math.max(popup.x - w / 2, 8), width - w - 8);
    let top = popup.y - popup.rad - 10 - h;                     // try above
    if (top < 8) top = popup.y + popup.rad + 12;                // no room: go below
    if (top + h > height - 8) top = Math.max(8, height - h - 8);
    setPos({ left, top });
  }, [popup, map]);

  return (
    <div className="rp-tip pop" ref={box}
         style={{ display: popup ? "block" : "none", width: popup ? popup.w : undefined, left: pos.left, top: pos.top }}
         dangerouslySetInnerHTML={{ __html: popup ? popup.html : "" }} />      // the html was built (and escaped) in popupHtml.js
  );
}
