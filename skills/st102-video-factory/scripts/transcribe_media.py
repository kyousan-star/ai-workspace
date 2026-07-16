#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import timecode

DEFAULT_MODEL = Path("/Users/lihuan/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120")


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a video to TXT, SRT, and JSON using faster-whisper.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()
    if not args.video.exists():
        raise SystemExit(f"Missing video: {args.video}")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit("faster-whisper is not installed in this Python environment.") from exc
    if not args.model.exists():
        raise SystemExit(f"Missing local model: {args.model}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(str(args.model), device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(args.video), beam_size=5, vad_filter=True)
    data = []
    for segment in segments:
        data.append({"start": round(segment.start, 3), "end": round(segment.end, 3), "text": segment.text.strip()})
    stem = args.video.stem
    (args.output_dir / f"{stem}.txt").write_text("\n".join(item["text"] for item in data) + "\n", encoding="utf-8")
    with (args.output_dir / f"{stem}.srt").open("w", encoding="utf-8") as handle:
        for index, item in enumerate(data, 1):
            handle.write(f"{index}\n{timecode(item['start'])} --> {timecode(item['end'])}\n{item['text']}\n\n")
    with (args.output_dir / f"{stem}.json").open("w", encoding="utf-8") as handle:
        json.dump({"language": info.language, "language_probability": info.language_probability, "segments": data}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(args.output_dir)


if __name__ == "__main__":
    main()
