#!/usr/bin/env python3
"""Crop a source image before it goes into a card, to cut off source watermarks/logos.

Usage: python3 prep_image.py in.jpg out.jpg [--top F] [--bottom F] [--left F] [--right F]
Each value is the fraction of the image to cut from that side (e.g. --bottom 0.13).

Known watermarks:
  - gsmarena.com: grey "GSMArena" band along the bottom -> --bottom 0.13
Always look at the result: if a logo, @handle, URL or channel name of the source is still visible, crop more or pick another image.
"""
import argparse
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
for side in ("top", "bottom", "left", "right"):
    ap.add_argument(f"--{side}", type=float, default=0.0)
a = ap.parse_args()

im = Image.open(a.src).convert("RGB")
w, h = im.size
box = (round(w * a.left), round(h * a.top), round(w * (1 - a.right)), round(h * (1 - a.bottom)))
im.crop(box).save(a.dst, quality=92)
print(f"{a.src} {w}x{h} -> {a.dst} {box[2]-box[0]}x{box[3]-box[1]}")
