#!/usr/bin/env python3
"""Export every Pin from one Pinterest board to a CSV artifact.

Required environment variables:
  PINTEREST_ACCESS_TOKEN
Optional:
  PINTEREST_BOARD_ID (defaults to the owner's Food board)
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_ROOT = "https://api.pinterest.com/v5"
BOARD_ID = os.environ.get("PINTEREST_BOARD_ID", "921901054911077545")
TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN")

if not TOKEN:
    sys.exit("Missing PINTEREST_ACCESS_TOKEN secret. Add it in GitHub Actions repository secrets.")

def get_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "User-Agent": "Recipe-Catalog-Sync/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            sys.exit("Pinterest access token expired/invalid (401). Update the PINTEREST_ACCESS_TOKEN GitHub secret.")
        if exc.code == 403:
            sys.exit("Pinterest denied access (403). Check that the token has boards:read_secret and pins:read_secret scopes.")
        sys.exit(f"Pinterest API returned HTTP {exc.code}: {body[:500]}")

pins = []
bookmark = None
page = 0
while True:
    params = {"page_size": "250"}
    if bookmark:
        params["bookmark"] = bookmark
    url = f"{API_ROOT}/boards/{urllib.parse.quote(BOARD_ID, safe='')}/pins?{urllib.parse.urlencode(params)}"
    payload = get_json(url)
    batch = payload.get("items", [])
    pins.extend(batch)
    page += 1
    print(f"Fetched page {page}: {len(batch)} pins (total {len(pins)})")
    next_bookmark = payload.get("bookmark")
    if not next_bookmark or not batch:
        break
    bookmark = next_bookmark
    time.sleep(0.15)

out_dir = Path("output")
out_dir.mkdir(exist_ok=True)
csv_path = out_dir / "pinterest_recipe_catalog.csv"
json_path = out_dir / "pinterest_recipe_catalog.json"

fields = [
    "id", "title", "description", "link", "created_at", "board_id",
    "alt_text", "media_type", "dominant_color", "pin_url",
]
with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for pin in pins:
        media = pin.get("media") or {}
        writer.writerow({
            "id": pin.get("id", ""),
            "title": pin.get("title", ""),
            "description": pin.get("description", ""),
            "link": pin.get("link", ""),
            "created_at": pin.get("created_at", ""),
            "board_id": BOARD_ID,
            "alt_text": pin.get("alt_text", ""),
            "media_type": media.get("media_type", ""),
            "dominant_color": pin.get("dominant_color", ""),
            "pin_url": f"https://www.pinterest.com/pin/{pin.get('id', '')}/" if pin.get("id") else "",
        })

with json_path.open("w", encoding="utf-8") as f:
    json.dump({"board_id": BOARD_ID, "pin_count": len(pins), "pins": pins}, f, ensure_ascii=False, indent=2)

print(f"SUCCESS: exported {len(pins)} pins to {csv_path} and {json_path}")
