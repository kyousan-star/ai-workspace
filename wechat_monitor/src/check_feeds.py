from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import urllib.error
import xml.etree.ElementTree as ET

import monitor


ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS_PATH = ROOT / "config" / "accounts.json"


def candidate_feed_urls(account: dict) -> list[str]:
    urls = list(account.get("feeds", []))
    if account.get("biz"):
        urls.append(f"https://rsshub.app/freewechat/profile/{account['biz']}")
    if account.get("biz_id"):
        urls.append(f"https://wechat2rss.xlab.app/feed/{account['biz_id']}.xml")
    return list(dict.fromkeys(urls))


def parse_feed(xml: str) -> tuple[int, str]:
    root = ET.fromstring(xml)
    items = root.findall(".//item")
    if not items:
        items = root.findall("{http://www.w3.org/2005/Atom}entry")
    sample = ""
    if items:
        sample = (
            items[0].findtext("title")
            or items[0].findtext("{http://www.w3.org/2005/Atom}title")
            or ""
        ).strip()
    return len(items), sample


def test_feed(url: str) -> tuple[bool, str]:
    try:
        xml = monitor.request_text(url, timeout=20)
        lowered = xml[:500].lower()
        if "<rss" not in lowered and "<feed" not in lowered:
            return False, "not rss/atom"
        count, sample = parse_feed(xml)
        if count <= 0:
            return False, "0 items"
        return True, f"{count} items; {sample[:80]}"
    except Exception as exc:
        if isinstance(exc, urllib.error.HTTPError):
            return False, f"HTTP {exc.code}"
        return False, f"{type(exc).__name__}: {exc}"


def append_unique(values: list[str], value: str) -> list[str]:
    merged = list(values)
    if value and value not in merged:
        merged.append(value)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Check public Wechat RSS feeds and optionally write usable feeds.")
    parser.add_argument("--write", action="store_true", help="Write newly working feeds to config/accounts.json")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    accounts = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    found = 0
    print("wechat_id\tname\tok\tstatus\turl")
    for account in accounts:
        account_found = False
        for url in candidate_feed_urls(account):
            ok, status = test_feed(url)
            print("\t".join([account["wechat_id"], account["name"], str(ok), status, url]))
            sys.stdout.flush()
            if ok:
                account_found = True
                if args.write:
                    account["feeds"] = append_unique(account.get("feeds", []), url)
                break
            time.sleep(args.delay)
        if account_found:
            found += 1

    if args.write:
        ACCOUNTS_PATH.write_text(json.dumps(accounts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"working_feed_accounts={found}/{len(accounts)}")


if __name__ == "__main__":
    main()
