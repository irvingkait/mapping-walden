# Walden map: the React app

Run `npm install` once, then `npm run dev`. See ../START_HERE.txt.

## Where things are

```
index.html            the one page; React fills <div id="root">
vite.config.js        settings for the build tool
public/data/          walden.json, basemap.jpg, walden.pdf   (written by ../build_data.py; do not edit)
public/fonts/         the Cardo font files                    (copied by ../build_data.py)
src/main.jsx          starts the app
src/App.jsx           loads walden.json
src/Walden.jsx        the map screen: the state, and how the pieces connect
src/styles.css        the whole look
src/components/       one file per piece of the screen
    ModeBar.jsx         One lens / Overlay, and the lens buttons
    ZoomBar.jsx         + and -
    Legend.jsx          the panel at top right
    Plates.jsx          north arrow, plate caption, color ramp
    Footer.jsx          scale line, credits, "Powered by Esri"
    Markers.jsx         Incipit and Finis
    Popup.jsx           the hover popup
src/map/              everything that talks to ArcGIS (no React in here)
    WaldenMap.js        builds the map, shows and hides lenses, hover, arrows, fit
    symbols.js          how lines, points and arrows look
    popupHtml.js        the words in the popups
    geo.js              latitude/longitude maths and small helpers
```
