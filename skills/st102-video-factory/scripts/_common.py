#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".webm"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_project(project_root: Path) -> dict[str, Any]:
    config_path = project_root / "project.yaml"
    if not config_path.exists():
        raise SystemExit(f"Missing project config: {config_path}")
    return load_json(config_path)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def find_binary(name: str) -> str | None:
    return shutil.which(name)


def probe_video(path: Path) -> dict[str, Any]:
    ffprobe = find_binary("ffprobe")
    if ffprobe:
        command = [
            ffprobe,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration:stream=width,height,codec_name",
            "-of", "json",
            str(path),
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            payload = json.loads(result.stdout)
            stream = (payload.get("streams") or [{}])[0]
            duration = (payload.get("format") or {}).get("duration", "")
            return {
                "duration": round(float(duration), 3) if duration else "",
                "width": stream.get("width", ""),
                "height": stream.get("height", ""),
                "codec": stream.get("codec_name", ""),
                "probe_status": "ok",
            }
        except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError):
            pass

    ffmpeg = find_binary("ffmpeg")
    if not ffmpeg:
        return {"duration": "", "width": "", "height": "", "codec": "", "probe_status": "ffmpeg_missing"}
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    diagnostic = result.stderr
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", diagnostic)
    video_match = re.search(r"Video:\s*([^,\s]+).*?(\d{2,5})x(\d{2,5})", diagnostic)
    if not video_match:
        return {"duration": "", "width": "", "height": "", "codec": "", "probe_status": "ffmpeg_probe_failed"}
    duration: float | str = ""
    if duration_match:
        hours, minutes, seconds = duration_match.groups()
        duration = round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)
    return {
        "duration": duration,
        "width": int(video_match.group(2)),
        "height": int(video_match.group(3)),
        "codec": video_match.group(1),
        "probe_status": "ok_ffmpeg_fallback",
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def next_versioned_path(directory: Path, stem: str, suffix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for version in range(1, 1000):
        candidate = directory / f"{stem}_v{version:02d}_{suffix}"
        if not candidate.exists():
            return candidate
    raise SystemExit(f"No version slot available for {stem} in {directory}")


def timecode(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
