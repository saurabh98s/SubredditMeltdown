#!/usr/bin/env python3
"""
Photon Arctic-Shift downloader
• Subreddit : r/askwomen
• Months    : 2019-10, 2019-11, 2020-10, 2020-11
• Output    : F:\askwomen\<month>\r_askwomen_{posts|comments}.jsonl
• Safe to rerun: existing non-empty files are skipped.
"""

import datetime as dt, json, time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://arctic-shift.photon-reddit.com/api"
ENDPOINTS = {"posts": "posts/search", "comments": "comments/search"}

SUBREDDIT = "movies"
RANGES = [
    ("2019-10-01", "2019-10-31", "2019_october"),
    ("2019-11-01", "2019-11-30", "2019_november"),
    ("2020-10-01", "2020-10-31", "2020_october"),
    ("2020-11-01", "2020-11-30", "2020_november"),
]

# ───────── helpers ────────────────────────────────────────────────────────────
iso_to_ms = lambda d: int(dt.datetime.strptime(d, "%Y-%m-%d")
                          .replace(tzinfo=dt.timezone.utc).timestamp()*1000)

def build_session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", HTTPAdapter(
        max_retries=Retry(total=5, backoff_factor=1.5,
                          status_forcelist=(429, 500, 502, 503, 504),
                          allowed_methods=frozenset(["GET"]))
    ))
    s.headers.update({
        "accept": "*/*",
        "user-agent": "photon-scraper/1.3",
        "referer": "https://arctic-shift.photon-reddit.com/download-tool",
    })
    return s

def load(resp):
    try:               body = resp.json()
    except ValueError: body = resp.text.splitlines()
    if isinstance(body, dict) and "data" in body: body = body["data"]
    if isinstance(body, dict):                     body = [body]
    if isinstance(body, list) and body and isinstance(body[0], str):
        body = [json.loads(l) for l in body if l.strip()]
    return body

# ───────── fetch with 422-bisect ──────────────────────────────────────────────
def fetch(sess, sub, a_ms, b_ms, kind, fp,
          page_comments=100,               # page size
          min_slice_ms=3_600_000):         # stop splitting below 1 h
    """
    Fetch [a_ms, b_ms) for `kind`.
    • comments → limit=page_comments
    • posts    → limit="auto"
    On 400/422 keep halving the slice (down to 1 h) before giving up.
    """
    url   = f"{BASE}/{ENDPOINTS[kind]}"
    total = 0
    stack = [(a_ms, b_ms)]                # LIFO stack of slices

    while stack:
        start_ms, end_ms = stack.pop()

        # --- streaming loop inside this slice -----------------------------
        after = start_ms
        while after < end_ms:
            params = {
                "subreddit": sub,
                "after": after,
                "before": end_ms,
                "limit": page_comments if kind == "comments" else "auto",
                "sort":  "asc",
                "meta-app": "download-tool",
            }
            try:
                r = sess.get(url, params=params, timeout=30)
                r.raise_for_status()
            except requests.HTTPError as e:
                if (r.status_code in (400, 422) and
                        end_ms - start_ms > min_slice_ms):
                    # Too big → split slice in half and retry later
                    mid = start_ms + (end_ms - start_ms) // 2
                    stack.extend([(mid, end_ms), (start_ms, mid)])
                    break  # abandon current inner loop; process splits
                raise e

            batch = load(r)
            if not batch:
                break  # this slice finished

            for obj in batch:
                fp.write(json.dumps(obj) + "\n")
            fp.flush()
            total += len(batch)

            last_sec = max(int(o["created_utc"]) for o in batch)
            after    = (last_sec + 1) * 1000       # advance cursor
            time.sleep(0.25)
    return total

# ───────── main loop ──────────────────────────────────────────────────────────
def main():
    base = Path("F:/") / SUBREDDIT
    base.mkdir(parents=True, exist_ok=True)
    sess = build_session()

    for s_iso, e_iso, tag in RANGES:
        s_ms = iso_to_ms(s_iso)
        e_ms = iso_to_ms(e_iso) + 86_400_000
        month = base / tag
        month.mkdir(parents=True, exist_ok=True)

        for kind in ("posts", "comments"):
            path = month / f"r_{SUBREDDIT}_{kind}.jsonl"
            if path.exists() and path.stat().st_size:
                print(f"[✓] {path.name} exists – skipping")
                continue

            print(f"[→] {tag}: {kind} → {path.name}")
            with path.open("w", encoding="utf-8") as fp:
                n = fetch(sess, SUBREDDIT, s_ms, e_ms, kind, fp)
            print(f"[✓] {n:,} lines written")

    print("Done ✔")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
