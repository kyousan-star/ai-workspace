#!/usr/bin/env python3
"""Vlogara Reddit 哨兵 — 挂在卖家脉搏晨报里的每日只读巡检。

做三件事（全部只读，不发布任何内容）：
1. 回查：逐条刷新已发评论的分数/回复数，回填 reddit_engagement_log.csv
2. 告警：评论疑似被删、分数为负、出现新回复 → 进飞书告警行
3. 补弹粗筛：扫目标 sub 的 new 页，按关键词粗筛 <48h 且回答少的候选帖
   （只筛不判断，正式判断和草稿在会话「跑 Vlogara Reddit 日常」里做）
   - 去重主源=账号真实评论历史（fetch_replied_thread_ids），CSV logged_urls 只是兜底
   - 冷启动养 karma 期：候选按 traction=hot(有围观🔥)/cold 排序，hot 优先（执行方案 §2.4）

两块依赖不同，互不拖累：
- 补弹粗筛：先 urllib 直抓 old.reddit HTML；2026-07-15 起 reddit 对直连 HTML 也返 403，
  被封的 sub 用回查同一条 Chrome 通道补抓（fetch_new_listing_via_tab）。
- 回查已发评论：需 web-access CDP proxy（localhost:3456，本机 Chrome 登录态）。
  proxy 不可用时跳过回查（飞书标注「会话补」），直抓成功的 sub 候选照常产出。
  会话触发「跑 Vlogara Reddit 日常」时 Chrome 在，回查+补抓随之补上。

输出：
- data/reddit_sentinel_feishu.txt   首行 DATE:YYYY-MM-DD，其余为飞书消息行
- output/reddit_sentinel_YYYY-MM-DD.json  当日完整巡检结果
- data/reddit_seen_candidates.txt   已推荐过的帖子 id，避免 48h 窗口内重复推荐
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # growth-monitor/
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "output"
LOG_CSV = DATA_DIR / "reddit_engagement_log.csv"
FEISHU_TXT = DATA_DIR / "reddit_sentinel_feishu.txt"
SEEN_FILE = DATA_DIR / "reddit_seen_candidates.txt"

PROXY = "http://localhost:3456"
CHECK_DEPS = Path.home() / ".claude/skills/web-access/scripts/check-deps.mjs"
TODAY = os.environ.get("BRIEF_DATE", date.today().strftime("%Y-%m-%d"))

ACCOUNT = "Aggravating-Usual213"
# 抓 old.reddit HTML 用浏览器 UA（reddit 已封 .json 与描述性UA 直连=403；HTML 页仍 200）
SCAN_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 目标 sub（执行方案 §2.2）；videography 是红线 sub，命中三脚架词时要标警示
SCAN_SUBS = ["NewTubers", "vlogging", "mobilefilmmaking", "iPhoneography", "videography"]
REDLINE_SUB = "videography"

# 需求簇关键词粗筛（只做召回，精判留给会话）
CLUSTERS = {
    "簇1-便宜三脚架": ["tripod"],
    "簇8-starter kit": ["starter kit", "beginner", "starting out", "first camera", "first setup"],
    "新手装备推荐": ["what gear", "equipment", "recommend", "which camera", "budget", "worth buying", "worth it"],
    "手机拍摄setup": ["phone", "iphone", "android", "smartphone"],
    "音频": ["mic", "microphone", "audio", "lav "],
    "稳定器": ["gimbal", "stabiliz", "shaky"],
    "灯光": ["lighting", "ring light", "softbox", " light "],
    "俯拍": ["overhead", "top down", "top-down"],
    "vlog": ["vlog"],
}
QUESTION_HINTS = ["?", "how ", "what ", "which ", "should i", "help", "advice", "recommend", "vs ", "or "]

MAX_CANDIDATES = 5
FRESH_HOURS = 48
MAX_EXISTING_COMMENTS = 10
PAGE_INTERVAL_SEC = 2.5

# 冷启动养 karma 期（执行方案 §2.4 特别规则，2026-07-15 用户实证后加）：
# 有围观的帖（评论/赞过阈值）标 hot 排前面，0 围观冷帖标 cold——冷帖首答攒不到 karma
TRACTION_MIN_COMMENTS = 3
TRACTION_MIN_SCORE = 3


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] reddit_sentinel: {msg}")


# ── CDP proxy 封装 ────────────────────────────────────────────────────────────

def proxy_get(path: str) -> dict:
    with urllib.request.urlopen(f"{PROXY}{path}", timeout=45) as r:
        return json.loads(r.read().decode())


def proxy_eval(target: str, js: str):
    req = urllib.request.Request(
        f"{PROXY}/eval?target={target}", data=js.encode(), method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        body = json.loads(r.read().decode())
    return body.get("value")


def ensure_proxy() -> bool:
    env = dict(os.environ, CLAUDE_SKILL_DIR=str(CHECK_DEPS.parent.parent))
    try:
        r = subprocess.run(["node", str(CHECK_DEPS)], env=env,
                           capture_output=True, text=True, timeout=60)
        return r.returncode == 0 and "proxy: ready" in (r.stdout + r.stderr)
    except Exception as e:
        log(f"check-deps 失败: {e}")
        return False


class Tab:
    def __init__(self):
        self.target = None

    def __enter__(self):
        self.target = proxy_get("/new?url=about:blank")["targetId"]
        return self

    def __exit__(self, *exc):
        try:
            proxy_get(f"/close?target={self.target}")
        except Exception:
            pass

    def goto(self, url: str):
        proxy_get(f"/navigate?target={self.target}&url={urllib.parse.quote(url, safe=':/?&=.')}")
        time.sleep(PAGE_INTERVAL_SEC)

    def eval(self, js: str):
        return proxy_eval(self.target, js)


# ── 1. 回查已发评论 ───────────────────────────────────────────────────────────

CHECK_COMMENT_JS = """
(() => {
  const c = document.querySelector(".commentarea .sitetable > .thing.comment");
  if (!c) return JSON.stringify({found: false});
  const replies = [...c.querySelectorAll(":scope > .child > .sitetable > .thing.comment")]
    .map(el => el.getAttribute("data-author"))
    .filter(a => a && a !== "AutoModerator" && a !== "%(account)s");
  return JSON.stringify({
    found: true,
    author: c.getAttribute("data-author"),
    score: parseInt(c.querySelector(".score.unvoted")?.getAttribute("title") ??
                    (c.querySelector(".score.unvoted")?.textContent || "").split(" ")[0], 10),
    replyAuthors: replies
  });
})()
"""


def check_posted_comments(tab: Tab):
    rows = list(csv.DictReader(open(LOG_CSV, encoding="utf-8")))
    alerts, ok_count = [], 0
    for row in rows:
        url = (row.get("comment_url") or "").strip()
        if not url or row.get("status") == "deleted":
            continue
        old_url = url.replace("www.reddit.com", "old.reddit.com")
        tab.goto(old_url + ("?context=0" if "?" not in old_url else ""))
        raw = tab.eval(CHECK_COMMENT_JS % {"account": ACCOUNT})
        try:
            info = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            info = {"found": False}

        title = (row.get("thread_title") or "")[:40]
        if not info.get("found") or info.get("author") in ("[deleted]", None):
            alerts.append(f"🚨 疑似被删：r/{row['subreddit']}「{title}」需人工核实")
            continue

        score = info.get("score")
        old_replies = int(row.get("followup_replies") or 0)
        new_replies = len(info.get("replyAuthors") or [])
        if isinstance(score, int):
            if score < 0:
                alerts.append(f"🚨 负分 {score}：r/{row['subreddit']}「{title}」")
            row["karma"] = str(score)
        if new_replies > old_replies:
            who = ", ".join(f"u/{a}" for a in (info.get("replyAuthors") or [])[:3])
            alerts.append(f"💬 新回复 +{new_replies - old_replies}（{who}）：r/{row['subreddit']}「{title}」")
        row["followup_replies"] = str(new_replies)
        ok_count += 1

    with open(LOG_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return ok_count, len(rows), alerts


# ── 2. 候选粗筛（公开 JSON，urllib 直连，不经 Chrome）─────────────────────────────

class _NewListingParser(HTMLParser):
    """解析 old.reddit /r/{sub}/new/ HTML，提取链接帖的 data 属性 + 标题。
    字段名对齐旧 .json 口径（created_utc 秒 / num_comments / permalink）。"""

    def __init__(self):
        super().__init__()
        self.posts = []
        self._cur = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "div":
            cls = (d.get("class") or "").split()
            fn = d.get("data-fullname") or ""
            if fn.startswith("t3_") and "link" in cls:
                if d.get("data-promoted") == "true" or "promoted" in cls:
                    self._cur = None
                    return
                ts = int(d.get("data-timestamp") or 0)
                self._cur = {
                    "name": fn,
                    "created_utc": ts / 1000 if ts else 0,   # HTML 给毫秒
                    "num_comments": int(d.get("data-comments-count") or 0),
                    "post_score": int(d.get("data-score") or 0),
                    "permalink": d.get("data-permalink") or "",
                    "stickied": "stickied" in cls,
                    "title": "",
                }
        elif tag == "a" and self._cur is not None:
            if "title" in (d.get("class") or "").split():
                self._in_title = True

    def handle_data(self, data):
        if self._in_title and self._cur is not None:
            self._cur["title"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title:
            self._in_title = False
            if self._cur and self._cur["title"].strip():
                self.posts.append(self._cur)
                self._cur = None


def fetch_new_listing(sub: str) -> list:
    """抓 old.reddit /r/{sub}/new/ HTML（浏览器 UA，无需登录），返回帖 data 列表。"""
    url = f"https://old.reddit.com/r/{sub}/new/"
    req = urllib.request.Request(url, headers={
        "User-Agent": SCAN_UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    parser = _NewListingParser()
    parser.feed(html)
    return parser.posts


# Chrome 补抓用：字段口径对齐 fetch_new_listing（created_utc 秒 / num_comments / permalink）
SCAN_SUB_JS = """
(() => {
  const posts = [...document.querySelectorAll(".thing.link")]
    .filter(el => el.getAttribute("data-promoted") !== "true" && !el.classList.contains("promoted"))
    .map(el => ({
      name: el.getAttribute("data-fullname") || "",
      created_utc: parseInt(el.getAttribute("data-timestamp") || "0", 10) / 1000,
      num_comments: parseInt(el.getAttribute("data-comments-count") || "0", 10),
      post_score: parseInt(el.getAttribute("data-score") || "0", 10),
      permalink: el.getAttribute("data-permalink") || "",
      stickied: el.classList.contains("stickied"),
      title: el.querySelector("a.title")?.textContent || ""
    }));
  return JSON.stringify(posts);
})()
"""


def fetch_new_listing_via_tab(tab, sub: str) -> list:
    """直抓被封时的兜底：经 Chrome 代理打开 /r/{sub}/new/ 再取同口径字段。"""
    tab.goto(f"https://old.reddit.com/r/{sub}/new/")
    return json.loads(tab.eval(SCAN_SUB_JS) or "[]")


# 已回帖去重主源：账号公开评论页里每条评论的 data-permalink 含所属帖的 id36
_REPLIED_RE = re.compile(r'data-permalink="/r/[^/"]+/comments/([a-z0-9]+)/')

_REPLIED_JS = """
(() => {
  const ids = [...document.querySelectorAll(".thing.comment")]
    .map(el => ((el.getAttribute("data-permalink") || "").match(/\\/comments\\/([a-z0-9]+)\\//) || [])[1])
    .filter(x => x);
  return JSON.stringify(ids);
})()
"""


def fetch_replied_thread_ids(tab=None):
    """读账号评论历史，返回回过的帖 t3_ id 集合（真实历史=去重主源，CSV 只是兜底）。
    urllib 直抓先试，被封且有 Chrome tab 时走渲染页 DOM；
    两条通道都拿不到（或解析出 0 条=疑似坏页）返回 None → 调用方不拦截，交 CSV 兜底。"""
    url = f"https://old.reddit.com/user/{ACCOUNT}/comments/"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": SCAN_UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            ids = {"t3_" + m for m in _REPLIED_RE.findall(r.read().decode("utf-8", "replace"))}
        if ids:
            return ids
    except Exception as e:
        log(f"账号评论历史直抓失败：{e}")
    if tab is None:
        return None
    try:
        tab.goto(url)
        ids = json.loads(tab.eval(_REPLIED_JS) or "[]")
        return {"t3_" + i for i in ids} or None
    except Exception as e:
        log(f"账号评论历史 Chrome 抓取失败：{e}")
        return None


def load_scan_filters(tab=None):
    seen = set()
    if SEEN_FILE.exists():
        seen = set(SEEN_FILE.read_text().split())
    logged_urls = " ".join(r.get("thread_url", "") for r in csv.DictReader(open(LOG_CSV, encoding="utf-8")))
    replied = fetch_replied_thread_ids(tab)
    if replied is None:
        log("已回帖历史不可用，本轮去重退回 CSV 兜底")
    return seen, logged_urls, replied


def filter_posts(sub: str, posts: list, seen: set, logged_urls: str, replied_threads=None) -> list:
    now = datetime.now(timezone.utc).timestamp()
    candidates = []
    for p in posts:
        fid = p.get("name")
        if not fid or fid in seen or p.get("stickied"):
            continue
        # 已回帖去重（主源）：账号评论历史里回过 → 跳过。
        # 降级时 replied_threads 为 None（falsy），本行不拦截，交由下方 CSV 兜底。
        if replied_threads and fid in replied_threads:
            continue
        age_h = (now - p.get("created_utc", 0)) / 3600 if p.get("created_utc") else 999
        num_c = p.get("num_comments", 0)
        if age_h > FRESH_HOURS or num_c >= MAX_EXISTING_COMMENTS:
            continue
        purl = "https://old.reddit.com" + p.get("permalink", "")
        if purl.split("?")[0].rstrip("/") in logged_urls:
            continue
        t = " " + p.get("title", "").lower() + " "
        hit_clusters = [c for c, kws in CLUSTERS.items() if any(k in t for k in kws)]
        if not hit_clusters:
            continue
        score = len(hit_clusters) + sum(1 for q in QUESTION_HINTS if q in t)
        warn = "⚠️红线sub" if (sub == REDLINE_SUB and "簇1-便宜三脚架" in hit_clusters) else ""
        traction = ("hot" if num_c >= TRACTION_MIN_COMMENTS
                    or p.get("post_score", 0) >= TRACTION_MIN_SCORE else "cold")
        candidates.append({
            "sub": sub, "id": fid, "title": p.get("title", "").strip()[:80],
            "url": purl, "comments": num_c, "post_score": p.get("post_score", 0),
            "age_h": round(age_h, 1), "clusters": hit_clusters,
            "score": score, "warn": warn, "traction": traction,
        })
    return candidates


def scan_candidates():
    """urllib 直抓各 sub；返回 (candidates, failed_subs)，截断与 seen 落盘留给 main 合并后做。"""
    seen, logged_urls, replied = load_scan_filters()
    candidates, failed_subs = [], []
    for sub in SCAN_SUBS:
        try:
            posts = fetch_new_listing(sub)
        except Exception as e:
            log(f"r/{sub} 直抓失败（待 Chrome 补抓）：{e}")
            failed_subs.append(sub)
            continue
        candidates += filter_posts(sub, posts, seen, logged_urls, replied)
        time.sleep(PAGE_INTERVAL_SEC)
    return candidates, failed_subs


# ── 输出 ─────────────────────────────────────────────────────────────────────

def write_feishu(lines):
    FEISHU_TXT.write_text(f"DATE:{TODAY}\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUT_DIR.mkdir(exist_ok=True)

    # 补弹粗筛：先 urllib 直抓（无人值守可跑）；被封的 sub 记下来走 Chrome 补抓
    try:
        cands, failed_subs = scan_candidates()
    except Exception as e:
        cands, failed_subs = [], list(SCAN_SUBS)
        log(f"粗筛异常：{e}")

    # 回查已发评论：需登录态 proxy；同一 Tab 顺带补抓直抓被封的 sub
    # （2026-07-15 起 reddit 对 old.reddit HTML 直连也返 403，Chrome 通道成为粗筛主路径）
    ok = total = 0
    alerts = []
    recheck_done = False
    if ensure_proxy():
        try:
            with Tab() as tab:
                ok, total, alerts = check_posted_comments(tab)
                recheck_done = True
                if failed_subs:
                    seen, logged_urls, replied = load_scan_filters(tab)
                    for sub in list(failed_subs):
                        try:
                            posts = fetch_new_listing_via_tab(tab, sub)
                            cands += filter_posts(sub, posts, seen, logged_urls, replied)
                            failed_subs.remove(sub)
                        except Exception as e:
                            log(f"r/{sub} Chrome 补抓也失败：{e}")
        except Exception as e:
            if not recheck_done:
                alerts = [f"⚠️ 回查异常（{type(e).__name__}），可会话触发补查"]
            log(f"回查/补抓异常：{e}")
    else:
        log("proxy 不可用，跳过回查（直抓被封的 sub 无法补抓，留待会话）")

    # 养 karma 期排序：有围观(hot)优先，其次关键词得分，再看新鲜度
    cands.sort(key=lambda c: (c.get("traction") != "hot", -c["score"], c["age_h"]))
    cands = cands[:MAX_CANDIDATES]
    if cands:
        with open(SEEN_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(c["id"] for c in cands) + "\n")

    head = (f"Reddit 哨兵：{ok}/{total} 条已核"
            if recheck_done else "Reddit 哨兵：已发评论回查待会话补（Chrome 未连）")
    lines = [head]
    if failed_subs:
        lines.append(f"  ⚠️ {len(failed_subs)} 个 sub 未抓到（直抓被封且 Chrome 补抓失败），粗筛不全")
    lines.extend(f"  {a}" for a in alerts)
    if cands:
        lines.append(f"  🎯 新候选 {len(cands)} 条（说「跑 Vlogara Reddit 日常」出草稿）：")
        for c in cands[:3]:
            fire = "🔥" if c.get("traction") == "hot" else ""
            lines.append(f"  · {fire}r/{c['sub']}「{c['title'][:40]}」{c['comments']}答/{c['age_h']}h {c['warn']}")
    elif recheck_done and not alerts:
        lines.append("  存活无异动，无新候选")
    write_feishu(lines)

    (OUT_DIR / f"reddit_sentinel_{TODAY}.json").write_text(
        json.dumps({"date": TODAY, "recheck_done": recheck_done,
                    "checked": ok, "total": total,
                    "alerts": alerts, "candidates": cands}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    log(f"完成：回查 {'done' if recheck_done else 'skip'} {ok}/{total}，"
        f"告警 {len(alerts)}，候选 {len(cands)}")


if __name__ == "__main__":
    main()
