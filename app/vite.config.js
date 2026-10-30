// vite.config.js: settings for Vite, the tool that runs the app while you work on it (npm run dev)
// and packs it into plain files for a web host (npm run build).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],           // lets Vite understand JSX, the HTML-like syntax in the .jsx files
  base: "./",                   // use relative links, so the built folder works from any folder on a web host
  build: {
    chunkSizeWarningLimit: 6000 // the ArcGIS SDK is large; silence the "chunk is large" warning
  }
});
