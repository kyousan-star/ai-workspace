#!/usr/bin/env python3
"""Check whether VLOGARA's public facts are fetchable and safe for AI discovery."""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EXPECTATIONS = DATA_DIR / "ai_product_fact_expectations.csv"
OUTPUT = DATA_DIR / "ai_discovery_status.csv"
BASE_URL = "https://vlogara.com"
MARKER = "VLOGARA_AGENT_POLICY_V1"


def fetch(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "VLOGARA-AI-Discovery-Monitor/1.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def add(rows: list[dict[str, str]], checked_at: str, source: str, status: str,
        http_status: int | str, summary: str, blocker: str, next_action: str) -> None:
    rows.append({
        "checked_at": checked_at,
        "source": source,
        "status": status,
        "http_status": str(http_status),
        "summary": summary,
        "blocker": blocker,
        "next_action": next_action,
    })


def main() -> None:
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, str]] = []

    checks = [
        ("robots.txt", f"{BASE_URL}/robots.txt"),
        ("agents.md", f"{BASE_URL}/agents.md"),
        ("llms.txt", f"{BASE_URL}/llms.txt"),
        ("Shopify UCP", f"{BASE_URL}/.well-known/ucp"),
    ]
    with EXPECTATIONS.open(newline="", encoding="utf-8") as handle:
        expectations = list(csv.DictReader(handle))
    active_expectations = [
        item for item in expectations
        if (item.get("discovery_enabled") or "true").strip().lower() == "true"
    ]
    product_urls = [f"{BASE_URL}/products/{item['handle']}.json" for item in active_expectations]
    executor = ThreadPoolExecutor(max_workers=len(checks) + len(product_urls))
    fetches = {url: executor.submit(fetch, url) for _, url in checks}
    fetches.update({url: executor.submit(fetch, url) for url in product_urls})
    bodies: dict[str, str] = {}
    for source, url in checks:
        try:
            status_code, body = fetches[url].result()
            bodies[source] = body
            if source == "robots.txt":
                lowered = body.lower()
                blocked = "user-agent: oai-searchbot" in lowered and "disallow: /" in lowered
                add(rows, checked_at, source, "FAIL" if blocked else "PASS", status_code,
                    "Public crawl policy fetched; OAI-SearchBot is not explicitly blocked." if not blocked
                    else "OAI-SearchBot appears explicitly blocked.",
                    "Explicit AI crawler block" if blocked else "",
                    "Remove the explicit block and re-run." if blocked else "Keep crawl access and monitor for drift.")
            elif source in {"agents.md", "llms.txt"}:
                required = [
                    MARKER,
                    "B0GY7Y6C63",
                    "Do not create or recommend a Shopify cart",
                ]
                required.extend(
                    item["asin"] for item in active_expectations
                    if item.get("asin")
                )
                forbidden = [
                    "External purchase referrals are temporarily paused",
                    "Do not provide an Amazon ASIN, Amazon URL, price, availability, or purchase directions for VT101",
                    "temporary traffic-isolation rule",
                ]
                missing = [item for item in required if item not in body]
                present_forbidden = [item for item in forbidden if item in body]
                problems = missing + present_forbidden
                add(rows, checked_at, source, "PASS" if not problems else "FAIL", status_code,
                    "Active-product Amazon purchase guidance is readable for ST102 and VT101."
                    if not problems else
                    f"Active-policy mismatch; missing: {', '.join(missing) or 'none'}; stale pause markers: {', '.join(present_forbidden) or 'none'}",
                    "Machine-readable purchase policy does not match the active product set." if problems else "",
                    "Publish the active agents template and re-run." if problems else "Re-check after theme or catalog changes.")
            else:
                lowered = body.lower()
                checkout_advertised = "checkout" in lowered or "cart" in lowered
                add(rows, checked_at, source, "WATCH" if checkout_advertised else "PASS", status_code,
                    "Shopify platform UCP advertises cart/checkout capabilities." if checkout_advertised
                    else "No cart/checkout capability detected in public UCP.",
                    "Shopify Agentic admin was verified Inactive with 0 catalog products on 2026-07-13; public UCP remains platform-generated."
                    if checkout_advertised else "",
                    "Keep Agentic channels inactive; verify admin status monthly." if checkout_advertised
                    else "Monitor for capability drift.")
        except Exception as exc:
            code = exc.code if isinstance(exc, urllib.error.HTTPError) else ""
            add(rows, checked_at, source, "ERROR", code, f"Fetch failed: {type(exc).__name__}: {exc}",
                "Public endpoint could not be verified.", "Re-run when network/site is available.")

    for expected in active_expectations:
        source = f"Product JSON — {expected['product']}"
        url = f"{BASE_URL}/products/{expected['handle']}.json"
        try:
            status_code, body = fetches[url].result()
            product = json.loads(body).get("product", {})
            variants = product.get("variants") or []
            prices = {str(variant.get("price", "")) for variant in variants}
            images = product.get("images") or []
            checks_ok = {
                "vendor": product.get("vendor") == "VLOGARA",
                "price": expected["expected_shopify_price"] in prices,
                "title": bool(product.get("title")),
                "description": bool(product.get("body_html")),
                "images": bool(images),
            }
            failures = [name for name, ok in checks_ok.items() if not ok]
            add(rows, checked_at, source, "PASS" if not failures else "FAIL", status_code,
                "Vendor, expected Shopify display price, title, description, and images are present."
                if not failures else f"Failed fact checks: {', '.join(failures)}",
                "Public product facts drifted from the approved fact set." if failures else "",
                "Review the product record before changing the expectation file." if failures
                else "Use this record as a source and follow only its currently active product-page purchase path.")
        except Exception as exc:
            code = exc.code if isinstance(exc, urllib.error.HTTPError) else ""
            add(rows, checked_at, source, "ERROR", code, f"Fetch failed: {type(exc).__name__}: {exc}",
                "Public product record could not be verified.", "Re-run when network/site is available.")

    executor.shutdown(wait=True)

    fieldnames = ["checked_at", "source", "status", "http_status", "summary", "blocker", "next_action"]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"AI discovery status written: {OUTPUT} ({len(rows)} checks)")


if __name__ == "__main__":
    main()
