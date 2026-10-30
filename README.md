# Walden Map

Walden Map is an interactive digital exploration of Henry David Thoreau’s Walden, combining literary analysis, geographic context, and web-based visualization. The project turns key themes, locations, and textual references into a navigable map experience designed for exploration, learning, and public engagement.

Live demo:
https://irvingkait.github.io/mapping-walden/

## Overview

Walden Map transforms Thoreau’s text into a navigable spatial experience. The app presents:

- multiple visual lenses for reading the text and their associated rules
- a public-facing web app designed for exploration and teaching

The project blends literary analysis, geospatial visualization, and web development into a single static site.

## Features

- Interactive map with layered views
- Multiple literacy lens mappings with individual and overlay views
- Hover popups with contextual information

## Tech Stack

- React
- Vite
- ArcGIS JavaScript API
- Python for data generation and preprocessing
- Static web assets for map data, fonts, and related media


## Local Development

To run the project locally:

```bash
cd app
npm install
npm run dev
```

Then open the local URL displayed by Vite in your browser.


## GitHub Pages Deployment

This repository is structured to work well with GitHub Pages:

- the app is built as a static site
- the frontend uses relative paths
- the generated build output is suitable for deployment to a static host

Recommended workflow:
1. Push the repository to GitHub
2. Go to the repository Settings
3. Open Pages
4. Set the source to GitHub Actions
5. Build the app in `app/` and publish the `app/dist` output

## Data and Research Pipeline

The repository includes Python-based preprocessing and analysis scripts used to shape the map data and textual overlays. These tools support:

- text processing
- lens generation
- map-related preprocessing
- asset generation for the front-end app

The front-end app consumes the generated data from `app/public/data`.


## License

This project is provided for educational and research use. Please check the repository for any licensing details before reusing or adapting the code or content.


## Disclaimer

This project was created with the assistance of AI tools.
