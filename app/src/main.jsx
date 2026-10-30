// main.jsx: where the app starts. It does three small things:
//   1. loads the ArcGIS SDK's own style sheet (needed by its widgets),
//   2. loads our style sheet (the paper look),
//   3. puts the <App /> component into the empty <div id="root"> in index.html.
import { createRoot } from "react-dom/client";
import "@arcgis/core/assets/esri/themes/light/main.css";
import "./styles.css";
import App from "./App.jsx";

// Note: React's <StrictMode> is left out on purpose. In development it creates every component twice to
// catch mistakes, and creating the ArcGIS map twice is slow and noisy.
createRoot(document.getElementById("root")).render(<App />);
