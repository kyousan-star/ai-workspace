from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS_PATH = ROOT / "config" / "accounts.json"


def request_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 WeChatPublicMonitor/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    return json.loads(data)


def normalize_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def append_unique(values: list[str], value: str) -> list[str]:
    merged = list(values)
    if value and value not in merged:
        merged.append(value)
    return merged


def wechat2rss_add_url(base_url: str, token: str, article_url: str) -> str:
    query = urllib.parse.urlencode({"url": article_url, "k": token})
    payload = request_json(f"{base_url}/addurl?{query}")
    if payload.get("err"):
        raise RuntimeError(payload["err"])
    return str(payload.get("data") or "").strip()


def wechat2rss_add_id(base_url: str, token: str, biz_id: str) -> str:
    query = urllib.parse.urlencode({"k": token})
    payload = request_json(f"{base_url}/add/{urllib.parse.quote(biz_id)}?{query}")
    if payload.get("err"):
        raise RuntimeError(payload["err"])
    return str(payload.get("data") or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Wechat2RSS feeds for monitored accounts.")
    parser.add_argument("--base-url", default=os.getenv("WECHAT2RSS_BASE_URL", ""))
    parser.add_argument("--token", default=os.getenv("WECHAT2RSS_TOKEN", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.base_url or not args.token:
        raise SystemExit("Set WECHAT2RSS_BASE_URL and WECHAT2RSS_TOKEN, or pass --base-url and --token.")

    base_url = normalize_base_url(args.base_url)
    accounts = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    results = []

    for account in accounts:
        feed_url = ""
        error = ""
        try:
            if account.get("sample_article_url"):
                feed_url = wechat2rss_add_url(base_url, args.token, account["sample_article_url"])
            elif account.get("biz_id"):
                feed_url = wechat2rss_add_id(base_url, args.token, account["biz_id"])
            else:
                error = "missing sample_article_url and biz_id"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        if feed_url:
            account["feeds"] = append_unique(account.get("feeds", []), feed_url)
        results.append((account["wechat_id"], account["name"], feed_url, error))

    print("wechat_id\tname\tfeed_url\terror")
    for row in results:
        print("\t".join(row))

    if not args.dry_run:
        ACCOUNTS_PATH.write_text(json.dumps(accounts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
