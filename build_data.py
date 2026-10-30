"""
=====================================================================================================
 build_data.py  --  RUN THIS FILE to build the map's data (step 1 of 2; step 2 is the React app in app/).
=====================================================================================================
 In a terminal, from this folder:

     python3 build_data.py

 It writes the files the React app reads into  app/public/data/  (walden.json, basemap.jpg, walden.pdf) and copies the
 Cardo fonts into  app/public/fonts/ . Then start the app (see START_HERE.txt): cd app, npm install, npm run dev.

 What this file does: it collects all the settings below and passes them to python/make_lenses.py, which does
 the real work. Think of this file as the control panel and make_lenses.py as the machine.

 To change a setting, edit the value after the = sign, save the file, and run it again. Keep the quote marks
 around text values, and keep the commas where they are in the lists.
"""
import os
import shutil
import subprocess
import sys

# The folder this file is in. All the paths below are relative to it, so you can move the whole folder anywhere.
HERE = os.path.dirname(os.path.abspath(__file__))
def path(*parts):
    return os.path.join(HERE, *parts)

# ----------------------------------------------------------------------------------------------------
# SETTINGS YOU MAY WANT TO CHANGE
# ----------------------------------------------------------------------------------------------------

# The text to walk, and its chapter list. Both live in data/. For another book, point these at your own files
# (see the guide: "Using another text"). Keep each text in its own folder, because the word and sentence
# results are saved next to the text and reused.
TEXT_FILE = path("data", "clean.txt")
CHAPTERS_FILE = path("data", "chapters.json")

# Where the turtle begins: latitude and longitude, in degrees. This is the site of Thoreau's hut at Walden Pond.
START_LAT = 42.44348
START_LON = -71.34053
START_NAME = "Site of Thoreau's hut, Walden Pond, Concord, Massachusetts"   # shown when you hover the Incipit marker

# The numeric code of the metric map grid used to measure meters. 26986 = Massachusetts Mainland.
# For another place, look up its grid at epsg.io (a UTM zone is a good general choice).
EPSG = 26986

# The text on the page. TITLE is the start of the legend heading: "Walden: " + the lens name.
TITLE = "Walden: "
SOURCE_LABEL = "Source text: Walden, or Life in the Woods (PDF)"
SOURCE_PDF = path("data", "walden.pdf")      # set to None to leave the PDF out (the file gets 1.4 MB smaller)

# The 1906 basemap picture and the latitude/longitude of its four edges: South, West, North, East.
# Set USE_BASEMAP = False to build the map without it.
USE_BASEMAP = True
BASEMAP_FILE = path("data", "concord.jpg")
BASEMAP_BOUNDS = (42.401046, -71.437767, 42.516697, -71.279724)
BASEMAP_CREDIT = ("Herbert Wendell Gleason, [Map of Concord, Mass. Showing Localities mentioned by Thoreau in his Journals] (1906). "
                  "Lincoln Town Archives, Lincoln Maps Collection.")
BASEMAP_CREDIT_URL = "https://lincolntownarchives.omeka.net/items/show/62"

# Building a map of a DIFFERENT book? The four overlay colors each carry a quote about autumn from Walden.
# Another book will not contain them, so switch the check off. (You can then edit the quotes in python/make_lenses.py.)
SKIP_QUOTE_CHECK = False

# Where the data files go. The React app serves everything in app/public/ as it stands.
OUTPUT_DIR = path("app", "public", "data")
FONTS_DIR = path("app", "public", "fonts")

# ----------------------------------------------------------------------------------------------------
# THE REST: you do not need to change anything below this line
# ----------------------------------------------------------------------------------------------------

def main():
    # The command we will run, as a list of words: python python/make_lenses.py <text> <chapters> <output> --option value ...
    cmd = [sys.executable, "-I", path("python", "make_lenses.py"),
           TEXT_FILE, CHAPTERS_FILE, OUTPUT_DIR,
           "--title", TITLE,
           "--start", str(START_LAT), str(START_LON),
           "--start-name", START_NAME,
           "--epsg", str(EPSG),
           "--source-label", SOURCE_LABEL]
    if SOURCE_PDF:
        cmd += ["--source-pdf", SOURCE_PDF]
    if USE_BASEMAP:
        cmd += ["--basemap", BASEMAP_FILE,
                "--basemap-bounds", *[str(v) for v in BASEMAP_BOUNDS],
                "--basemap-credit", BASEMAP_CREDIT,
                "--basemap-credit-url", BASEMAP_CREDIT_URL]
    if SKIP_QUOTE_CHECK:
        cmd.append("--skip-quote-check")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FONTS_DIR, exist_ok=True)
    print("Building the map. The first build of a NEW text takes a few minutes; this one should take under a minute.")
    result = subprocess.run(cmd)       # run make_lenses.py and show its messages here
    if result.returncode != 0:
        sys.exit("The build stopped with an error. Read the last lines above; the guide has a troubleshooting section.")
    for name in os.listdir(path("vendor", "fonts")):          # the Cardo fonts the app's style sheet points at
        shutil.copyfile(path("vendor", "fonts", name), os.path.join(FONTS_DIR, name))
    print("\nDone. The data is in:\n  " + OUTPUT_DIR + "\nNow start the app: cd app, npm install (first time only), npm run dev.")


if __name__ == "__main__":
    main()
