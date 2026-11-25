#!/usr/bin/env python3
"""Package 16:9 slide PNGs into an image-based PPTX and contact sheet."""

from __future__ import annotations

import argparse
import glob
import math
import sys
from pathlib import Path


def _import_deps():
    try:
        from PIL import Image, ImageDraw
        from pptx import Presentation
        from pptx.util import Inches
    except Exception as exc:  # pragma: no cover - environment error path
        raise SystemExit(
            "Missing dependency. Install with: python3 -m pip install pillow python-pptx\n"
            f"Import error: {exc}"
        )
    return Image, ImageDraw, Presentation, Inches


def _expand_images(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            paths.extend(Path(match).resolve() for match in matches)
        else:
            candidate = Path(pattern)
            if candidate.exists():
                paths.append(candidate.resolve())
    unique: list[Path] = []
    seen = set()
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def _validate_aspect(Image, image_paths: list[Path], tolerance: float) -> None:
    bad: list[str] = []
    for path in image_paths:
        with Image.open(path) as im:
            ratio = im.width / im.height
        if abs(ratio - (16 / 9)) > tolerance:
            bad.append(f"{path} ({ratio:.4f})")
    if bad:
        joined = "\n".join(bad)
        raise SystemExit(f"Images are not close to 16:9:\n{joined}")


def _make_pptx(Presentation, Inches, image_paths: list[Path], out_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    for path in image_paths:
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(path), 0, 0, width=prs.slide_width, height=prs.slide_height)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_path)


def _make_contact_sheet(Image, ImageDraw, image_paths: list[Path], out_path: Path, thumb_width: int) -> None:
    thumbs = []
    for path in image_paths:
        with Image.open(path) as im:
            im = im.convert("RGB")
            height = round(thumb_width * im.height / im.width)
            im.thumbnail((thumb_width, height))
            canvas = Image.new("RGB", (thumb_width, height), "white")
            canvas.paste(im, ((thumb_width - im.width) // 2, (height - im.height) // 2))
            thumbs.append((path, canvas))

    cols = 2 if len(thumbs) <= 6 else 3
    label_h = 34
    gap = 24
    rows = math.ceil(len(thumbs) / cols)
    cell_w = thumb_width
    cell_h = thumbs[0][1].height + label_h
    sheet_w = cols * cell_w + (cols + 1) * gap
    sheet_h = rows * cell_h + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)

    for idx, (path, thumb) in enumerate(thumbs):
        row, col = divmod(idx, cols)
        x = gap + col * (cell_w + gap)
        y = gap + row * (cell_h + gap)
        sheet.paste(thumb, (x, y + label_h))
        draw.text((x, y), f"{idx + 1:02d}  {path.name}", fill=(23, 32, 51))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", nargs="+", required=True, help="Image paths or glob patterns in slide order.")
    parser.add_argument("--out", required=True, help="Output PPTX path.")
    parser.add_argument("--contact-sheet", required=True, help="Output contact sheet PNG path.")
    parser.add_argument("--aspect-tolerance", type=float, default=0.015, help="Allowed 16:9 ratio deviation.")
    parser.add_argument("--thumb-width", type=int, default=720, help="Contact sheet thumbnail width.")
    args = parser.parse_args()

    Image, ImageDraw, Presentation, Inches = _import_deps()
    image_paths = _expand_images(args.images)
    if not image_paths:
        raise SystemExit("No images matched --images.")
    _validate_aspect(Image, image_paths, args.aspect_tolerance)
    _make_pptx(Presentation, Inches, image_paths, Path(args.out).resolve())
    _make_contact_sheet(Image, ImageDraw, image_paths, Path(args.contact_sheet).resolve(), args.thumb_width)
    print(f"slides={len(image_paths)}")
    print(f"pptx={Path(args.out).resolve()}")
    print(f"contact_sheet={Path(args.contact_sheet).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
