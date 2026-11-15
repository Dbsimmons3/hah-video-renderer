#!/usr/bin/env python3
"""Rebuild render/assets/us_states.json from the U.S. Census Bureau cartographic boundary file.

Source: https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_20m.zip (1:20,000,000).
Census terms: free to use in a product or publication, with acknowledgement of the U.S. Census
Bureau as the source (the map scene credits it on screen).

Dev-only (needs `pip install pyshp`, not in requirements.txt; CI never runs this):
    python tools/build_us_states.py /path/to/cb_2023_us_state_20m render/assets/us_states.json

Output: states projected to an Albers equal-area conic (lower 48) with Alaska and Hawaii as insets,
simplified, in a 1000 x 620 box: {"width":1000,"height":620,"states":{"TX":[[[x,y],...],...],...}}.
"""
import json
import math
import sys

import shapefile  # pyshp

STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
}
W, H = 1000, 620


def albers(lat0, lon0, lat1, lat2):
    p0, p1, p2 = (math.radians(v) for v in (lat0, lat1, lat2))
    n = (math.sin(p1) + math.sin(p2)) / 2
    c = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    r0 = math.sqrt(c - 2 * n * math.sin(p0)) / n

    def f(lon, lat):
        # Aleutian islands west of the antimeridian are stored with positive longitudes.
        if lon > 0:
            lon -= 360
        r = math.sqrt(c - 2 * n * math.sin(math.radians(lat))) / n
        t = n * math.radians(lon - lon0)
        return r * math.sin(t), r0 - r * math.cos(t)

    return f


PROJ = {
    "AK": albers(50, -154, 55, 65),
    "HI": albers(3, -157, 8, 18),
}
LOWER48 = albers(37.5, -96, 29.5, 45.5)


def simplify(pts, tol):
    if len(pts) < 4:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    best, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[: idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def area(ring):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))) / 2


def main(src, out):
    sys.setrecursionlimit(20000)
    r = shapefile.Reader(src)
    raw = {}
    for sr in r.iterShapeRecords():
        code = sr.record["STUSPS"]
        if code not in STATES:
            continue
        proj = PROJ.get(code, LOWER48)
        shp = sr.shape
        parts = list(shp.parts) + [len(shp.points)]
        raw[code] = [[proj(*p) for p in shp.points[a:b]] for a, b in zip(parts, parts[1:])]

    def bbox(codes):
        xs = [x for c in codes for ring in raw[c] for x, _ in ring]
        ys = [y for c in codes for ring in raw[c] for _, y in ring]
        return min(xs), min(ys), max(xs), max(ys)

    def place(codes, sx, sy, s, box):
        bx0, _, _, by1 = box
        for c in codes:
            raw[c] = [[(sx + (x - bx0) * s, sy + (by1 - y) * s) for x, y in ring] for ring in raw[c]]

    lower = [c for c in raw if c not in PROJ]
    box = bbox(lower)
    scale = min((W - 20) / (box[2] - box[0]), (H - 20) / (box[3] - box[1]))
    place(lower, 10, 10, scale, box)
    place(["AK"], 15, H - 165, 0.35 * scale, bbox(["AK"]))
    place(["HI"], 285, H - 85, scale, bbox(["HI"]))

    states = {}
    for c, rings in sorted(raw.items()):
        kept = []
        for ring in rings:
            # Closed ring: simplify each half, since Douglas-Peucker needs two distinct endpoints.
            mid = len(ring) // 2
            s = simplify(ring[: mid + 1], 0.6)[:-1] + simplify(ring[mid:], 0.6)
            if len(s) >= 4 and area(s) >= 4:
                kept.append([[round(x, 1), round(y, 1)] for x, y in s])
        states[c] = kept
    with open(out, "w") as fh:
        json.dump({"width": W, "height": H, "source": "U.S. Census Bureau, cb_2023_us_state_20m",
                   "states": states}, fh, separators=(",", ":"))
    print(out, len(states), "states", sum(len(ring) for v in states.values() for ring in v), "points")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
