"""Static 1080x1080 PNG card for text posts: optional eyebrow, a title, 1-3 short lines, brand footer.
Generic on purpose, so any content source can queue one.

data: {"key": "<unique per card>", "title": "...", "lines": ["...", "..."],
       "eyebrow": "TRUCKING TIP" (optional), "footer": "Free lane rates & carrier lookup" (optional)}
The text is drawn exactly as given; the renderer adds nothing but the brand.
"""
from PIL import Image, ImageDraw

from .brand import AMBER, GREY, NAVY, NAVY2, SITE, TAGLINE, WHITE, font, require, wrap

EXT = "png"
S = 1080
PAD = 90


def validate(x: dict) -> None:
    require(isinstance(x.get("title"), str) and 0 < len(x["title"].strip()) <= 120, "title: 1-120 chars")
    lines = x.get("lines")
    require(isinstance(lines, list) and 1 <= len(lines) <= 3, "lines: 1 to 3 strings")
    for ln in lines:
        require(isinstance(ln, str) and 0 < len(ln.strip()) <= 160, "each line: 1-160 chars")
    for k in ("eyebrow", "footer"):
        if x.get(k) is not None:
            require(isinstance(x[k], str) and len(x[k]) <= 60, f"{k}: up to 60 chars")


def layout(d, x: dict, scale: float):
    """Wrapped title and body at a given scale; returns (title lines, title font, body, body font, height)."""
    tf = font("Black", int(78 * scale))
    bf = font("Bold", int(44 * scale))
    title = wrap(d, x["title"], tf, S - 2 * PAD)
    body = [wrap(d, ln, bf, S - 2 * PAD) for ln in x["lines"]]
    h = len(title) * int(92 * scale) + 40 + sum(len(b) * int(58 * scale) + 22 for b in body)
    return title, tf, body, bf, h


def render(x: dict, out: str) -> None:
    validate(x)
    im = Image.new("RGB", (S, S), NAVY)
    d = ImageDraw.Draw(im)
    for i in range(0, 2 * S, 90):
        d.line([(i, 0), (i - S, S)], fill=NAVY2, width=28)
    d.rectangle([40, 40, S - 40, S - 40], fill=NAVY)
    d.rectangle([40, 40, S - 40, 52], fill=AMBER)

    top = 130
    if x.get("eyebrow"):
        d.text((PAD, top), x["eyebrow"].upper(), font=font("Black", 38), fill=AMBER)
        top += 80
    avail = S - 230 - top
    scale = 1.0
    title, tf, body, bf, h = layout(d, x, scale)
    while h > avail and scale > 0.55:
        scale -= 0.05
        title, tf, body, bf, h = layout(d, x, scale)
    require(h <= avail, "text too long for a card")

    y = top + (avail - h) / 2
    for ln in title:
        d.text((PAD, y), ln, font=tf, fill=WHITE)
        y += int(92 * scale)
    y += 40
    for block in body:
        for ln in block:
            d.text((PAD, y), ln, font=bf, fill=GREY)
            y += int(58 * scale)
        y += 22

    d.rectangle([PAD, S - 200, PAD + 160, S - 192], fill=AMBER)
    d.text((PAD, S - 170), x.get("footer") or TAGLINE, font=font("Bold", 36), fill=GREY)
    d.text((PAD, S - 120), SITE, font=font("Black", 48), fill=WHITE)
    im.save(out, "PNG", optimize=True)
