#!/usr/bin/env python3
# Modified for Gouache Picture-book PPT. See NOTICE.
"""Prepare source text and reusable visual assets for gouache picture-book presentations."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VECTOR_EXTS = {".pdf", ".svg"}
TEXT_EXTS = {".txt", ".md", ".tex"}


def read_text(path: Path) -> str:
    if path.suffix.lower() in TEXT_EXTS:
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".docx":
        return read_docx_text(path)
    return ""


def read_docx_text(path: Path) -> str:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as zf:
        data = zf.read("word/document.xml")
    root = ET.fromstring(data)
    for para in root.findall(".//w:p", ns):
        pieces = [node.text or "" for node in para.findall(".//w:t", ns)]
        text = "".join(pieces).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def iter_source_files(inputs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            for path in item.rglob("*"):
                if path.is_file():
                    files.append(path)
        elif item.is_file():
            files.append(item)
    return sorted(files)


def extract_includegraphics(tex_text: str) -> list[str]:
    pattern = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
    return pattern.findall(tex_text)


def copy_asset(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    safe_name = src.name.replace(" ", "_")
    dst = dst_dir / safe_name
    counter = 2
    while dst.exists() and src.resolve() != dst.resolve():
        dst = dst_dir / f"{src.stem.replace(' ', '_')}_{counter}{src.suffix.lower()}"
        counter += 1
    shutil.copy2(src, dst)
    return dst


def render_pdf_first_page(src: Path, dst_dir: Path) -> Path | None:
    try:
        import fitz  # type: ignore
    except Exception:
        return None
    try:
        doc = fitz.open(src)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        dst = dst_dir / f"{src.stem.replace(' ', '_')}.png"
        pix.save(dst)
        doc.close()
        return dst
    except Exception:
        return None


def extract_docx_media(src: Path, dst_dir: Path) -> list[Path]:
    out: list[Path] = []
    with zipfile.ZipFile(src) as zf:
        for name in zf.namelist():
            if not name.startswith("word/media/"):
                continue
            ext = Path(name).suffix.lower()
            if ext not in IMAGE_EXTS:
                continue
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / f"{src.stem}_{Path(name).name}"
            with zf.open(name) as in_f, open(dst, "wb") as out_f:
                shutil.copyfileobj(in_f, out_f)
            out.append(dst)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="Input files or folders.")
    parser.add_argument("--deck-dir", required=True, help="Target deck directory.")
    args = parser.parse_args()

    inputs = [Path(p).expanduser().resolve() for p in args.input]
    missing = [str(p) for p in inputs if not p.exists()]
    if missing:
        raise SystemExit(f"Missing inputs: {', '.join(missing)}")

    deck_dir = Path(args.deck_dir).expanduser().resolve()
    assets_dir = deck_dir / "assets"
    refs_dir = assets_dir / "reference_images"
    original_dir = assets_dir / "original_assets"
    deck_dir.mkdir(parents=True, exist_ok=True)

    files = iter_source_files(inputs)
    text_parts: list[str] = []
    assets: list[dict] = []
    include_refs: dict[str, list[str]] = {}

    for file_path in files:
        suffix = file_path.suffix.lower()
        if suffix in TEXT_EXTS or suffix == ".docx":
            text = read_text(file_path)
            if text:
                rel = file_path.name
                text_parts.append(f"\n\n<!-- SOURCE: {file_path} -->\n\n{text}")
            if suffix == ".tex":
                include_refs[str(file_path)] = extract_includegraphics(text)
        if suffix == ".docx":
            for media in extract_docx_media(file_path, refs_dir):
                assets.append({"source": str(file_path), "type": "docx-media", "prepared": str(media)})
        if suffix in IMAGE_EXTS:
            copied = copy_asset(file_path, refs_dir)
            assets.append({"source": str(file_path), "type": "raster", "prepared": str(copied)})
        elif suffix in VECTOR_EXTS:
            copied = copy_asset(file_path, original_dir)
            record = {"source": str(file_path), "type": suffix.lstrip("."), "prepared_original": str(copied)}
            if suffix == ".pdf":
                rendered = render_pdf_first_page(file_path, refs_dir)
                if rendered:
                    record["prepared"] = str(rendered)
                    record["type"] = "pdf-rendered"
            assets.append(record)

    source_text = deck_dir / "source_text.md"
    source_text.write_text("\n".join(text_parts).strip() + "\n", encoding="utf-8")

    inventory = {
        "inputs": [str(p) for p in inputs],
        "source_files": [str(p) for p in files],
        "source_text": str(source_text),
        "reference_images_dir": str(refs_dir),
        "original_assets_dir": str(original_dir),
        "assets": assets,
        "latex_includegraphics": include_refs,
        "notes": [
            "Use prepared raster reference images for exact figure preservation.",
            "For PDF figures, prepared PNG renderings are first-page previews when PyMuPDF is available.",
            "For SVG files, keep the original asset unless an external renderer is available."
        ],
    }
    inventory_path = deck_dir / "source_inventory.json"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "deck_dir": str(deck_dir), "source_text": str(source_text), "inventory": str(inventory_path), "assets": len(assets)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
