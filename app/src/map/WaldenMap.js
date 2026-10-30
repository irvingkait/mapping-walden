// WaldenMap.js: everything that talks to the ArcGIS SDK. React does not know how the map is drawn; it just creates
// one WaldenMap, tells it when the controls change (apply, setBase, fit), and listens for hover events.
//
// Why a plain class and not a React component? The map holds thousands of shapes and its own animation loop.
// Letting React re-create them on every click would be slow, so we build every shape ONCE and afterwards only
// hide, show and restyle them.
//
// The ArcGIS words used here:
//   MapView        the window onto the map (zooming, panning, pixel <-> ground conversion)
//   Map            the container of layers (ours has no Esri basemap; the 1906 picture is our basemap)
//   GraphicsLayer  a layer holding shapes we draw ourselves
//   Graphic        one shape: geometry (where) + symbol (look) + attributes (notes we attach)
//   MediaLayer     a layer that places a picture on the map by its corners

import esriConfig from "@arcgis/core/config.js";
import EsriMap from "@arcgis/core/Map.js";
import MapView from "@arcgis/core/views/MapView.js";
import Graphic from "@arcgis/core/Graphic.js";
import GraphicsLayer from "@arcgis/core/layers/GraphicsLayer.js";
import MediaLayer from "@arcgis/core/layers/MediaLayer.js";
import ImageElement from "@arcgis/core/layers/support/ImageElement.js";
import ExtentAndRotationGeoreference from "@arcgis/core/layers/support/ExtentAndRotationGeoreference.js";
import * as reactiveUtils from "@arcgis/core/core/reactiveUtils.js";

import { mx, my, unLat, unLon, pointAt, WM, Z0, zoomFromScale, scaleFromZoom, MIN_ZOOM, MAX_ZOOM } from "./geo.js";
import { lineSym, dotSym, startSyms, arrowSym, radius, rsize, dotScale, startRadius } from "./symbols.js";
import { makePopupWriters } from "./popupHtml.js";

// The SDK needs some of its own files (icons, workers, translations). Fetch them from Esri's servers, at the same version.
// To serve them yourself instead, copy node_modules/@arcgis/core/assets into public/ and set this to "./assets".
esriConfig.assetsPath = "https://js.arcgis.com/5.1/@arcgis/core/assets";

const MAX_ARROWS = 6000;       // most turn arrows drawn at once (lower this if close zooms feel slow)

export class WaldenMap {
  constructor(container, D, { onHover }) {
    this.D = D;
    this.onHover = onHover;
    this.popups = makePopupWriters(D);
    this.s = null;                                  // the latest control state (see App.jsx); set by apply()

    // ---- the view: no Esri basemap, a paper-colored background, our own controls ----
    this.view = new MapView({
      container, map: new EsriMap(),
      center: [D.start[1], D.start[0]], zoom: 12,
      background: { color: "#efe2c1" },
      constraints: { minScale: scaleFromZoom(MIN_ZOOM), maxScale: scaleFromZoom(MAX_ZOOM), snapToZoom: false, rotationEnabled: false },
      ui: { components: [] },                       // we draw our own zoom buttons, scale line and credits
      popupEnabled: false                           // we draw our own popups
    });

    this.buildBasemap();
    this.buildLenses();
    this.turnLayer = new GraphicsLayer({ title: "Turn arrows" });
    this.view.map.add(this.turnLayer);

    // The view is "ready" once it has layers to draw. App.jsx waits for this before showing the map.
    this.ready = this.view.when();
    this.startWatching();
    this.startHover();
  }

  get zoom() { return zoomFromScale(this.view.scale); }
  isOverlay() { return this.s.mode === "overlay"; }
  isActive(b) { return this.isOverlay() ? this.s.on[b.lens.id] : this.s.lens === b.lens.id; }

