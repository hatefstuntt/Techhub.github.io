"""Image edits so reposted photos look like the owner's channel and carry no source watermark.

- crop_top / crop_bottom (fractions) cut off a source's watermark band
- an optional logo (PNG with transparency) is placed in a corner
"""
from __future__ import annotations

from PIL import Image


def brand_image(src: str, dst: str, crop_top: float = 0.0, crop_bottom: float = 0.0,
                logo: str | None = None, logo_corner: str = "bottom-left",
                logo_width: float = 0.18, logo_opacity: float = 0.9) -> str:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    top, bottom = round(h * crop_top), round(h * (1 - crop_bottom))
    if bottom - top > h * 0.3:  # never crop away most of the picture
        im = im.crop((0, top, w, bottom))
    if logo:
        lg = Image.open(logo).convert("RGBA")
        lw = max(40, round(im.width * logo_width))
        lg = lg.resize((lw, round(lg.height * lw / lg.width)), Image.LANCZOS)
        if logo_opacity < 1:
            a = lg.getchannel("A").point(lambda v: round(v * logo_opacity))
            lg.putalpha(a)
        m = round(im.width * 0.03)
        x = m if "left" in logo_corner else im.width - lg.width - m
        y = m if "top" in logo_corner else im.height - lg.height - m
        base = im.convert("RGBA")
        base.alpha_composite(lg, (x, y))
        im = base.convert("RGB")
    im.save(dst, "JPEG", quality=92)
    return dst
