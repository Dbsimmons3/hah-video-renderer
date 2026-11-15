"""Shared Haul-Away Haulers look: colors, bundled Inter fonts, the vertical frame, and encoding.

Every renderer draws PIL images and hands them to `encode_video`, which pipes raw frames to ffmpeg
(H.264 + a silent AAC track, which some platforms require on a Short).
"""
import os
import subprocess
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

NAVY = (27, 36, 48)
NAVY2 = (36, 48, 64)
AMBER = (217, 119, 6)
WHITE = (250, 250, 250)
GREY = (209, 213, 219)
MUTED = (148, 163, 184)

VW, VH, FPS = 1080, 1920, 30
SITE = "haulawayhaulers.com"
TAGLINE = "Free lane rates & carrier lookup"

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")


@lru_cache(maxsize=None)
def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Inter-{weight}.ttf"), size)


def center(d: ImageDraw.ImageDraw, y: float, text: str, f, fill, width: int = VW) -> None:
    d.text(((width - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def fit(d: ImageDraw.ImageDraw, text: str, weight: str, size: int, max_w: int):
    """The largest font at or under `size` that fits `text` on one line in `max_w` pixels."""
    while size > 20 and d.textlength(text, font=font(weight, size)) > max_w:
        size -= 2
    return font(weight, size)


def wrap(d: ImageDraw.ImageDraw, text: str, f, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        nxt = f"{cur} {word}".strip()
        if cur and d.textlength(nxt, font=f) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines


def vertical_base(header: str, scene_title: str):
    """1080x1920 frame: striped navy, amber header, scene title, site footer with the benefit line."""
    im = Image.new("RGB", (VW, VH), NAVY)
    d = ImageDraw.Draw(im)
    for i in range(0, VW + VH, 90):
        d.line([(i, 0), (i - VH, VH)], fill=NAVY2, width=28)
    d.rectangle([0, 0, VW, 210], fill=NAVY)
    center(d, 70, header, font("Black", 72), AMBER)
    d.rectangle([390, 168, 690, 176], fill=AMBER)
    if scene_title:
        center(d, 250, scene_title, fit(d, scene_title, "Bold", 52, VW - 120), GREY)
    d.rectangle([0, VH - 230, VW, VH], fill=NAVY)
    center(d, VH - 190, TAGLINE, font("Bold", 46), GREY)
    center(d, VH - 120, SITE, font("Black", 64), WHITE)
    return im, d


def money(v: float) -> str:
    return f"${v:,.3f}"


def signed_money(v: float) -> str:
    return f"{'+' if v >= 0 else '−'}${abs(v):.3f}"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def number(v, name: str, positive: bool = True) -> float:
    require(isinstance(v, (int, float)) and not isinstance(v, bool), f"{name} must be a number")
    require(not positive or v > 0, f"{name} must be > 0")
    return float(v)


def stills(scenes, fade_frames: int = 9):
    """(image, seconds) scenes -> frames, each scene fading in from navy."""
    for im, secs in scenes:
        n = round(secs * FPS)
        bg = Image.new("RGB", im.size, NAVY)
        for i in range(n):
            yield Image.blend(bg, im, (i + 1) / fade_frames) if i < fade_frames - 1 else im


def encode_video(frames, out: str, size=(VW, VH)) -> None:
    w, h = size
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-map", "0:v", "-map", "1:a", "-shortest",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", out,
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for im in frames:
            p.stdin.write(im.tobytes())
    finally:
        p.stdin.close()
        err = p.stderr.read().decode(errors="replace")
        if p.wait() != 0:
            raise RuntimeError(f"ffmpeg failed: {err[-500:]}")
