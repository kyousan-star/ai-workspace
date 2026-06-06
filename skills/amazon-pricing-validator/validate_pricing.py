"""
Amazon Price Plan Validator
用法：
  python validate_pricing.py --url "GOOGLE_SHEET_URL" --x 20 --list-price 35 --bfcm-target 22 --event LD
  python validate_pricing.py --file plan.csv --x 20 --list-price 35 --bfcm-target 22 --event BD

参数：
  --url          Google Sheet 链接（需设为"任何人可查看"）
  --file         本地 CSV 路径（二选一）
  --x            最低售价（成本底线）
  --list-price   List Price（锚点价）
  --bfcm-target  黑五/网一目标活动价
  --event        活动类型：BD / LD / PD（默认 LD）
  --output       输出 CSV 路径（可选，默认只打印终端报告）
"""

import argparse
import sys
import re
import csv
import io
from datetime import datetime, timedelta

try:
    import pandas as pd
except ImportError:
    print("缺少依赖：pip install pandas requests")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("缺少依赖：pip install requests")
    sys.exit(1)

# ── ANSI 颜色 ──────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def red(s):    return f"{RED}{s}{RESET}"
def green(s):  return f"{GREEN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"

# ── Google Sheet URL → CSV ────────────────────────────────
def sheet_url_to_csv_url(url: str) -> str:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        raise ValueError("无法解析 Google Sheet ID，请检查链接格式")
    sheet_id = m.group(1)
    gid_m = re.search(r"[?&]gid=(\d+)", url)
    gid = gid_m.group(1) if gid_m else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

def load_sheet(url: str) -> pd.DataFrame:
    csv_url = sheet_url_to_csv_url(url)
    resp = requests.get(csv_url, timeout=15)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))

def load_file(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

# ── 数据清洗 ──────────────────────────────────────────────
REQUIRED_COLS = ["week", "date_start", "list_price", "your_price",
                 "promo_type", "promo_price", "promo_days"]

def clean(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"表格缺少列：{missing}\n请参考模板：template.csv")

    df = df.dropna(subset=["week", "date_start"]).copy()
    df["date_start"] = pd.to_datetime(df["date_start"])
    df = df.sort_values("date_start").reset_index(drop=True)

    df["list_price"]  = pd.to_numeric(df["list_price"],  errors="coerce")
    df["your_price"]  = pd.to_numeric(df["your_price"],  errors="coerce")
    df["promo_price"] = pd.to_numeric(df["promo_price"], errors="coerce")
    df["promo_days"]  = pd.to_numeric(df["promo_days"],  errors="coerce").fillna(0).astype(int)
    df["promo_type"]  = df["promo_type"].fillna("none").str.lower().str.strip()

    # effective_price = 本周实际最低成交价
    df["effective_price"] = df.apply(
        lambda r: r["promo_price"] if pd.notna(r["promo_price"]) and r["promo_days"] > 0
                  else r["your_price"],
        axis=1
    )
    return df

# ── 滚动窗口计算 ──────────────────────────────────────────
def rolling_windows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)
    r90_promo = []
    r30_low   = []
    r60_low   = []
    was_price = []

    for i in range(n):
        current_date = df.loc[i, "date_start"]

        # 90 天窗口
        d90 = current_date - timedelta(days=90)
        mask90 = (df["date_start"] > d90) & (df["date_start"] <= current_date)
        subset90 = df.loc[mask90]

        promo_days_90 = subset90["promo_days"].sum()
        r90_promo.append(int(promo_days_90))

        # Was Price 估算：90天内非促销日的 your_price 中位数
        non_promo = subset90[subset90["promo_days"] == 0]["your_price"]
        wp = round(non_promo.median(), 2) if len(non_promo) > 0 else df.loc[i, "your_price"]
        was_price.append(wp)

        # 30 天最低
        d30 = current_date - timedelta(days=30)
        mask30 = (df["date_start"] > d30) & (df["date_start"] <= current_date)
        low30 = df.loc[mask30, "effective_price"].min()
        r30_low.append(round(low30, 2) if pd.notna(low30) else df.loc[i, "effective_price"])

        # 60 天最低
        d60 = current_date - timedelta(days=60)
        mask60 = (df["date_start"] > d60) & (df["date_start"] <= current_date)
        low60 = df.loc[mask60, "effective_price"].min()
        r60_low.append(round(low60, 2) if pd.notna(low60) else df.loc[i, "effective_price"])

    df["rolling_90d_promo_days"] = r90_promo
    df["promo_pct_90d"]          = (df["rolling_90d_promo_days"] / 90).round(3)
    df["rolling_30d_low"]        = r30_low
    df["rolling_60d_low"]        = r60_low
    df["was_price_est"]          = was_price
    return df

