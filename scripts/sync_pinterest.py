#!/usr/bin/env python3
"""Export all Pins from the configured Pinterest board to private-use artifacts.

Required GitHub Actions secrets:
  PINTEREST_APP_ID, PINTEREST_APP_SECRET, PINTEREST_REFRESH_TOKEN
Optional:
  PINTEREST_BOARD_ID
"""
import base64
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
APP_ID = os.environ.get("PINTEREST_APP_ID")
APP_SECRET = os.environ.get("PINTEREST_APP_SECRET")
REFRESH_TOKEN = os.environ.get("PINTEREST_REFRESH_TOKEN")

if not APP_ID or not APP_SECRET or not REFRESH_TOKEN:
    sys.exit("Missing one or more required GitHub Actions secrets: PINTEREST_APP_ID, PINTEREST_APP_SECRET, PINTEREST_REFRESH_TOKEN.")

def refresh_access_token():
    credentials = base64.b64encode(f"{APP_ID}:{APP_SECRET}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    }).encode()
    req = urllib.request.Request(
        "https://api.pinterest.com/v5/oauth/token",
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Recipe-Catalog-Sync/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        if exc.code in (400, 401):
            sys.exit("Pinterest could not refresh the token. Check PINTEREST_APP_ID, PINTEREST_APP_SECRET and PINTEREST_REFRESH_TOKEN in GitHub Secrets; if the refresh token was revoked or expired, reconnect Pinterest and replace it. Details: " + body_text[:300])
        sys.exit(f"Pinterest token endpoint returned HTTP {exc.code}: {body_text[:300]}")
    token = data.get("access_token")
    if not token:
        sys.exit("Pinterest's refresh response did not include an access token.")
    if data.get("refresh_token") and data["refresh_token"] != REFRESH_TOKEN:
        print("WARNING: Pinterest returned a replacement refresh token. Update the PINTEREST_REFRESH_TOKEN GitHub secret before the next scheduled run.")
    return token

TOKEN = refresh_access_token()

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
        body_text = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            sys.exit("Pinterest rejected the refreshed access token (401). Reconnect Pinterest and replace the GitHub secrets.")
        if exc.code == 403:
            sys.exit("Pinterest denied access (403). Check that the token was authorized with boards:read_secret and pins:read_secret.")
        sys.exit(f"Pinterest API returned HTTP {exc.code}: {body_text[:400]}")

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
csv_path = out_dir / "pinterest_pins.csv"
json_path = out_dir / "pinterest_pins.json"

fields = ["id", "title", "description", "link", "created_at", "board_id", "alt_text", "media_type", "dominant_color", "pin_url"]
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
