#!/usr/bin/env python3
"""Vlogara Reddit 哨兵 — 挂在卖家脉搏晨报里的每日只读巡检。

做三件事（全部只读，不发布任何内容）：
1. 回查：逐条刷新已发评论的分数/回复数，回填 reddit_engagement_log.csv
2. 告警：评论疑似被删、分数为负、出现新回复 → 进飞书告警行
3. 补弹粗筛：扫目标 sub 的 new 页，按关键词粗筛 <48h 且回答少的候选帖
   （只筛不判断，正式判断和草稿在会话「跑 Vlogara Reddit 日常」里做）

依赖 web-access skill 的 CDP proxy（localhost:3456，走本机 Chrome 登录态）。
Chrome/代理不可用时降级：飞书行写"哨兵未跑"，不影响晨报主体。

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


# ── 2. 候选粗筛 ──────────────────────────────────────────────────────────────

SCAN_SUB_JS = """
(() => {
  const posts = [...document.querySelectorAll(".thing.link")]
    .filter(el => el.getAttribute("data-promoted") !== "true")
    .map(el => ({
      id: el.getAttribute("data-fullname"),
      title: el.querySelector("a.title")?.textContent || "",
      url: el.querySelector("a.comments")?.href || "",
      comments: parseInt((el.querySelector("a.comments")?.textContent || "0").replace(/\\D/g, "") || "0", 10),
      ts: parseInt(el.getAttribute("data-timestamp") || "0", 10)
    }));
  return JSON.stringify(posts);
})()
"""


def scan_candidates(tab: Tab):
    seen = set()
    if SEEN_FILE.exists():
        seen = set(SEEN_FILE.read_text().split())
    logged_urls = " ".join(r.get("thread_url", "") for r in csv.DictReader(open(LOG_CSV, encoding="utf-8")))

    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    candidates = []
    for sub in SCAN_SUBS:
        tab.goto(f"https://old.reddit.com/r/{sub}/new/")
        try:
            posts = json.loads(tab.eval(SCAN_SUB_JS) or "[]")
        except (TypeError, json.JSONDecodeError):
            log(f"r/{sub} 解析失败，跳过")
            continue
        for p in posts:
            if not p["id"] or p["id"] in seen:
                continue
            age_h = (now_ms - p["ts"]) / 3600_000 if p["ts"] else 999
            if age_h > FRESH_HOURS or p["comments"] >= MAX_EXISTING_COMMENTS:
                continue
            if p["url"].split("?")[0].rstrip("/") in logged_urls:
                continue
            t = " " + p["title"].lower() + " "
            hit_clusters = [c for c, kws in CLUSTERS.items() if any(k in t for k in kws)]
            if not hit_clusters:
                continue
            score = len(hit_clusters) + sum(1 for q in QUESTION_HINTS if q in t)
            warn = "⚠️红线sub" if (sub == REDLINE_SUB and "簇1-便宜三脚架" in hit_clusters) else ""
            candidates.append({
                "sub": sub, "id": p["id"], "title": p["title"].strip()[:80],
                "url": p["url"], "comments": p["comments"],
                "age_h": round(age_h, 1), "clusters": hit_clusters,
                "score": score, "warn": warn,
            })
    candidates.sort(key=lambda c: (-c["score"], c["age_h"]))
    top = candidates[:MAX_CANDIDATES]
    if top:
        with open(SEEN_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(c["id"] for c in top) + "\n")
    return top


# ── 输出 ─────────────────────────────────────────────────────────────────────

def write_feishu(lines):
    FEISHU_TXT.write_text(f"DATE:{TODAY}\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUT_DIR.mkdir(exist_ok=True)
    if not ensure_proxy():
        write_feishu(["Reddit 哨兵：Chrome/代理不可用，今日未巡检（不影响发帖，可会话触发补查）"])
        log("代理不可用，降级退出")
        return

    try:
        with Tab() as tab:
            ok, total, alerts = check_posted_comments(tab)
            cands = scan_candidates(tab)
    except Exception as e:
        write_feishu([f"Reddit 哨兵：巡检异常（{type(e).__name__}: {e}），可会话触发补查"])
        log(f"异常: {e}")
        return

    lines = []
    if not alerts and not cands:
        lines.append(f"Reddit 哨兵：{ok}/{total} 条存活无异动，无新候选")
    else:
        lines.append(f"Reddit 哨兵：{ok}/{total} 条已核")
        lines.extend(f"  {a}" for a in alerts)
        if cands:
            lines.append(f"  🎯 新候选 {len(cands)} 条（说「跑 Vlogara Reddit 日常」出草稿）：")
            for c in cands[:3]:
                lines.append(f"  · r/{c['sub']}「{c['title'][:40]}」{c['comments']}答/{c['age_h']}h {c['warn']}")
    write_feishu(lines)

    (OUT_DIR / f"reddit_sentinel_{TODAY}.json").write_text(
        json.dumps({"date": TODAY, "checked": ok, "total": total,
                    "alerts": alerts, "candidates": cands}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    log(f"完成：核查 {ok}/{total}，告警 {len(alerts)}，候选 {len(cands)}")


if __name__ == "__main__":
    main()