  // ---- the 1906 picture, placed by its corner coordinates ----
  buildBasemap() {
    const { D } = this;
    this.baseLayer = null;
    if (!D.basemap) return;
    const [[s, w], [n, e]] = D.basemap.bounds;
    const element = new ImageElement({
      image: D.basemap.url,
      georeference: new ExtentAndRotationGeoreference({ extent: { xmin: mx(w), ymin: my(s), xmax: mx(e), ymax: my(n), spatialReference: WM } })
    });
    this.baseLayer = new MediaLayer({
      source: [element], title: "1906 map of Concord", visible: false, opacity: 0.15,
      effect: "sepia(30%) saturate(90%) contrast(95%)"      // the aged look
    });
    this.view.map.add(this.baseLayer);
  }

  // ---- every lens: one layer of paths, one of points, one of chapter starts; every shape made once ----
  buildLenses() {
    const { D, view } = this;
    this.built = D.lenses.filter(l => l.built).map(lens => {
      const b = {
        lens,
        bounds: { xmin: mx(D.start[1]), ymin: my(D.start[0]), xmax: mx(D.start[1]), ymax: my(D.start[0]) },   // grows as we add paths
        lineLayer: new GraphicsLayer({ title: lens.name + " paths", visible: false, blendMode: "multiply" }),   // multiply: overlapping lines darken
        dotLayer: new GraphicsLayer({ title: lens.name + " points", visible: false }),
        startLayer: new GraphicsLayer({ title: lens.name + " chapter starts", visible: false }),
        dotItems: [], chapters: [], turnChapter: null
      };
      lens.chapters.forEach((c, i) => {
        const xy = c.path.map(p => [mx(p[1]), my(p[0])]);
        xy.forEach(([x, y]) => {
          if (x < b.bounds.xmin) b.bounds.xmin = x; if (x > b.bounds.xmax) b.bounds.xmax = x;
          if (y < b.bounds.ymin) b.bounds.ymin = y; if (y > b.bounds.ymax) b.bounds.ymax = y;
        });
        const line = new Graphic({ geometry: { type: "polyline", paths: [xy], spatialReference: WM }, symbol: lineSym(c.color), attributes: { kind: "line" } });
        b.lineLayer.add(line);
        const sp = pointAt(c.path[0][0], c.path[0][1]);
        const startG = [0, 1].map(k => new Graphic({ geometry: sp, symbol: startSyms(16)[k], attributes: { kind: "start", lens: lens.id, ch: i } }));
        b.startLayer.addMany(startG);
        b.chapters.push({ line, startG, dotItems: [] });
      });
      lens.dots.forEach((d, di) => {
        const [lat, lon, size, ch, , , , , kind] = d;
        const item = { kind, size, ch, d, base: radius(rsize(kind, size)) };
        item.g = new Graphic({ geometry: pointAt(lat, lon), symbol: dotSym(lens, kind, item.base, false), attributes: { kind: "dot", lens: lens.id, di } });
        b.dotItems.push(item);
        b.chapters[ch].dotItems.push(item);
        b.dotLayer.add(item.g);
      });
      view.map.addMany([b.lineLayer, b.dotLayer, b.startLayer]);
      return b;
    });
  }

  // ---- apply the controls to the map: show the right lens, chapters and points ----
  // Called whenever the controls change (see App.jsx). Cheap enough to call often: no shapes are created, only switched.
  apply(s) {
    this.s = s;
    const overlay = this.isOverlay();
    this.built.forEach(b => {
      const act = this.isActive(b);
      b.lineLayer.visible = act; b.dotLayer.visible = act && s.dots; b.startLayer.visible = act;
      b.chapters.forEach((c, i) => {
        const show = act && (overlay || s.chap[i]);
        c.line.symbol = lineSym(overlay ? b.lens.color : b.lens.chapters[i].color);    // overlay: one color per lens; else one per chapter
        c.line.visible = show;
        c.dotItems.forEach(it => { it.g.visible = show; });
        const startShown = show && (!overlay || s.starts);
        c.startG.forEach(g => { g.visible = startShown; });
      });
    });
    this.sizeAll();
    this.drawTurns();
  }

