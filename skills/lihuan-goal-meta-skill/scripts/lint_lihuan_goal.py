#!/usr/bin/env python3
"""Validate a Lihuan-style Codex /goal draft."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_GROUPS = [
    ("command", [r"^\s*/goal\b"]),
    ("verification", [r"验证[:：]", r"Verification[:：]"]),
    ("constraints", [r"约束[:：]", r"Constraints[:：]"]),
    ("boundaries", [r"边界[:：]", r"Boundaries[:：]"]),
    ("iteration", [r"迭代策略[:：]", r"Iteration policy[:：]"]),
    ("completion", [r"完成条件[:：]", r"Stop when[:：]"]),
    ("pause", [r"暂停条件[:：]", r"Pause if[:：]"]),
]

BAD_PATTERNS = [
    r"\[[^\]]+\]",
    r"<[^>]+>",
    r"\bTODO\b",
    r"\bTBD\b",
    r"待定",
    r"待补充",
    r"随便改",
    r"随意修改",
    r"make sure it works",
    r"edit anything",
    r"keep trying",
    r"直到满意",
    r"感觉可以",
]

EVIDENCE_PATTERNS = [
    r"运行|启动|打开|读取|核对|检查|验证|截图|日志|产物|文件|浏览器|移动端|表格|公式|图表|导出|outputs",
    r"\b(run|start|open|inspect|check|verify|screenshot|log|artifact|file|browser|mobile|formula|chart|export|outputs)\b",
]

LIHUAN_HELPFUL_PATTERNS = [
    r"事实|推断|建议|证据|风险|优先级|outputs|原始数据|口径|移动端",
]


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def marker_line(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(rf"^\s*{pattern}\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def lint(text: str, source: str) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []

    if re.search(r"^\s*/目标\b", text, flags=re.MULTILINE):
        errors.append(f"{source}: use `/goal`, not `/目标`")

    for name, patterns in REQUIRED_GROUPS:
        if not has_any(text, patterns):
            errors.append(f"{source}: missing required marker `{name}`")

    for pattern in BAD_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"{source}: vague or placeholder text matched `{pattern}`")

    goal_line = next((line.strip() for line in text.splitlines() if line.strip().startswith("/goal")), "")
    if goal_line and len(goal_line.removeprefix("/goal").strip()) < 24:
        errors.append(f"{source}: /goal outcome is too short")

    verification = marker_line(text, REQUIRED_GROUPS[1][1])
    if verification and not has_any(verification, EVIDENCE_PATTERNS):
        errors.append(f"{source}: verification lacks concrete evidence")

    for name, patterns in REQUIRED_GROUPS[1:]:
        content = marker_line(text, patterns)
        if content and len(content) < 14:
            errors.append(f"{source}: `{name}` content is too thin")

    if not has_any(text, LIHUAN_HELPFUL_PATTERNS):
        warnings.append(f"{source}: warning: consider adding Lihuan-specific evidence such as facts/inferences/actions, risks, metric definitions, outputs, raw data preservation, or mobile checks")

    return errors + warnings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: lint_lihuan_goal.py <goal-file> [<goal-file> ...]", file=sys.stderr)
        return 2

    all_messages: list[str] = []
    has_error = False
    for raw in argv[1:]:
        path = Path(raw)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"{path}: cannot read file: {exc}", file=sys.stderr)
            has_error = True
            continue
        messages = lint(text, str(path))
        for message in messages:
            if "warning:" not in message:
                has_error = True
        all_messages.extend(messages)

    for message in all_messages:
        print(message, file=sys.stderr if "warning:" not in message else sys.stdout)

    if has_error:
        return 1
    print("Lihuan goal lint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
