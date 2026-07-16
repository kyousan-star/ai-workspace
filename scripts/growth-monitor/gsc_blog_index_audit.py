#!/usr/bin/env python3
"""Read-only Google Search Console URL Inspection audit for VLOGARA blogs."""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATH = Path.home() / ".claude/scripts/google_growth_token.json"
SITE_URL = "https://vlogara.com/"
API_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
OUTPUT = ROOT / "data" / f"gsc_blog_index_status_{date.today():%Y-%m-%d}.csv"

BLOGS = [
    ("ST102", "Blog 1", "https://vlogara.com/blogs/news/how-to-choose-a-cell-phone-tripod-for-recording-videos"),
    ("ST102", "Blog 2", "https://vlogara.com/blogs/news/best-phone-tripod-height-for-vlogging-yoga-cooking-and-streaming"),
    ("ST102", "Blog 3", "https://vlogara.com/blogs/news/5-moments-that-wrecked-my-first-50-phone-vlogs"),
    ("ST102", "Blog 4", "https://vlogara.com/blogs/news/best-phone-tripod-for-cooking-videos"),
    ("ST102", "Blog 5", "https://vlogara.com/blogs/news/best-phone-tripod-for-yoga-workout-videos"),
    ("ST102", "Blog 6", "https://vlogara.com/blogs/news/71-inch-phone-tripod-vs-60-inch-tripod"),
    ("ST102", "Blog 7", "https://vlogara.com/blogs/news/phone-tripod-with-bluetooth-remote-for-iphone"),
    ("ST102", "Blog 8", "https://vlogara.com/blogs/news/how-to-film-overhead-videos-with-a-phone-tripod"),
    ("VT101", "Blog 9", "https://vlogara.com/blogs/news/phone-vlogging-kit-checklist-light-mic-tripod-mounts"),
]


def access_token() -> str:
    token = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    data = urllib.parse.urlencode({
        "client_id": token["client_id"],
        "client_secret": token["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30) as response:
        return json.loads(response.read())["access_token"]


def inspect(access_token_value: str, url: str) -> dict:
    request = urllib.request.Request(
        API_URL,
        headers={"Authorization": f"Bearer {access_token_value}", "Content-Type": "application/json"},
        data=json.dumps({"inspectionUrl": url, "siteUrl": SITE_URL, "languageCode": "en-US"}).encode(),
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read())


def main() -> None:
    token = access_token()
    rows = []
    for product, blog, url in BLOGS:
        try:
            result = inspect(token, url).get("inspectionResult", {}).get("indexStatusResult", {})
            rows.append({
                "checked_date": f"{date.today():%Y-%m-%d}",
                "product": product,
                "blog": blog,
                "url": url,
                "verdict": result.get("verdict", ""),
                "coverage_state": result.get("coverageState", ""),
                "indexing_state": result.get("indexingState", ""),
                "page_fetch_state": result.get("pageFetchState", ""),
                "robots_txt_state": result.get("robotsTxtState", ""),
                "last_crawl_time": result.get("lastCrawlTime", ""),
                "user_canonical": result.get("userCanonical", ""),
                "google_canonical": result.get("googleCanonical", ""),
                "error": "",
            })
        except Exception as exc:
            rows.append({
                "checked_date": f"{date.today():%Y-%m-%d}",
                "product": product,
                "blog": blog,
                "url": url,
                "verdict": "",
                "coverage_state": "",
                "indexing_state": "",
                "page_fetch_state": "",
                "robots_txt_state": "",
                "last_crawl_time": "",
                "user_canonical": "",
                "google_canonical": "",
                "error": f"{type(exc).__name__}: {exc}",
            })

    fieldnames = list(rows[0])
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(1 for row in rows if row["verdict"] == "PASS")
    failed = sum(1 for row in rows if row["error"])
    print(f"GSC blog index audit: {passed}/9 PASS, {failed} API errors")
    print(OUTPUT)


if __name__ == "__main__":
    main()
