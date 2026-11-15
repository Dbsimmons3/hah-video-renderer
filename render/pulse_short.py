"""Weekly Freight Pulse Short, 1080x1920, 14.5 s (ported from make_pulse_short.py).

data (the site builds it from freight_pulse_weekly via buildPulseCaptions().video):
  {"key": "2026-11-02", "week_label": "Week of Nov 2", "diesel": 6.127, "diesel_change": -0.165 | null,
   "diesel_as_of": "Nov 9", "new_carriers": 2605, "states": [["Texas", 327], ["California", 244], ...]}
"""
from .brand import (AMBER, GREY, WHITE, center, encode_video, font, money, number, require,
                    signed_money, stills, vertical_base)

EXT = "mp4"
HEADER = "FREIGHT PULSE"


def validate(x: dict) -> None:
    require(isinstance(x.get("week_label"), str) and x["week_label"], "week_label required")
    require(isinstance(x.get("diesel_as_of"), str) and x["diesel_as_of"], "diesel_as_of required")
    number(x.get("diesel"), "diesel")
    if x.get("diesel_change") is not None:
        number(x["diesel_change"], "diesel_change", positive=False)
    number(x.get("new_carriers"), "new_carriers")
    states = x.get("states")
    require(isinstance(states, list) and len(states) >= 1, "states must be a non-empty list")
    for s in states[:3]:
        require(isinstance(s, list) and len(s) == 2 and isinstance(s[0], str), "states: [name, count]")
        number(s[1], "state count")


def scenes(x: dict):
    out = []
    im, d = vertical_base(HEADER, x["week_label"])
    center(d, 760, "This week in", font("Bold", 70), WHITE)
    center(d, 860, "U.S. trucking", font("Black", 110), WHITE)
    center(d, 1040, "in 15 seconds", font("Bold", 60), AMBER)
    out.append((im, 3.0))

    im, d = vertical_base(HEADER, "Diesel, U.S. average")
    center(d, 700, money(x["diesel"]), font("Black", 210), WHITE)
    center(d, 950, "per gallon", font("Bold", 64), GREY)
    if x.get("diesel_change") is not None:
        center(d, 1060, f"{signed_money(x['diesel_change'])} vs last week", font("Bold", 60), AMBER)
    center(d, 1180, f"as of {x['diesel_as_of']}", font("Regular", 44), GREY)
    out.append((im, 4.0))

    im, d = vertical_base(HEADER, "New trucking companies")
    center(d, 640, f"{int(x['new_carriers']):,}", font("Black", 200), WHITE)
    center(d, 880, "new USDOT registrations", font("Bold", 58), GREY)
    y = 1040
    for i, (st, n) in enumerate(x["states"][:3], 1):
        center(d, y, f"{i}. {st}  {int(n):,}", font("Bold", 64), AMBER if i == 1 else WHITE)
        y += 100
    out.append((im, 4.0))

    im, d = vertical_base(HEADER, "What it means")
    y = 700
    for ln in ["Carriers: check cost per mile", "before quoting long runs.", "",
               "Shippers: confirm authority", "& insurance before you tender."]:
        if ln:
            center(d, y, ln, font("Bold", 62), WHITE)
        y += 90
    out.append((im, 3.5))
    return out


def render(x: dict, out: str) -> None:
    validate(x)
    encode_video(stills(scenes(x)), out)
