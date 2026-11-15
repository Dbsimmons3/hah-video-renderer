"""Diesel trend Short, 1080x1920, 16 s: the U.S. average price over the last (up to) 12 EIA weeks,
drawn as an animated line, then the latest price and the change across the window.

data (the site builds it from diesel_price_history, region US, when a Freight Pulse week publishes):
  {"key": "2026-11-02", "region": "US", "as_of": "2026-11-09",
   "points": [{"period": "2026-08-24", "price": 5.652}, ..., {"period": "2026-11-09", "price": 6.127}]}
Points are oldest first. Every number on screen is one of these or a difference of two of them.
"""
import datetime as dt

from PIL import ImageDraw

from .brand import (AMBER, FPS, GREY, MUTED, NAVY, NAVY2, WHITE, center, encode_video, font, money,
                    number, require, signed_money, stills, vertical_base)

EXT = "mp4"
HEADER = "DIESEL WATCH"
X0, X1, Y0, Y1 = 150, 990, 560, 1280


def label(period: str) -> str:
    d = dt.date.fromisoformat(period)
    return f"{d:%b} {d.day}"


def validate(x: dict) -> None:
    pts = x.get("points")
    require(isinstance(pts, list) and 2 <= len(pts) <= 12, "points: 2 to 12 weekly prices")
    prev = ""
    for p in pts:
        require(isinstance(p, dict) and isinstance(p.get("period"), str), "points[].period required")
        dt.date.fromisoformat(p["period"])
        require(p["period"] > prev, "points must be oldest first, one per period")
        prev = p["period"]
        number(p.get("price"), "points[].price")


def chart_geometry(pts):
    prices = [p["price"] for p in pts]
    lo, hi = min(prices), max(prices)
    pad = max((hi - lo) * 0.15, 0.05)
    lo, hi = lo - pad, hi + pad
    n = len(pts)
    xy = [(X0 + (X1 - X0) * i / (n - 1), Y1 - (Y1 - Y0) * (p - lo) / (hi - lo)) for i, p in enumerate(prices)]
    return xy, lo, hi


def chart_base(x: dict):
    pts = x["points"]
    im, d = vertical_base(HEADER, f"U.S. average diesel, last {len(pts)} weeks")
    xy, lo, hi = chart_geometry(pts)
    d.rectangle([X0 - 20, Y0 - 40, X1 + 20, Y1 + 30], fill=NAVY)
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = Y1 - (Y1 - Y0) * k / 4
        d.line([(X0, y), (X1, y)], fill=NAVY2, width=2)
        d.text((X0 - 130, y - 18), f"${v:.2f}", font=font("Regular", 32), fill=MUTED)
    for i in sorted({0, len(pts) // 2, len(pts) - 1}):
        t = label(pts[i]["period"])
        w = d.textlength(t, font=font("Regular", 34))
        d.text((min(max(xy[i][0] - w / 2, X0 - 40), X1 + 20 - w), Y1 + 50), t, font=font("Regular", 34), fill=MUTED)
    center(d, 1440, "Dollars per gallon, weekly. Source: U.S. EIA", font("Regular", 36), MUTED)
    return im, xy


def chart_frames(x: dict, draw_secs: float = 5.0, hold_secs: float = 2.0):
    pts = x["points"]
    base, xy = chart_base(x)
    n_draw, n_hold = round(draw_secs * FPS), round(hold_secs * FPS)
    for f in range(n_draw + n_hold):
        t = min(1.0, (f + 1) / n_draw)
        pos = t * (len(xy) - 1)
        i = int(pos)
        frac = pos - i
        line = xy[: i + 1]
        if i < len(xy) - 1:
            a, b = xy[i], xy[i + 1]
            line = line + [(a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac)]
        im = base.copy()
        d = ImageDraw.Draw(im)
        if len(line) > 1:
            d.line(line, fill=AMBER, width=10, joint="curve")
        for px, py in xy[: i + 1]:
            d.ellipse([px - 8, py - 8, px + 8, py + 8], fill=WHITE)
        hx, hy = line[-1]
        d.ellipse([hx - 16, hy - 16, hx + 16, hy + 16], fill=AMBER, outline=WHITE, width=4)
        price = pts[min(round(pos), len(pts) - 1)]["price"]
        tag = money(price)
        tw = d.textlength(tag, font=font("Black", 56))
        tx = min(max(hx - tw / 2, 40), 1040 - tw)
        ty = hy - 100 if hy - 100 > Y0 - 60 else hy + 40
        d.text((tx, ty), tag, font=font("Black", 56), fill=WHITE)
        yield im


def summary(x: dict):
    pts = x["points"]
    first, last = pts[0], pts[-1]
    lo = min(pts, key=lambda p: p["price"])
    hi = max(pts, key=lambda p: p["price"])
    im, d = vertical_base(HEADER, f"Diesel as of {label(last['period'])}")
    center(d, 620, money(last["price"]), font("Black", 210), WHITE)
    center(d, 870, "per gallon, U.S. average", font("Bold", 58), GREY)
    change = round(last["price"] - first["price"], 3)
    center(d, 1000, f"{signed_money(change)} since {label(first['period'])}", font("Bold", 64), AMBER)
    center(d, 1140, f"Low {money(lo['price'])} ({label(lo['period'])})", font("Bold", 52), WHITE)
    center(d, 1220, f"High {money(hi['price'])} ({label(hi['period'])})", font("Bold", 52), WHITE)
    return im


def intro(x: dict):
    im, d = vertical_base(HEADER, "")
    center(d, 720, "Diesel prices,", font("Bold", 80), WHITE)
    center(d, 830, f"the last {len(x['points'])} weeks", font("Black", 100), WHITE)
    center(d, 1000, "U.S. average, per gallon", font("Bold", 56), AMBER)
    return im


def outro():
    im, d = vertical_base(HEADER, "")
    for i, ln in enumerate(["Quoting a long run?", "Check your cost per mile", "with this week's diesel."]):
        center(d, 760 + i * 100, ln, font("Black" if i == 0 else "Bold", 72 if i == 0 else 62),
               AMBER if i == 0 else WHITE)
    return im


def frames(x: dict):
    yield from stills([(intro(x), 2.5)])
    yield from chart_frames(x)
    yield from stills([(summary(x), 4.0), (outro(), 2.5)])


def render(x: dict, out: str) -> None:
    validate(x)
    encode_video(frames(x), out)
