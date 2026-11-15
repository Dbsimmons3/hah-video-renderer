"""Renders every kind from real fixture data and checks the output with ffprobe / Pillow.
Set RENDER_OUT=/some/dir to keep the files for a look; otherwise they go to pytest's tmp dir."""
import copy
import json
import os
import subprocess

import pytest
from PIL import Image

from render import KINDS

FIXTURES = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "jobs.json")))


@pytest.fixture
def outdir(tmp_path):
    d = os.environ.get("RENDER_OUT") or str(tmp_path)
    os.makedirs(d, exist_ok=True)
    return d


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height",
         "-show_entries", "format=duration", "-of", "json", path],
        check=True, capture_output=True, text=True).stdout
    return json.loads(out)


@pytest.mark.parametrize("kind,lo,hi", [
    ("pulse_short", 13.5, 16.0),
    ("diesel_trend", 14.0, 18.0),
    ("carrier_map", 14.0, 18.0),
])
def test_video(kind, lo, hi, outdir):
    out = os.path.join(outdir, f"{kind}.mp4")
    KINDS[kind].render(copy.deepcopy(FIXTURES[kind]), out)
    info = probe(out)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1080, 1920)
    assert video["codec_name"] == "h264"
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert lo <= float(info["format"]["duration"]) <= hi
    assert os.path.getsize(out) < 50 * 1024 * 1024


def test_card(outdir):
    out = os.path.join(outdir, "card.png")
    KINDS["card"].render(copy.deepcopy(FIXTURES["card"]), out)
    with Image.open(out) as im:
        assert im.format == "PNG" and im.size == (1080, 1080)
    assert os.path.getsize(out) < 10 * 1024 * 1024


@pytest.mark.parametrize("kind,patch", [
    ("pulse_short", {"diesel": 0}),
    ("pulse_short", {"new_carriers": None}),
    ("diesel_trend", {"points": [{"period": "2026-11-09", "price": 6.1}]}),
    ("carrier_map", {"total": "13012"}),
    ("card", {"lines": []}),
    ("card", {"title": "x" * 200}),
])
def test_rejects_bad_data(kind, patch, tmp_path):
    with pytest.raises(ValueError):
        KINDS[kind].render({**FIXTURES[kind], **patch}, str(tmp_path / "x"))
