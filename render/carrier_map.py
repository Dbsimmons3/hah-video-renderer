"""Monthly new-carrier map Short, 1080x1920, 16 s: the month's new USDOT registrations, a U.S.
choropleth by state that fills in from fewest to most, then the top five states.

data (the site builds it from new_carrier_reports.payload when a monthly report publishes):
  {"key": "2026-10", "month_label": "October 2026", "total": 9123, "previous_total": 8840 | null,
   "previous_label": "September" | null,
   "states": [{"state": "TX", "name": "Texas", "count": 1180}, ...]}   (largest first)
State shapes: U.S. Census Bureau cartographic boundaries (render/assets/us_states.json), credited
on screen as the Census terms require.
"""
import json
import os
from functools import lru_cache

from PIL import Image, ImageDraw

from .brand import (AMBER, FPS, GREY, MUTED, NAVY, NAVY2, WHITE, center, encode_video, font, number,
                    require, stills, vertical_base)

EXT = "mp4"
HEADER = "NEW CARRIERS"
MAP_X, MAP_Y, MAP_SCALE = 40, 640, 1.0
EMPTY = (51, 65, 85)


@lru_cache(maxsize=1)
def shapes() -> dict:
    with open(os.path.join(os.path.dirname(__file__), "assets", "us_states.json")) as fh:
        return json.load(fh)


def validate(x: dict) -> None:
    require(isinstance(x.get("month_label"), str) and x["month_label"], "month_label required")
    number(x.get("total"), "total")
    if x.get("previous_total") is not None:
        number(x["previous_total"], "previous_total")
    states = x.get("states")
    require(isinstance(states, list) and len(states) >= 3, "states: at least 3 entries")
    for s in states:
        require(isinstance(s, dict) and isinstance(s.get("state"), str), "states[].state required")
        number(s.get("count"), "states[].count", positive=False)


def shade(t: float):
    """0..1 -> navy-slate to amber."""
    lo, hi = (71, 85, 105), AMBER
    return tuple(round(a + (b - a) * t) for a, b in zip(lo, hi))


def intro(x: dict):
    im, d = vertical_base(HEADER, x["month_label"])
    center(d, 640, f"{int(x['total']):,}", font("Black", 200), WHITE)
    center(d, 880, "new trucking companies", font("Bold", 62), WHITE)
    center(d, 960, "registered with FMCSA", font("Bold", 52), GREY)
    prev = x.get("previous_total")
    if prev:
        pct = (x["total"] - prev) / prev * 100
        vs = f"vs {x['previous_label']}" if x.get("previous_label") else "vs the month before"
        center(d, 1100, f"{'+' if pct >= 0 else '−'}{abs(pct):.1f}% {vs}", font("Bold", 60), AMBER)
    return im


def map_frames(x: dict, fill_secs: float = 3.5, hold_secs: float = 2.5):
    geo = shapes()
    counts = {s["state"]: int(s["count"]) for s in x["states"] if s["state"] in geo["states"]}
    ranked = sorted(counts, key=lambda c: counts[c])
    top = max(counts.values()) or 1

    base, d = vertical_base(HEADER, "Where they registered")
    pt = lambda p: (MAP_X + p[0] * MAP_SCALE, MAP_Y + p[1] * MAP_SCALE)
    for code, rings in geo["states"].items():
        for ring in rings:
            d.polygon([pt(p) for p in ring], fill=EMPTY, outline=NAVY)
    # Legend: a gradient bar labelled with the real lowest and highest state counts.
    lx0, lx1, ly = 240, 840, 1400
    for i in range(lx1 - lx0):
        d.line([(lx0 + i, ly), (lx0 + i, ly + 26)], fill=shade(i / (lx1 - lx0)))
    lo_n = min(counts.values())
    d.text((lx0, ly + 40), f"{lo_n:,}", font=font("Regular", 34), fill=MUTED)
    hi_t = f"{top:,}"
    d.text((lx1 - d.textlength(hi_t, font=font("Regular", 34)), ly + 40), hi_t, font=font("Regular", 34), fill=MUTED)
    center(d, ly - 60, "New registrations by state", font("Bold", 40), GREY)
    center(d, 1560, "Data: FMCSA. Map: U.S. Census Bureau", font("Regular", 32), MUTED)

    n_fill, n_hold = round(fill_secs * FPS), round(hold_secs * FPS)
    for f in range(n_fill + n_hold):
        shown = ranked[: round(len(ranked) * min(1.0, (f + 1) / n_fill))]
        im = base.copy()
        d = ImageDraw.Draw(im)
        for code in shown:
            for ring in geo["states"][code]:
                d.polygon([pt(p) for p in ring], fill=shade(counts[code] / top), outline=NAVY)
        if f >= n_fill:
            leader = max(counts, key=lambda c: counts[c])
            name = next((s.get("name") for s in x["states"] if s["state"] == leader), None) or leader
            center(d, 560, f"Most: {name}, {counts[leader]:,}", font("Black", 56), AMBER)
        yield im


def top_five(x: dict):
    im, d = vertical_base(HEADER, f"Top states, {x['month_label']}")
    y = 560
    rows = sorted(x["states"], key=lambda s: -s["count"])[:5]
    for i, s in enumerate(rows, 1):
        name = s.get("name") or s["state"]
        f = font("Black" if i == 1 else "Bold", 70 if i == 1 else 62)
        color = AMBER if i == 1 else WHITE
        d.text((140, y), f"{i}. {name}", font=f, fill=color)
        n = f"{int(s['count']):,}"
        d.text((940 - d.textlength(n, font=f), y), n, font=f, fill=color)
        y += 130
    return im


def outro():
    im, d = vertical_base(HEADER, "")
    for i, ln in enumerate(["New carrier on your load?", "Check authority & insurance", "before you tender."]):
        center(d, 760 + i * 100, ln, font("Black" if i == 0 else "Bold", 70 if i == 0 else 62),
               AMBER if i == 0 else WHITE)
    return im


def frames(x: dict):
    yield from stills([(intro(x), 3.0)])
    yield from map_frames(x)
    yield from stills([(top_five(x), 4.0), (outro(), 3.0)])


def render(x: dict, out: str) -> None:
    validate(x)
    encode_video(frames(x), out)
