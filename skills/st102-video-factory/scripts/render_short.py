#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from _common import find_binary, load_json, next_versioned_path

FORBIDDEN = (
    "zero wobble",
    "no wobble",
    "1-second release",
    "1 second release",
    "works on uneven ground",
    "heavy duty",
    "windproof",
    "universal for all devices",
)


def escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def validate_manifest(payload: dict) -> None:
    required = ["content_id", "input", "start", "end", "output_dir", "output_name", "source_kind", "rights_status"]
    missing = [field for field in required if field not in payload]
    if missing:
        raise SystemExit(f"Manifest missing fields: {', '.join(missing)}")
    if float(payload["end"]) <= float(payload["start"]):
        raise SystemExit("Manifest end must be greater than start.")
    text = " ".join([payload.get("title", ""), payload.get("disclosure", ""), *payload.get("claims", [])]).lower()
    blocked = [claim for claim in FORBIDDEN if claim in text]
    if blocked:
        raise SystemExit(f"Forbidden claim(s): {', '.join(blocked)}")
    if payload.get("source_kind") == "sponsored_creator":
        if payload.get("rights_status") != "approved_cross_channel":
            raise SystemExit("Sponsored creator footage requires rights_status=approved_cross_channel before rendering.")
        if not payload.get("disclosure"):
            raise SystemExit("Sponsored creator footage requires a disclosure.")


def render(manifest_path: Path, mode: str) -> Path:
    payload = load_json(manifest_path)
    validate_manifest(payload)
    ffmpeg = find_binary("ffmpeg")
    if not ffmpeg:
        raise SystemExit("Independent ffmpeg is not available. Install or expose ffmpeg in PATH before rendering.")
    input_path = Path(payload["input"]).expanduser()
    if not input_path.exists():
        raise SystemExit(f"Missing input: {input_path}")
    campaign = Path(payload["output_dir"]).expanduser()
    output_dir = campaign / ("previews" if mode == "preview" else "finals")
    suffix = "preview.mp4" if mode == "preview" else "final.mp4"
    output = next_versioned_path(output_dir, payload["output_name"], suffix)
    width, height, crf = (720, 1280, 27) if mode == "preview" else (1080, 1920, 20)
    filters = [f"scale={width}:{height}:force_original_aspect_ratio=increase", f"crop={width}:{height}"]
    captions = payload.get("captions_srt")
    if captions:
        captions_path = Path(captions).expanduser()
        if not captions_path.exists():
            raise SystemExit(f"Missing captions: {captions_path}")
        filters.append(
            "subtitles='{}':force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101818,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=170'".format(
                escape_filter_path(captions_path)
            )
        )
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
        "-ss", str(float(payload["start"])), "-to", str(float(payload["end"])),
        "-i", str(input_path),
        "-vf", ",".join(filters),
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one approved ST102 cut manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--mode", choices=["preview", "final"], default="preview")
    args = parser.parse_args()
    print(render(args.manifest.resolve(), args.mode))


if __name__ == "__main__":
    main()
