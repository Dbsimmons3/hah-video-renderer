#!/usr/bin/env python3
"""Fetch the site's render queue, render each job, upload the result (or report the failure).

Env: SITE_URL (e.g. https://haulawayhaulers.com), VIDEO_UPLOAD_TOKEN (secret; never printed).
The site owns retries and owner alerts: each queue fetch counts one attempt per job it returns,
and after 5 the site marks the job failed and emails the owner a one-click requeue link. So a
failed render here is reported to the site and the run carries on with the next job.

Exit status: 1 only when the queue itself can't be read (bad token or site down), else 0.
"""
import json
import os
import sys
import tempfile
import traceback
import urllib.error
import urllib.parse
import urllib.request

from render import CONTENT_TYPE, KINDS

UA = "hah-video-renderer/1"


def call(method: str, url: str, token: str, body=None, headers=None, timeout=120):
    req = urllib.request.Request(url, data=body, method=method, headers={
        "authorization": f"Bearer {token}", "user-agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read() or b"null")


def main() -> int:
    site = os.environ.get("SITE_URL", "").rstrip("/")
    token = os.environ.get("VIDEO_UPLOAD_TOKEN", "")
    if not site or not token:
        print("SITE_URL and VIDEO_UPLOAD_TOKEN must be set", file=sys.stderr)
        return 1
    try:
        jobs = call("GET", f"{site}/api/marketing/render-queue", token)["jobs"]
    except (urllib.error.URLError, KeyError, ValueError) as e:
        print(f"queue fetch failed: {getattr(e, 'code', '')} {getattr(e, 'reason', e)}", file=sys.stderr)
        return 1
    print(f"{len(jobs)} job(s) queued")

    with tempfile.TemporaryDirectory() as td:
        for job in jobs:
            jid, kind = job["id"], job["kind"]
            q = urllib.parse.urlencode({"id": jid})
            mod = KINDS.get(kind)
            out = os.path.join(td, f"{jid}.{mod.EXT if mod else 'bin'}")
            try:
                if not mod:
                    raise ValueError(f"unknown kind {kind!r}")
                mod.render(job["data"], out)
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"[:500]
                print(f"{kind} {jid}: render failed: {msg}")
                traceback.print_exc()
                try:
                    call("POST", f"{site}/api/marketing/media/fail?{q}", token,
                         json.dumps({"error": msg}).encode(), {"content-type": "application/json"})
                except urllib.error.URLError as fe:
                    print(f"{kind} {jid}: could not report failure: {getattr(fe, 'code', fe)}")
                continue
            size = os.path.getsize(out)
            try:
                with open(out, "rb") as fh:
                    r = call("PUT", f"{site}/api/marketing/media?{q}", token, fh,
                             {"content-type": CONTENT_TYPE[mod.EXT], "content-length": str(size)},
                             timeout=300)
                print(f"{kind} {jid}: uploaded {size:,} bytes -> {r.get('url')}")
            except urllib.error.HTTPError as e:
                print(f"{kind} {jid}: upload failed: HTTP {e.code} {e.read()[:300]!r}")
            except urllib.error.URLError as e:
                print(f"{kind} {jid}: upload failed: {e.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
