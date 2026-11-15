# hah-video-renderer

Renders Haul-Away Haulers' marketing videos and images for free on GitHub Actions.

Once a day (15:20 UTC, or by hand from the Actions tab) the workflow asks
haulawayhaulers.com for its pending render jobs, renders each one, and uploads the
file back to the site. The site stores it and uses it in its social posts.

**This repo holds only render code.** It has no data and no secrets. Every number
in a video comes from the job the site sends at run time. The one credential,
`VIDEO_UPLOAD_TOKEN`, lives in the repo's Actions secrets and is never printed.

## What it renders

| kind | output | data comes from (on the site) |
|---|---|---|
| `pulse_short` | 1080x1920 MP4, ~14.5 s | the week's Freight Pulse (`freight_pulse_weekly`) |
| `diesel_trend` | 1080x1920 MP4, 16 s, animated line chart | U.S. average diesel, last 12 EIA weeks |
| `carrier_map` | 1080x1920 MP4, 16 s, U.S. map by state | the monthly new-carrier report (FMCSA) |
| `card` | 1080x1080 PNG | title + 1-3 lines, sent by whatever queued it |

The data shape for each kind is in the docstring at the top of `render/<kind>.py`.

## How it talks to the site

- `GET  $SITE_URL/api/marketing/render-queue` returns `{ jobs: [{id, kind, data}] }`
- `PUT  $SITE_URL/api/marketing/media?id=<id>` with the `video/mp4` or `image/png` file
- `POST $SITE_URL/api/marketing/media/fail?id=<id>` with `{ "error": "..." }`

All three send `Authorization: Bearer $VIDEO_UPLOAD_TOKEN`. The site counts attempts;
after 5 it stops retrying and emails the owner one link to try again.

## Setup (once)

- Actions secret `VIDEO_UPLOAD_TOKEN`: the same value as the site's Worker secret of that name.
- Actions variable `SITE_URL`: `https://haulawayhaulers.com`

## Run the tests

Needs Python 3.12+ and ffmpeg.

```
pip install -r requirements.txt
pytest -q                         # renders every kind from tests/fixtures/jobs.json
RENDER_OUT=/tmp/out pytest -q     # same, keeping the files to look at
```

## Credits and licenses

- Inter font (`render/fonts/`), SIL Open Font License 1.1: see `render/fonts/OFL.txt`.
- State shapes (`render/assets/us_states.json`): U.S. Census Bureau cartographic boundary file
  `cb_2023_us_state_20m`, simplified and projected by `tools/build_us_states.py`. Census terms
  allow free use with acknowledgement of the Census Bureau as the source, which the map video
  shows on screen.
