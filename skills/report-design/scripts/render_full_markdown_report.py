#!/usr/bin/env python3
import html
import re
import sys
from datetime import date
from pathlib import Path


def esc(value):
    return html.escape(str(value), quote=True)


def slugify(text, used):
    base = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text).strip("-").lower()
    if not base:
        base = "section"
    slug = base
    index = 2
    while slug in used:
        slug = f"{base}-{index}"
        index += 1
    used.add(slug)
    return slug


def inline_md(text):
    placeholders = []

    def keep_code(match):
        placeholders.append(f"<code>{esc(match.group(1))}</code>")
        return f"@@CODE{len(placeholders) - 1}@@"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(
        r"(https?://[^\s<]+)",
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    for i, value in enumerate(placeholders):
        text = text.replace(f"@@CODE{i}@@", value)
    return text


def cell_class(text):
    raw = str(text)
    classes = []
    if any(token in raw for token in ["✅", "通过", "GO", "Go"]):
        classes.append("cell-good")
    if any(token in raw for token in ["❌", "否决", "NO-GO", "No-Go"]):
        classes.append("cell-bad")
    if any(token in raw for token in ["⚠️", "HOLD", "Hold", "中"]):
        classes.append("cell-warn")
    if re.search(r"-\d+(?:\.\d+)?%|-\\$", raw):
        classes.append("cell-bad")
    return " ".join(classes)


def is_table_separator(line):
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def is_table_start(lines, i):
    return i + 1 < len(lines) and "|" in lines[i] and is_table_separator(lines[i + 1])


def split_table_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_table(lines):
    header = split_table_row(lines[0])
    rows = [split_table_row(line) for line in lines[2:] if "|" in line]
    out = ['<div class="table-wrap"><table>']
    out.append("<thead><tr>" + "".join(f"<th>{inline_md(cell)}</th>" for cell in header) + "</tr></thead>")
    out.append("<tbody>")
    for row in rows:
        if len(row) < len(header):
            row += [""] * (len(header) - len(row))
        cells = []
        for cell in row[: len(header)]:
            cls = cell_class(cell)
            attr = f' class="{cls}"' if cls else ""
            cells.append(f"<td{attr}>{inline_md(cell)}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def parse_tables(lines):
    tables = []
    i = 0
    current_heading = ""
    while i < len(lines):
        heading = re.match(r"^(#{1,6})\s+(.+)$", lines[i].strip())
        if heading:
            current_heading = heading.group(2).strip()
        if is_table_start(lines, i):
            block = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip():
                block.append(lines[i])
                i += 1
            header = split_table_row(block[0])
            rows = [split_table_row(line) for line in block[2:]]
            tables.append({"heading": current_heading, "header": header, "rows": rows})
            continue
        i += 1
    return tables


def table_by_heading(tables, keyword):
    for table in tables:
        if keyword in table["heading"]:
            return table
    return None


def kv_from_table(table):
    result = {}
    if not table:
        return result
    for row in table["rows"]:
        if len(row) >= 2:
            key = re.sub(r"\*+", "", row[0]).strip()
            value = re.sub(r"\*+", "", row[1]).strip()
            result[key] = value
    return result


def number_from_text(value):
    match = re.search(r"-?\d+(?:\.\d+)?", value or "")
    return float(match.group(0)) if match else None


def extract_dashboard(md, tables):
    summary = kv_from_table(table_by_heading(tables, "执行摘要"))
    score = summary.get("综合评分", "")
    decision = summary.get("决策", "")
    status = "yellow"
    if re.search(r"NO|否决|red", decision, re.I):
        status = "red"
    elif re.search(r"\bGO\b|通过|green", decision, re.I):
        status = "green"

    meta = {}
    for line in md.splitlines():
        match = re.match(r">\s+\*\*(.+?)\*\*:\s*(.+)$", line.strip())
        if match:
            meta[match.group(1)] = match.group(2)

    kpi_keys = ["品类年销售额", "年销量", "同期对比 (2025.03-12 vs 2024.03-12)", "CR3 / CR5 / CR10", "综合评分", "决策"]
    kpis = []
    for key in kpi_keys:
        if key in summary:
            kpis.append((key, summary[key]))

    findings = []
    patterns = [
        r"\*\*关键信号\*\*:\s*(.+)",
        r"\*\*解读\*\*:\s*(.+老品垄断.+)",
        r"1\.\s+\*\*可互换刀头\*\*是最大的机会点\(.+",
        r"\*\*理由\*\*:\s*(.+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, md):
            findings.append(re.sub(r"\*+", "", match.group(0)).strip())
            break

    score_table = table_by_heading(tables, "五维度评分卡")
    score_items = []
    if score_table:
        for row in score_table["rows"]:
            if len(row) >= 3 and "综合" not in row[0]:
                val = number_from_text(row[2])
                if val is not None:
                    score_items.append((re.sub(r"\*+", "", row[0]).strip(), val, row[-1] if row else ""))

    gate_table = table_by_heading(tables, "利润 Gate")
    gate_items = []
    if gate_table:
        for row in gate_table["rows"]:
            if len(row) >= 5:
                val = number_from_text(row[3])
                if val is not None:
                    gate_items.append((row[0], val, row[4]))

    return {
        "title": re.search(r"^#\s+(.+)$", md, re.M).group(1) if re.search(r"^#\s+(.+)$", md, re.M) else "Amazon Report",
        "meta": meta,
        "summary": summary,
        "status": status,
        "score": score,
        "decision": decision,
        "kpis": kpis,
        "findings": findings[:4],
        "score_items": score_items,
        "gate_items": gate_items,
    }


def render_bar_items(items, value_suffix=""):
    if not items:
        return ""
    max_abs = max(abs(item[1]) for item in items) or 1
    rows = []
    for label, value, note in items:
        width = max(4, min(100, abs(value) / max_abs * 100))
        cls = "negative" if value < 0 else "positive"
        rows.append(
            f'<div class="bar-row"><div class="bar-label">{inline_md(label)}</div>'
            f'<div class="bar-track"><div class="bar-fill {cls}" style="width:{width:.1f}%"></div></div>'
            f'<div class="bar-value">{esc(value)}{value_suffix}</div><div class="bar-note">{inline_md(note)}</div></div>'
        )
    return "\n".join(rows)


def markdown_to_html(md):
    lines = md.splitlines()
    used = set()
    toc = []
    body = []
    i = 0
    first_h1_skipped = False
    paragraph = []

    def flush_paragraph():
        if paragraph:
            body.append(f"<p>{inline_md(' '.join(paragraph).strip())}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if level == 1 and not first_h1_skipped:
                first_h1_skipped = True
                i += 1
                continue
            hid = slugify(re.sub(r"<[^>]+>", "", text), used)
            if level <= 3:
                toc.append((level, text, hid))
            body.append(f'<h{level} id="{hid}">{inline_md(text)}</h{level}>')
            i += 1
            continue

        if is_table_start(lines, i):
            flush_paragraph()
            block = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip():
                block.append(lines[i])
                i += 1
            body.append(render_table(block))
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            body.append('<div class="source-meta">' + "".join(f"<p>{inline_md(q)}</p>" for q in quote) + "</div>")
            continue

        if stripped in {"---", "***"}:
            flush_paragraph()
            body.append("<hr>")
            i += 1
            continue

        if re.match(r"^[-*]\s+", stripped):
            flush_paragraph()
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            body.append("<ul>" + "".join(f"<li>{inline_md(item)}</li>" for item in items) + "</ul>")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            body.append("<ol>" + "".join(f"<li>{inline_md(item)}</li>" for item in items) + "</ol>")
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    return toc, "\n".join(body)


def render(md):
    lines = md.splitlines()
    tables = parse_tables(lines)
    dash = extract_dashboard(md, tables)
    toc, body = markdown_to_html(md)
    toc_html = "\n".join(
        f'<a class="toc-l{level}" href="#{hid}">{inline_md(text)}</a>' for level, text, hid in toc
    )
    kpi_html = "\n".join(
        f'<section class="kpi"><div class="kpi-label">{inline_md(k)}</div><div class="kpi-value">{inline_md(v)}</div></section>'
        for k, v in dash["kpis"]
    )
    findings_html = "\n".join(f"<li>{inline_md(item)}</li>" for item in dash["findings"])
    generated = date.today().isoformat()

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(dash["title"])}</title>
  <style>
    :root {{
      --bg: #f4f6f8;
      --paper: #fff;
      --ink: #18212f;
      --muted: #657282;
      --line: #dce3ea;
      --blue: #235b8f;
      --green: #1f7a4d;
      --yellow: #a96d00;
      --red: #b9342c;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.58;
      font-size: 15px;
    }}
    .layout {{ display: grid; grid-template-columns: 260px minmax(0, 1fr); max-width: 1380px; margin: 0 auto; }}
    aside {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
      padding: 22px 18px;
      border-right: 1px solid var(--line);
      background: #f9fafb;
    }}
    aside strong {{ display: block; margin-bottom: 12px; font-size: 14px; }}
    aside a {{ display: block; color: var(--muted); text-decoration: none; padding: 5px 0; border-radius: 4px; }}
    aside a:hover {{ color: var(--blue); }}
    .toc-l1 {{ font-weight: 800; color: var(--ink); margin-top: 8px; }}
    .toc-l2 {{ padding-left: 10px; }}
    .toc-l3 {{ padding-left: 22px; font-size: 13px; }}
    main {{ min-width: 0; padding: 28px 30px 52px; }}
    .hero {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 18px;
      box-shadow: 0 12px 32px rgba(18, 31, 48, 0.06);
    }}
    .hero-top {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: start; }}
    h1, h2, h3, h4 {{ letter-spacing: 0; line-height: 1.25; }}
    h1 {{ margin: 0 0 10px; font-size: 30px; }}
    h2 {{ margin: 34px 0 14px; padding-top: 8px; font-size: 22px; border-top: 1px solid var(--line); }}
    h3 {{ margin: 24px 0 10px; font-size: 18px; }}
    h4 {{ margin: 18px 0 8px; font-size: 16px; }}
    p {{ margin: 8px 0; }}
    .sub {{ color: var(--muted); font-size: 13px; }}
    .badge {{
      min-width: 112px;
      border: 1px solid currentColor;
      border-radius: 6px;
      padding: 8px 12px;
      text-align: center;
      font-weight: 800;
    }}
    .badge.yellow {{ color: var(--yellow); }}
    .badge.red {{ color: var(--red); }}
    .badge.green {{ color: var(--green); }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin: 18px 0; }}
    .kpi {{ border: 1px solid var(--line); border-top: 4px solid var(--blue); border-radius: 7px; padding: 12px; min-height: 94px; background: #fff; }}
    .kpi-label {{ color: var(--muted); font-size: 12px; margin-bottom: 7px; }}
    .kpi-value {{ font-size: 21px; font-weight: 850; }}
    .dashboard-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px; }}
    .panel {{ border: 1px solid var(--line); border-radius: 8px; padding: 16px; background: #fff; }}
    .panel h2 {{ border: 0; margin: 0 0 12px; padding: 0; font-size: 17px; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(130px, 210px) 1fr 64px minmax(120px, 220px); gap: 9px; align-items: center; font-size: 13px; margin: 9px 0; }}
    .bar-track {{ height: 11px; border-radius: 999px; background: #edf1f5; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--blue); }}
    .bar-fill.negative {{ background: var(--red); }}
    .bar-fill.positive {{ background: var(--green); }}
    .bar-value {{ font-weight: 800; text-align: right; }}
    .bar-note {{ color: var(--muted); }}
    .content {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 24px 28px;
      box-shadow: 0 8px 24px rgba(18, 31, 48, 0.04);
    }}
    .source-meta {{ border-left: 4px solid var(--blue); background: #f6f9fc; padding: 10px 14px; margin: 12px 0; color: var(--muted); }}
    .table-wrap {{ overflow-x: auto; margin: 12px 0 18px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
    table {{ width: 100%; min-width: 680px; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; color: #3b4858; font-weight: 800; position: sticky; top: 0; }}
    tr:last-child td {{ border-bottom: 0; }}
    .cell-good {{ color: var(--green); font-weight: 800; }}
    .cell-bad {{ color: var(--red); font-weight: 800; }}
    .cell-warn {{ color: var(--yellow); font-weight: 800; }}
    ul, ol {{ margin: 8px 0 14px; padding-left: 22px; }}
    li {{ margin: 5px 0; }}
    strong {{ font-weight: 850; }}
    a {{ color: var(--blue); }}
    hr {{ border: 0; border-top: 1px solid var(--line); margin: 22px 0; }}
    footer {{ color: var(--muted); font-size: 12px; margin-top: 18px; }}
    @media (max-width: 980px) {{
      .layout {{ display: block; }}
      aside {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      main {{ padding: 18px 14px 36px; }}
      .hero-top, .dashboard-grid {{ grid-template-columns: 1fr; }}
      .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .bar-row {{ grid-template-columns: 1fr; }}
      .bar-value {{ text-align: left; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <strong>报告目录</strong>
      {toc_html}
    </aside>
    <main>
      <section class="hero">
        <div class="hero-top">
          <div>
            <h1>{inline_md(dash["title"])}</h1>
            <div class="sub">生成日期 {generated} · 完整内容由 Markdown 保留渲染</div>
          </div>
          <div class="badge {dash["status"]}">{inline_md(dash["decision"] or dash["score"] or "Review")}</div>
        </div>
        <div class="kpi-grid">{kpi_html}</div>
        <div class="dashboard-grid">
          <section class="panel">
            <h2>评分看板</h2>
            {render_bar_items(dash["score_items"])}
          </section>
          <section class="panel">
            <h2>利润 Gate</h2>
            {render_bar_items(dash["gate_items"], "%")}
          </section>
        </div>
        <section class="panel" style="margin-top:14px">
          <h2>首屏关键判断</h2>
          <ul>{findings_html}</ul>
        </section>
      </section>
      <article class="content">
        {body}
      </article>
      <footer>Rendered with amazon-report-design full markdown renderer. Original content is preserved; dashboard is an added reading layer.</footer>
    </main>
  </div>
</body>
</html>"""


def main():
    if len(sys.argv) != 3:
        print("Usage: render_full_markdown_report.py source.md output.html", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    md = src.read_text(encoding="utf-8")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(render(md), encoding="utf-8")
    print(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
