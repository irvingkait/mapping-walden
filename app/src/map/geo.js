// geo.js: the small bits of map maths every other file shares.
//
// The ArcGIS SDK draws in "web mercator" meters (the projection used by most web maps). The data from Python is
// in latitude and longitude, so these functions convert one to the other.

export const RE = 6378137;                 // the earth's radius (meters) that web mercator assumes
export const D2R = Math.PI / 180;          // degrees to radians
export const WM = { wkid: 102100 };        // the name ArcGIS uses for web mercator ("spatial reference")

export const mx = lon => RE * lon * D2R;                                              // longitude -> web mercator x
export const my = lat => RE * Math.log(Math.tan(Math.PI / 4 + lat * D2R / 2));        // latitude  -> web mercator y
export const unLon = x => x / RE / D2R;                                               // x -> longitude
export const unLat = y => (2 * Math.atan(Math.exp(y / RE)) - Math.PI / 2) / D2R;      // y -> latitude

// A point in the form ArcGIS wants.
export const pointAt = (lat, lon) => ({ type: "point", x: mx(lon), y: my(lat), spatialReference: WM });

// Zoom. With no tiled basemap the view has no zoom "levels" of its own, so we work out the usual web-map zoom
// number (9 = whole town, 22 = a few meters) from the view's scale. Z0 is the scale at zoom level 0.
export const Z0 = 591657527.591555;
export const zoomFromScale = scale => Math.log2(Z0 / scale);
export const scaleFromZoom = zoom => Z0 / Math.pow(2, zoom);
export const MIN_ZOOM = 9, MAX_ZOOM = 22;

// ArcGIS sizes symbols in points; the design is in pixels. 1 pixel = 0.75 point.
export const PT = 0.75;

// "#rrggbb" -> [r, g, b, alpha], the color form ArcGIS wants. Alpha is 0 to 1, except for solid colors given as 255.
export const hexA = (hex, a) => [parseInt(hex.substr(1, 2), 16), parseInt(hex.substr(3, 2), 16), parseInt(hex.substr(5, 2), 16), a];

// "#rrggbb" -> "rgba(r,g,b,a)", the color form CSS wants.
export const rgba = (hex, a) => "rgba(" + [1, 3, 5].map(i => parseInt(hex.substr(i, 2), 16)).join(",") + "," + a + ")";

// Make text safe to put inside HTML (the book's text contains < and & characters).
export const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
