"""Small helper: convert a PNG to a Windows .ico file for desktop shortcuts.

Usage:
  python tools/make_icon.py resources/tom_icon.png

This will write `resources/tom_icon.ico` (sizes 256x256, 128x128, 64x64, 48x48, 32x32, 16x16)
Requires Pillow: `pip install pillow`
"""
import sys
import os
from PIL import Image


def make_icon(src_png: str, out_ico: str):
    img = Image.open(src_png).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icons = []
    for s in sizes:
        icons.append(img.resize(s, Image.LANCZOS))
    # save as .ico
    icons[0].save(out_ico, format="ICO", sizes=[s for s in sizes])


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/make_icon.py path/to/source.png")
        return
    src = sys.argv[1]
    if not os.path.exists(src):
        print("Source PNG not found:", src)
        return
    out = os.path.join(os.path.dirname(src), "tom_icon.ico")
    try:
        make_icon(src, out)
        print("Wrote:", out)
    except Exception as exc:
        print("Failed to create icon:", exc)


if __name__ == "__main__":
    main()
