#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "claude" / "pinterest-assets" / "blog9-vt101-20260710"
BLOG_URL = "https://vlogara.com/blogs/news/phone-vlogging-kit-checklist-light-mic-tripod-mounts"
CAMPAIGN = "pinterest_blog9_vt101_202607"


ASSETS = [
    {
        "asset_id": "pin_blog_vt101_checklist_01",
        "title": "Phone vlogging kit checklist",
        "subtitle": "Light, mic, tripod, mounts, remote, and carry bag in one setup.",
        "source": "AMZ 图片/VT101/主图/主图1.jpg",
        "description": "A practical phone vlogging kit checklist for solo creators choosing lights, microphones, tripod support, mounts, adapters, and carry bag.",
    },
    {
        "asset_id": "pin_blog_vt101_checklist_02",
        "title": "What should be in a vlogging kit?",
        "subtitle": "Start with framing, lighting, audio, mounting, and faster repeat setup.",
        "source": "AMZ 图片/VT101/主图/主图9.jpg",
        "description": "Use this checklist before buying a phone vlogging kit so you do not miss lights, microphones, mounts, receiver, cables, remote, or storage.",
    },
    {
        "asset_id": "pin_blog_vt101_checklist_03",
        "title": "Better phone audio for solo videos",
        "subtitle": "Wireless microphones help when the phone is across the room.",
        "source": "AMZ 图片/VT101/主图/主图3.jpg",
        "description": "Phone vlogging kit checklist with notes on wireless microphones, receivers, adapters, and creator setups for talking videos and tutorials.",
    },
    {
        "asset_id": "pin_blog_vt101_checklist_04",
        "title": "Lighting matters when the room is not ready",
        "subtitle": "Fill lights make bedrooms, kitchens, and desks easier to film.",
        "source": "AMZ 图片/VT101/主图/主图7.jpg",
        "description": "Checklist for choosing a phone vlogging kit with fill lights, microphones, tripod support, mounts, remote control, and carry bag.",
    },
    {
        "asset_id": "pin_blog_vt101_checklist_05",
        "title": "All-in-one creator kit or separate gear?",
        "subtitle": "Choose less friction when you need a setup you can repeat every day.",
        "source": "AMZ 图片/VT101/主图/主图8.jpg",
        "description": "Compare buying separate creator gear with an all-in-one phone vlogging kit for faster solo filming, travel clips, livestreams, and tutorials.",
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width_chars: int, line_gap: int, fill: str, fnt: ImageFont.FreeTypeFont) -> int:
    x, y = xy
    for line in wrap(text, width_chars):
        draw.text((x, y), line, fill=fill, font=fnt)
        bbox = draw.textbbox((x, y), line, font=fnt)
        y += bbox[3] - bbox[1] + line_gap
    return y


def make_pin(asset: dict[str, str]) -> Path:
    src = ROOT / asset["source"]
    im = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", (1000, 1500), "#f6f3ec")
    draw = ImageDraw.Draw(canvas)

    # Product-photo area: crop to Pinterest-friendly upper hero, preserving real product shape.
    target_w, target_h = 880, 930
    scale = max(target_w / im.width, target_h / im.height)
    resized = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left = (resized.width - target_w) // 2
    top = max(0, (resized.height - target_h) // 2 - 30)
    crop = resized.crop((left, top, left + target_w, top + target_h))
    canvas.paste(crop, (60, 56))

    # Text band.
    draw.rectangle((60, 1030, 940, 1440), fill="#171717")
    draw.rectangle((60, 1010, 940, 1030), fill="#c9512f")
    draw.text((100, 1070), "VLOGARA GUIDE", fill="#f0d7b7", font=font(30, True))
    y = draw_wrapped(draw, asset["title"], (100, 1120), 20, 10, "#ffffff", font(58, True))
    y += 12
    draw_wrapped(draw, asset["subtitle"], (100, y), 38, 7, "#f4efe7", font(28))
    draw.text((100, 1386), "Read the checklist at vlogara.com", fill="#f0d7b7", font=font(26, True))

    out_path = OUT_DIR / f'{asset["asset_id"]}.jpg'
    canvas.save(out_path, quality=92, optimize=True)
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in ASSETS:
        path = make_pin(asset)
        utm = f"{BLOG_URL}?utm_source=pinterest&utm_medium=organic&utm_campaign={CAMPAIGN}&utm_content={asset['asset_id']}"
        rows.append(
            {
                "asset_id": asset["asset_id"],
                "pin_title": asset["title"],
                "description": asset["description"],
                "landing_page": BLOG_URL,
                "utm_url": utm,
                "utm_campaign": CAMPAIGN,
                "utm_content": asset["asset_id"],
                "local_source": str(path.relative_to(ROOT)),
            }
        )

    with (OUT_DIR / "upload_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (OUT_DIR / "upload_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    montage = Image.new("RGB", (2500, 1500), "#f6f3ec")
    for idx, row in enumerate(rows):
        pin = Image.open(ROOT / row["local_source"]).resize((500, 750), Image.LANCZOS)
        montage.paste(pin, (idx * 500, 0))
    montage.save(OUT_DIR / "blog9-vt101-pinterest-montage.jpg", quality=90, optimize=True)

    print(f"Generated {len(rows)} Blog 9 Pinterest assets in {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