# ── BFCM 资格验证 ─────────────────────────────────────────
DISCOUNT_REQ = {
    "bd": {"ref": 0.15, "your_price": None, "was": 0.05},
    "ld": {"ref": 0.20, "your_price": None, "was": 0.05},
    "pd": {"ref": 0.15, "your_price": 0.20, "was": 0.05},
}

def check_eligibility(df: pd.DataFrame, list_price: float,
                      bfcm_target: float, event: str) -> pd.DataFrame:
    df = df.copy()
    req = DISCOUNT_REQ.get(event.lower(), DISCOUNT_REQ["ld"])

    issues_col = []
    eligible_col = []

    for _, r in df.iterrows():
        issues = []

        # 1. List Price 是否够高（目标价必须至少比参考价低 ref%）
        # 要求：bfcm_target ≤ L × (1 - ref)，即 L ≥ bfcm_target / (1 - ref)
        lp = r["list_price"] if pd.notna(r["list_price"]) else list_price
        min_lp_required = bfcm_target / (1 - req["ref"])
        if lp < min_lp_required - 0.01:
            issues.append(f"List Price({lp:.2f}) 不够高，需 ≥ {min_lp_required:.2f} 才能让目标价{bfcm_target}达到{req['ref']:.0%}折扣")

        # 2. Was Price
        if r["was_price_est"] * 0.95 < bfcm_target - 0.01:
            issues.append(f"Was Price 估算({r['was_price_est']:.2f})×95%={r['was_price_est']*0.95:.2f} < 目标价，Was Price 太低")

        # 3. 30天最低价
        if r["rolling_30d_low"] * 0.95 < bfcm_target - 0.01:
            issues.append(f"30天低价({r['rolling_30d_low']:.2f})×95%={r['rolling_30d_low']*0.95:.2f} < 目标价")

        # 4. 60天最低价（硬底线：活动价必须 ≤ 60天低价）
        if r["rolling_60d_low"] < bfcm_target - 0.01:
            issues.append(f"🚨 60天内曾出现 {r['rolling_60d_low']:.2f} < 目标价{bfcm_target}，活动必须报更低价")

        # 5. 促销频次
        if r["promo_pct_90d"] >= 0.50:
            issues.append(f"90天促销占比{r['promo_pct_90d']:.0%} ≥ 50%，Was Price 将被拉低")

        # 6. PD 额外：Your Price 折扣（目标价需比 Your Price 低 20%）
        if req["your_price"] and bfcm_target > r["your_price"] * (1 - req["your_price"]) + 0.01:
            issues.append(f"Your Price({r['your_price']:.2f})×{1-req['your_price']:.0%}={r['your_price']*(1-req['your_price']):.2f} < 目标价{bfcm_target}，折扣不足")

        issues_col.append("; ".join(issues) if issues else "")
        eligible_col.append("✅" if not issues else "❌")

    df["issues"]        = issues_col
    df["bfcm_eligible"] = eligible_col
    return df

