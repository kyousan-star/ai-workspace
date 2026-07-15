from __future__ import annotations

import hashlib
import json
import os
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class WorkbenchError(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat(timespec="milliseconds")


def encode_crockford(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        chars.append(CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid() -> str:
    timestamp_ms = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(10), "big")
    return encode_crockford(timestamp_ms, 10) + encode_crockford(randomness, 16)


def slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in cleaned.split("-") if part) or "unknown"


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_metadata(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        head = handle.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
            width, height = struct.unpack(">II", head[16:24])
            return {"format": "png", "width": width, "height": height}
        if head[:2] == b"\xff\xd8":
            handle.seek(2)
            while True:
                marker_start = handle.read(1)
                if not marker_start:
                    break
                if marker_start != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if not marker or marker in {b"\xd8", b"\xd9"}:
                    continue
                length_bytes = handle.read(2)
                if len(length_bytes) != 2:
                    break
                length = struct.unpack(">H", length_bytes)[0]
                if marker[0] in {
                    0xC0,
                    0xC1,
                    0xC2,
                    0xC3,
                    0xC5,
                    0xC6,
                    0xC7,
                    0xC9,
                    0xCA,
                    0xCB,
                    0xCD,
                    0xCE,
                    0xCF,
                }:
                    payload = handle.read(5)
                    if len(payload) != 5:
                        break
                    height, width = struct.unpack(">HH", payload[1:5])
                    return {"format": "jpeg", "width": width, "height": height}
                handle.seek(max(0, length - 2), 1)
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP" and head[12:16] == b"VP8X":
            width = 1 + int.from_bytes(head[24:27], "little")
            height = 1 + int.from_bytes(head[27:30], "little")
            return {"format": "webp", "width": width, "height": height}
    return {"format": path.suffix.lower().lstrip(".") or "unknown", "width": None, "height": None}


def technical_check(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    metadata = image_metadata(path)
    expected = contract.get("expected_output") or {}
    checks = []

    expected_format = str(expected.get("format") or "").lower().replace("jpg", "jpeg")
    actual_format = str(metadata["format"]).lower().replace("jpg", "jpeg")
    if expected_format:
        checks.append(
            {
                "name": "format",
                "passed": actual_format == expected_format,
                "expected": expected_format,
                "actual": actual_format,
            }
        )

    aspect = str(expected.get("aspect_ratio") or "")
    width = metadata.get("width")
    height = metadata.get("height")
    if aspect and width and height and ":" in aspect:
        left, right = aspect.split(":", 1)
        expected_ratio = float(left) / float(right)
        actual_ratio = width / height
        checks.append(
            {
                "name": "aspect_ratio",
                "passed": abs(actual_ratio - expected_ratio) <= 0.01,
                "expected": aspect,
                "actual": f"{width}:{height}",
            }
        )
    elif aspect:
        checks.append(
            {
                "name": "aspect_ratio",
                "passed": False,
                "expected": aspect,
                "actual": "unknown",
            }
        )

    min_width = expected.get("min_width")
    if min_width is not None:
        checks.append(
            {
                "name": "min_width",
                "passed": bool(width and width >= int(min_width)),
                "expected": int(min_width),
                "actual": width,
            }
        )

    passed = all(check["passed"] for check in checks) if checks else bool(width and height)
    return {"status": "passed" if passed else "failed", "metadata": metadata, "checks": checks}
