Resource files for TOM Desktop

Place Tom image assets here so the UI and launcher can find them regardless of working directory.

Recommended files (any of these):
- tom_icon.png      -> used for UI logo and icon generation
- tom with bng.png
- tom without bng.png

To create a Windows .ico from a PNG, run:

  pip install pillow
  python tools/make_icon.py resources/tom_icon.png

That will write `resources/tom_icon.ico` which you can set as the desktop shortcut icon.
