// ZoomBar.jsx: the + and - buttons. We draw our own so they match the paper look.
export default function ZoomBar({ map }) {
  const click = step => e => { e.preventDefault(); if (map) map.zoomBy(step); };
  return (
    <div className="zoombar">
      <a href="#" title="Zoom in" role="button" onClick={click(1)}>+</a>
      <a href="#" title="Zoom out" role="button" onClick={click(-1)}>&#x2212;</a>
    </div>
  );
}
