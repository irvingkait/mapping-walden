// symbols.js: how things LOOK on the map. A "symbol" is ArcGIS's word for a style: a line's color and width,
// a circle's fill and outline, an arrow's shape.
//
// Symbols are cached: asking twice for the same look returns the same object, which keeps the map fast.

import { PT, hexA } from "./geo.js";

// ---- point (dot) sizes ----
export const FILL = { p: "#ff8c1a", c: "#ff8c1a", v: "#e5252a", w: "#ff8c1a", s: "#ff8c1a" };   // orange; vowels red
export const DOT_A = 0.18;                                    // how see-through the orange fill is
// The size number in the data (for example "3 marks in a row") -> the number that sets the radius.
export const rsize = (kind, size) =>
  kind === "c" ? size - 2 : kind === "v" ? size - 1 : kind === "w" ? 2 + (size - 12) / 2 : kind === "s" ? 2 + (size - 2) * 0.6 : size;
// The base radius in pixels for a size number. Bigger runs get bigger circles, up to 20 px.
export const radius = size => Math.min(3 + 2.5 * (size - 2), 20);

export const Z100 = 16;        // dots keep their base size at and below this zoom, then grow with the ground
export const START_R = 8;      // radius of a chapter-start diamond at the base zoom, in pixels
export const dotScale = (zoom, cap) => Math.max(1, Math.pow(2, Math.min(zoom, cap || 18) - Z100));
export const startRadius = zoom => Math.max(3, START_R * Math.pow(0.8, Math.max(0, zoom - Z100)));

const cache = new Map();
const cached = (key, make) => {
  let s = cache.get(key);
  if (!s) { s = make(); cache.set(key, s); }
  return s;
};

// A chapter's path.
export const lineSym = color => cached("line" + color, () =>
  ({ type: "simple-line", color: hexA(color, 0.9), width: 2 * PT, cap: "round", join: "round" }));

// A point. r is the radius in pixels. In One lens mode points are orange with a black outline; in the Overlay they take
// their lens's color (vowel points in the Letter lens are hollow rings).
export function dotSym(lens, kind, r, overlay) {
  const rr = Math.round(r * 4) / 4;
  return cached((overlay ? "o" + lens.id : "n") + kind + rr, () => {
    let fill, line;
    if (!overlay) { fill = hexA(FILL[kind], DOT_A); line = { color: [0, 0, 0, 1], width: 1 * PT }; }
    else if (kind === "v") { fill = hexA(lens.color, 0.12); line = { color: hexA(lens.color, 1), width: 2.5 * PT }; }
    else { fill = hexA(lens.color, 0.5); line = { color: [0, 0, 0, 1], width: 1 * PT }; }
    return { type: "simple-marker", style: "circle", size: 2 * rr * PT, color: fill, outline: line };
  });
}

// A chapter-start marker is two symbols stacked: a white diamond with a brown outline, and a brown dot in its middle.
export function startSyms(px) {
  const q = Math.round(px * 2) / 2;
  return cached("start" + q, () => [
    { type: "simple-marker", style: "diamond", size: q * PT, color: [255, 255, 255, 0.65], outline: { color: [107, 58, 20, 1], width: 2 * PT } },
    { type: "simple-marker", style: "circle", size: Math.min(5, q * 0.35) * PT, color: [107, 58, 20, 1], outline: { color: [107, 58, 20, 0], width: 0 } }]);
}

// A turn arrow. It is drawn with a "CIM" symbol (ArcGIS's detailed symbol format) made of a paper-colored halo,
// the colored arrow, and a small dot at the turn. There are eight headings (every 45 degrees), so only eight
// arrows per color are ever made; the rotation is done here, so no rotation setting is needed.
export function arrowSym(heading, color) {
  return cached("arrow" + heading + color, () => {
    const t = heading * Math.PI / 4, c = Math.cos(t), s = Math.sin(t);
    const rot = ([x, y]) => [x * c + y * s, -x * s + y * c];          // turn clockwise by heading * 45 degrees (y is up)
    const path = [[[0, 0], [0, 11]].map(rot), [[-4, 6.5], [0, 12], [4, 6.5]].map(rot)];     // the shaft and the arrowhead
    const stroke = (w, col) => ({ type: "CIMLineSymbol", symbolLayers: [{ type: "CIMSolidStroke", enable: true, width: w * PT, color: col, capStyle: "Round", joinStyle: "Round" }] });
    const ring = Array.from({ length: 17 }, (_, k) => [2.2 * Math.cos(k * Math.PI / 8), 2.2 * Math.sin(k * Math.PI / 8)]);
    const paper = [244, 234, 208, 255], ink = hexA(color, 255);
    return { type: "cim", data: { type: "CIMSymbolReference", symbol: { type: "CIMPointSymbol", symbolLayers: [{
      type: "CIMVectorMarker", enable: true, size: 30 * PT, anchorPoint: { x: 0, y: 0 }, anchorPointUnits: "Relative",
      frame: { xmin: -15, ymin: -15, xmax: 15, ymax: 15 },
      markerGraphics: [
        { type: "CIMMarkerGraphic", geometry: { paths: path }, symbol: stroke(4.5, paper) },       // halo, so arrows read over busy paths
        { type: "CIMMarkerGraphic", geometry: { paths: path }, symbol: stroke(1.6, ink) },         // the arrow
        { type: "CIMMarkerGraphic", geometry: { rings: [ring] }, symbol: { type: "CIMPolygonSymbol", symbolLayers: [
          { type: "CIMSolidStroke", enable: true, width: 1 * PT, color: paper }, { type: "CIMSolidFill", enable: true, color: ink }] } }] }] } } };
  });
}