  // The 1906 picture: shown or hidden, and how strong. fade is 0 to 100.
  setBase(on, fade) {
    if (!this.baseLayer) return;
    this.baseLayer.visible = on;
    this.baseLayer.opacity = fade / 100;
  }

  // ---- size points and chapter-start diamonds to the zoom: they keep their size when zoomed out and grow with the ground when zoomed in ----
  sizeAll() {
    if (!this.s) return;
    const overlay = this.isOverlay(), zoom = this.zoom;
    const k = startRadius(zoom);
    const ss = startSyms(2 * k);
    this.built.forEach(b => {
      const grow = dotScale(zoom, b.lens.id === "word" ? 17 : 18);
      b.dotItems.forEach(it => { it.g.symbol = dotSym(b.lens, it.kind, Math.min(it.base * grow, 60), overlay); });
      b.chapters.forEach(c => { c.startG[0].symbol = ss[0]; c.startG[1].symbol = ss[1]; });
    });
  }

  // ---- close-up turn arrows: at every turn, an arrow along the new heading. Only drawn when zoomed in, and only on screen. ----
  drawTurns() {
    const { D, view, turnLayer, s } = this;
    turnLayer.removeAll();
    if (!s || !s.turns) return;
    const overlay = this.isOverlay();
    const ext = view.extent, px = ext.width * 0.1, py = ext.height * 0.1;      // a 10 percent margin so arrows do not pop in at the edge
    const x0 = ext.xmin - px, x1 = ext.xmax + px, y0 = ext.ymin - py, y1 = ext.ymax + py;
    const graphics = [];
    let shown = 0;
    this.built.forEach(b => {
      const lens = b.lens, T = lens.turns;
      // In the Overlay every lens uses the first lens's zoom threshold, so all arrows appear together.
      const threshold = overlay ? this.built[0].lens.turnZoom : lens.turnZoom;
      if (!T || !this.isActive(b) || this.zoom < threshold) return;
      if (!b.turnChapter) {            // work out each turn's chapter once
        b.turnChapter = new Array(T.off.length); let c = 0;
        T.off.forEach((o, i) => { while (c + 1 < D.chapterTitles.length && o >= D.chBounds[c + 1]) c++; b.turnChapter[i] = c; });
      }
      const color = overlay ? lens.color : "#2a1d10";
      for (let i = 0; i < T.off.length && shown < MAX_ARROWS; i++) {
        const x = mx(D.start[1] + T.lon[i] / 1e6), y = my(D.start[0] + T.lat[i] / 1e6), ch = b.turnChapter[i];
        if (x < x0 || x > x1 || y < y0 || y > y1 || (!overlay && !s.chap[ch])) continue;
        graphics.push(new Graphic({
          geometry: { type: "point", x, y, spatialReference: WM },
          symbol: arrowSym(T.code[i] & 7, color),          // the low 3 bits of "code" are the heading (0 to 7, times 45 degrees)
          attributes: { kind: "turn", lens: lens.id, i, ch }
        }));
        shown++;
      }
    });
    turnLayer.addMany(graphics);
  }

  // ---- redraw what depends on zoom and position whenever the view comes to rest ----
  startWatching() {
    const { view } = this;
    this.handles = [
      reactiveUtils.watch(() => view.stationary, still => {
        if (!still) this.onHover(null);                     // hide the popup while panning or zooming
        else { this.sizeAll(); this.drawTurns(); }
      })
    ];
  }

