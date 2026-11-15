"""Haul-Away Haulers media renderers: one module per job kind, each with EXT, validate(data) and
render(data, out_path). Kinds match public.marketing_media_jobs.kind on the site."""
from . import card, carrier_map, diesel_trend, pulse_short

KINDS = {
    "pulse_short": pulse_short,
    "diesel_trend": diesel_trend,
    "carrier_map": carrier_map,
    "card": card,
}
CONTENT_TYPE = {"mp4": "video/mp4", "png": "image/png"}
