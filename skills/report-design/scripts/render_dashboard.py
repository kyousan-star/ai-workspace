#!/usr/bin/env python3
import html
import json
import sys
from datetime import date
from pathlib import Path


STATUS_LABELS = {
    "red": "红灯",
    "yellow": "黄灯",
    "green": "绿灯",
}


def esc(value):
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def status(value):
    value = str(value or "yellow").lower()
    return value if value in {"red", "yellow", "green"} else "yellow"


def pct_width(value, max_value):
    try:
        v = float(value)
        m = float(max_value) if max_value else 1
        return max(3, min(100, round(v / m * 100, 1)))
    except Exception:
        return 12


def render_kpis(kpis):
    cards = []
    for item in kpis or []:
        st = status(item.get("status"))
        cards.append(f"""
        <section class="kpi {st}">
          <div class="kpi-label">{esc(item.get("label"))}</div>
          <div class="kpi-value">{esc(item.get("value"))}</div>
          <div class="kpi-meta">
            <span>{esc(item.get("delta"))}</span>
            <span>{esc(item.get("note"))}</span>
          </div>
        </section>""")
    return "\n".join(cards)


def render_charts(charts):
    blocks = []
    for chart in charts or []:
        items = chart.get("items") or []
        max_value = max([float(i.get("value") or 0) for i in items if isinstance(i.get("value"), (int, float))] or [1])
        rows = []
        for item in items[:12]:
            width = pct_width(item.get("value"), max_value)
            rows.append(f"""
            <div class="bar-row">
              <div class="bar-label">{esc(item.get("label"))}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div>
              <div class="bar-value">{esc(item.get("value"))}</div>
              <div class="bar-note">{esc(item.get("note"))}</div>
            </div>""")
        blocks.append(f"""
        <section class="panel">
          <h2>{esc(chart.get("title"))}</h2>
          <div class="bar-list">{''.join(rows)}</div>
        </section>""")
    return "\n".join(blocks)


def render_findings(findings):
    rows = []
    for item in findings or []:
        st = status(item.get("severity"))
        rows.append(f"""
        <article class="finding {st}">
          <div class="flag">{STATUS_LABELS.get(st, "黄灯")}</div>
          <div>
            <h3>{esc(item.get("title"))}</h3>
            <p class="evidence">{esc(item.get("evidence"))}</p>
            <p>{esc(item.get("impact"))}</p>
          </div>
        </article>""")
    return "\n".join(rows)


def render_actions(actions):
    rows = []
    for item in actions or []:
        rows.append(f"""
        <tr>
          <td>{esc(item.get("priority"))}</td>
          <td>{esc(item.get("owner"))}</td>
          <td>{esc(item.get("action"))}</td>
          <td>{esc(item.get("metric"))}</td>
          <td>{esc(item.get("due"))}</td>
        </tr>""")
    return "\n".join(rows)


def render_risks(risks):
    return "\n".join(f"<li>{esc(risk)}</li>" for risk in risks or [])


def render(data):
    st = status(data.get("status"))
    generated = date.today().isoformat()
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(data.get("title") or "Amazon Report Dashboard")}</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --ink: #17202a;
      --muted: #687383;
      --line: #dfe4ea;
      --panel: #ffffff;
      --red: #c9332b;
      --yellow: #b77b00;
      --green: #177245;
      --blue: #225d9c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.45;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 22px 44px; }}
    header {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: end;
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 20px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 6px; font-size: 15px; letter-spacing: 0; }}
    p {{ margin: 0; }}
    .sub {{ color: var(--muted); font-size: 14px; }}
    .status {{
      border: 1px solid currentColor;
      border-radius: 6px;
      padding: 8px 12px;
      font-weight: 700;
      min-width: 86px;
      text-align: center;
    }}
    .status.red {{ color: var(--red); }}
    .status.yellow {{ color: var(--yellow); }}
    .status.green {{ color: var(--green); }}
    .headline {{
      background: var(--panel);
      border-left: 5px solid var(--blue);
      padding: 16px 18px;
      margin-bottom: 18px;
      font-size: 18px;
      font-weight: 700;
    }}
    .grid {{ display: grid; gap: 14px; }}
    .kpis {{ grid-template-columns: repeat(6, minmax(0, 1fr)); margin-bottom: 18px; }}
    .kpi, .panel, .finding {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .kpi {{ padding: 14px; min-height: 116px; border-top: 4px solid var(--line); }}
    .kpi.red {{ border-top-color: var(--red); }}
    .kpi.yellow {{ border-top-color: var(--yellow); }}
    .kpi.green {{ border-top-color: var(--green); }}
    .kpi-label {{ color: var(--muted); font-size: 13px; margin-bottom: 8px; }}
    .kpi-value {{ font-size: 25px; font-weight: 800; margin-bottom: 8px; }}
    .kpi-meta {{ color: var(--muted); font-size: 12px; display: grid; gap: 3px; }}
    .two {{ grid-template-columns: 1.15fr .85fr; align-items: start; }}
    .panel {{ padding: 18px; margin-bottom: 14px; }}
    .bar-list {{ display: grid; gap: 10px; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(120px, 210px) 1fr 72px minmax(100px, 180px); gap: 10px; align-items: center; font-size: 13px; }}
    .bar-track {{ height: 12px; background: #edf1f5; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--blue); }}
    .bar-value {{ font-weight: 700; text-align: right; }}
    .bar-note {{ color: var(--muted); }}
    .finding {{ display: grid; grid-template-columns: 64px 1fr; gap: 12px; padding: 14px; margin-bottom: 10px; }}
    .flag {{ font-size: 12px; font-weight: 800; align-self: start; text-align: center; padding: 5px 6px; border-radius: 5px; color: #fff; }}
    .finding.red .flag {{ background: var(--red); }}
    .finding.yellow .flag {{ background: var(--yellow); }}
    .finding.green .flag {{ background: var(--green); }}
    .evidence {{ color: var(--muted); font-size: 13px; margin-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: var(--panel); }}
    th, td {{ text-align: left; padding: 10px 9px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 700; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin: 7px 0; }}
    footer {{ color: var(--muted); font-size: 12px; margin-top: 22px; }}
    @media (max-width: 960px) {{
      header, .two {{ grid-template-columns: 1fr; }}
      .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .bar-value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div>
        <h1>{esc(data.get("title") or "Amazon Report Dashboard")}</h1>
        <div class="sub">{esc(data.get("subtitle"))} · {esc(data.get("date_range"))}</div>
      </div>
      <div class="status {st}">{STATUS_LABELS.get(st, "黄灯")}</div>
    </header>
    <section class="headline">{esc(data.get("headline"))}</section>
    <section class="grid kpis">{render_kpis(data.get("kpis"))}</section>
    <section class="grid two">
      <div>
        {render_charts(data.get("charts"))}
        <section class="panel">
          <h2>行动计划</h2>
          <table>
            <thead><tr><th>优先级</th><th>负责人</th><th>动作</th><th>验证指标</th><th>时间</th></tr></thead>
            <tbody>{render_actions(data.get("actions"))}</tbody>
          </table>
        </section>
      </div>
      <div>
        <section class="panel">
          <h2>关键发现</h2>
          {render_findings(data.get("findings"))}
        </section>
        <section class="panel">
          <h2>风险与口径</h2>
          <ul>{render_risks(data.get("risks"))}</ul>
        </section>
      </div>
    </section>
    <footer>Generated {generated}. Figures should retain their original data source and calculation base.</footer>
  </main>
</body>
</html>"""


def main():
    if len(sys.argv) != 3:
        print("Usage: render_dashboard.py input.json output.html", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    data = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(data), encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