  // ---- hover: one pointer-move handler for every interactive graphic ----
  startHover() {
    const { view } = this;
    let busy = false;
    const handle = view.on("pointer-move", ev => {
      if (busy || !this.s) return;
      busy = true;
      const where = { x: ev.x, y: ev.y };
      requestAnimationFrame(async () => {        // at most one hit-test per screen frame
        busy = false;
        let hit = null;
        try {
          const layers = [this.turnLayer, ...this.built.flatMap(b => [b.startLayer, b.dotLayer])];
          const r = await view.hitTest(where, { include: layers });
          hit = r.results.find(x => x.type === "graphic" && x.graphic.attributes && x.graphic.attributes.kind);
        } catch (err) { /* the view may be closing; ignore */ }
        if (!hit) { this.onHover(null); view.container.style.cursor = ""; return; }
        view.container.style.cursor = "pointer";
        this.describe(hit.graphic);
      });
    });
    const hide = view.on(["pointer-down", "mouse-wheel", "drag"], () => this.onHover(null));
    this.handles.push(handle, hide);
  }

  // Work out the popup text for a hovered graphic and hand it to React.
  describe(g) {
    const a = g.attributes, overlay = this.isOverlay(), at = this.view.toScreen(g.geometry);
    const b = this.built.find(x => x.lens.id === a.lens);
    if (a.kind === "start") {
      const side = startRadius(this.zoom) * Math.SQRT2;
      this.onHover({ html: this.popups.startHtml(b.lens, a.ch, overlay), x: at.x, y: at.y, rad: side * 0.71, w: 300 });
    } else if (a.kind === "dot") {
      const it = b.dotItems[a.di];
      this.onHover({ html: this.popups.dotHtml(b.lens, it, overlay), x: at.x, y: at.y, rad: it.g.symbol.size / 0.75 / 2, w: it.kind === "s" ? 400 : 290 });
    } else if (a.kind === "turn") {
      this.onHover({ html: this.popups.turnHtml(b.lens, a.i, a.ch, overlay), x: at.x, y: at.y, rad: 10, w: b.lens.id === "sentence" ? 400 : 260 });
    }
  }

  // ---- fit the view to the active lenses, leaving room for the legend (right) and the color ramp (bottom) ----
  fit(s, animate) {
    this.s = s;
    let box = null;
    this.built.forEach(b => {
      if (!this.isActive(b)) return;
      const e = b.bounds;
      box = box ? { xmin: Math.min(box.xmin, e.xmin), ymin: Math.min(box.ymin, e.ymin), xmax: Math.max(box.xmax, e.xmax), ymax: Math.max(box.ymax, e.ymax) } : { ...e };
    });
    if (!box) return Promise.resolve();
    const wide = window.innerWidth > 700;
    const padL = 30, padT = 80, padR = wide ? 460 : 30, padB = 140;       // pixels kept free on each side
    const { width, height } = this.view;
    const aw = Math.max(50, width - padL - padR), ah = Math.max(50, height - padT - padB);
    const mpp = Math.max((box.xmax - box.xmin) / aw, (box.ymax - box.ymin) / ah);      // map units per pixel that makes the paths just fit
    const cx = (box.xmin + box.xmax) / 2, cy = (box.ymin + box.ymax) / 2;
    const sx = (padL - padR) / 2, sy = (padT - padB) / 2;                              // how far the free area's center is from the view's center
    const zoom = Math.log2(Z0 / (mpp * 96 / 0.0254));
    const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.floor(zoom * 4) / 4));      // round down to a quarter of a zoom level
    const mppSnap = (Z0 / Math.pow(2, z)) * 0.0254 / 96;
    const goal = { center: [unLon(cx - sx * mppSnap), unLat(cy + sy * mppSnap)], scale: scaleFromZoom(z) };    // center is [longitude, latitude]
    return this.view.goTo(goal, { animate: !!animate, duration: 600 }).catch(() => {});
  }

  // The + and - buttons: one whole zoom level in or out.
  zoomBy(step) {
    const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round(this.zoom) + step));
    this.view.goTo({ scale: scaleFromZoom(z) }, { duration: 250 });
  }

  destroy() {
    this.handles.forEach(h => h.remove());
    this.view.destroy();
  }
}
