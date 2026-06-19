#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export public du portfolio photo.

Le script lit uniquement les photos placées dans A_publier/,
supprime les métadonnées EXIF, génère :
- des miniatures optimisées pour la galerie ;
- des images haute qualité pour la lightbox ;
- docs/data/photos.json.

A_publier/ doit rester ignoré par Git.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageOps

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "A_publier"

DOCS_DIR = PROJECT_DIR / "docs"
PHOTOS_DIR = DOCS_DIR / "photos"
THUMBS_DIR = PHOTOS_DIR / "thumbs"
FULL_DIR = PHOTOS_DIR / "full"
DATA_DIR = DOCS_DIR / "data"
JSON_PATH = DATA_DIR / "photos.json"

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

THUMB_MAX_SIZE = 1600
THUMB_QUALITY = 86

FULL_MAX_SIZE = 3200
FULL_QUALITY = 92

RANDOM_SEED = "portfolio-public-v1"


def stable_hash(path: Path) -> str:
    try:
        stat = path.stat()
        raw = f"{path.name}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8", errors="ignore")
    except Exception:
        raw = str(path).encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:14]


def collect_images() -> List[Path]:
    if not SOURCE_DIR.exists():
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        return []

    files = [
        path
        for path in SOURCE_DIR.rglob("*")
        if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
    ]

    return sorted(files, key=lambda item: item.name.casefold())


def reset_output() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    if THUMBS_DIR.exists():
        shutil.rmtree(THUMBS_DIR)
    if FULL_DIR.exists():
        shutil.rmtree(FULL_DIR)

    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    FULL_DIR.mkdir(parents=True, exist_ok=True)

    gitkeep = PHOTOS_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")


def open_clean_image(source: Path) -> Image.Image:
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        img.load()

    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.getchannel("A") if "A" in img.getbands() else None
        background.paste(img.convert("RGBA"), mask=alpha)
        return background

    if img.mode != "RGB":
        img = img.convert("RGB")

    return img


def resize_to_max(img: Image.Image, max_size: int) -> Image.Image:
    copy = img.copy()
    copy.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return copy


def save_webp(img: Image.Image, target: Path, quality: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, "WEBP", quality=quality, method=6)


def export_one(source: Path, index: int, order: int) -> Dict[str, object]:
    image_id = stable_hash(source)
    filename = f"photo-{index:04d}.webp"

    with open_clean_image(source) as img:
        full = resize_to_max(img, FULL_MAX_SIZE)
        thumb = resize_to_max(img, THUMB_MAX_SIZE)

        full_path = FULL_DIR / filename
        thumb_path = THUMBS_DIR / filename

        save_webp(full, full_path, FULL_QUALITY)
        save_webp(thumb, thumb_path, THUMB_QUALITY)

        width, height = thumb.size
        full_width, full_height = full.size

    return {
        "id": f"photo-{index:04d}-{image_id}",
        "order": order,
        "thumb_url": f"photos/thumbs/{filename}",
        "full_url": f"photos/full/{filename}",
        "url": f"photos/thumbs/{filename}",
        "width": width,
        "height": height,
        "full_width": full_width,
        "full_height": full_height,
    }


def build_random_order(images: List[Path]) -> Dict[Path, int]:
    ordered = list(images)
    random.Random(RANDOM_SEED).shuffle(ordered)
    return {path: order for order, path in enumerate(ordered)}


def main() -> int:
    images = collect_images()

    reset_output()

    if not images:
        JSON_PATH.write_text("[]\n", encoding="utf-8")
        print("Aucune photo trouvée dans A_publier/.")
        return 0

    order_map = build_random_order(images)
    exported = []

    for index, source in enumerate(images, start=1):
        try:
            exported.append(export_one(source, index, order_map[source]))
            print(f"Export : {source.name}")
        except Exception as exc:
            print(f"Erreur avec {source.name} : {exc}")

    exported.sort(key=lambda item: int(item["order"]))
    JSON_PATH.write_text(json.dumps(exported, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print(f"{len(exported)} photo(s) exportée(s).")
    print(f"Miniatures : {THUMBS_DIR}")
    print(f"Photos HD  : {FULL_DIR}")
    print(f"Données    : {JSON_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