# ── 终端报告 ──────────────────────────────────────────────
def print_report(df: pd.DataFrame, x: float, list_price: float,
                 bfcm_target: float, event: str):
    print()
    print(bold("=" * 72))
    print(bold(f"  Amazon 价格规划验证报告 — 活动类型：{event.upper()}"))
    print(bold(f"  最低售价 x={x} | List Price={list_price} | BFCM目标价={bfcm_target}"))
    print(bold("=" * 72))

    display_cols = ["week", "date_start", "your_price", "effective_price",
                    "promo_pct_90d", "rolling_30d_low", "rolling_60d_low",
                    "was_price_est", "bfcm_eligible"]

    header = f"{'周':>4}  {'日期':>10}  {'日常价':>6}  {'实效价':>6}  {'促销%':>5}  {'30d低':>6}  {'60d低':>6}  {'Was':>6}  {'资格':>5}  问题"
    print(header)
    print("-" * 120)

    for _, r in df.iterrows():
        promo_pct_str = f"{r['promo_pct_90d']:.0%}"
        eligible = r["bfcm_eligible"]
        issues = r["issues"]

        line = (f"{str(r['week']):>4}  "
                f"{str(r['date_start'].date()):>10}  "
                f"{r['your_price']:>6.2f}  "
                f"{r['effective_price']:>6.2f}  "
                f"{promo_pct_90d_colored(r['promo_pct_90d']):>5}  "
                f"{r['rolling_30d_low']:>6.2f}  "
                f"{rolling_60d_colored(r['rolling_60d_low'], bfcm_target):>6}  "
                f"{r['was_price_est']:>6.2f}  "
                f"{eligible:>5}")

        if issues:
            print(line + "  " + red(issues[:80]))
        else:
            print(line)

    total = len(df)
    ok    = (df["bfcm_eligible"] == "✅").sum()
    print()
    print(bold(f"  合格周数：{green(str(ok))}/{total}  |  "
               f"问题周数：{red(str(total-ok))}/{total}"))
    print(bold("=" * 72))
    print()

def promo_pct_90d_colored(pct: float) -> str:
    s = f"{pct:.0%}"
    if pct >= 0.50:
        return red(s)
    elif pct >= 0.40:
        return yellow(s)
    return green(s)

def rolling_60d_colored(val: float, target: float) -> str:
    s = f"{val:.2f}"
    return red(s) if val < target - 0.01 else s

# ── 主程序 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Amazon 价格规划验证器")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url",  help="Google Sheet 链接")
    src.add_argument("--file", help="本地 CSV 路径")
    parser.add_argument("--x",           type=float, required=True, help="最低售价（成本底线）")
    parser.add_argument("--list-price",  type=float, required=True, help="List Price 锚点价")
    parser.add_argument("--bfcm-target", type=float, required=True, help="黑五目标活动价")
    parser.add_argument("--event",       default="LD", choices=["BD","LD","PD","bd","ld","pd"])
    parser.add_argument("--output",      help="输出 CSV 路径（可选）")
    args = parser.parse_args()

    print(f"{CYAN}正在加载数据...{RESET}")
    if args.url:
        df = load_sheet(args.url)
    else:
        df = load_file(args.file)

    df = clean(df)
    df = rolling_windows(df)
    df = check_eligibility(df, args.list_price, args.bfcm_target, args.event)

    print_report(df, args.x, args.list_price, args.bfcm_target, args.event)

    if args.output:
        export_cols = ["week", "date_start", "list_price", "your_price",
                       "promo_type", "promo_price", "promo_days",
                       "effective_price", "rolling_90d_promo_days", "promo_pct_90d",
                       "rolling_30d_low", "rolling_60d_low", "was_price_est",
                       "bfcm_eligible", "issues"]
        df[export_cols].to_csv(args.output, index=False)
        print(f"{GREEN}报告已输出：{args.output}{RESET}")

if __name__ == "__main__":
    main()
