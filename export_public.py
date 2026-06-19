#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export public du portfolio photo.

Usage :
    1. Mets uniquement des photos publiables dans le dossier A_publier/
    2. Lance :
        python export_public.py

Le script :
    - lit les images dans A_publier/
    - randomise leur ordre de manière stable
    - corrige l'orientation
    - supprime les métadonnées EXIF
    - redimensionne pour le web
    - convertit en .webp
    - renomme les fichiers en photo-0001.webp, photo-0002.webp...
    - génère docs/data/photos.json sans date, sans nom original et sans chemin privé
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageOps


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "A_publier"
DOCS_DIR = PROJECT_DIR / "docs"
OUTPUT_PHOTOS_DIR = DOCS_DIR / "photos"
OUTPUT_DATA_DIR = DOCS_DIR / "data"
OUTPUT_JSON = OUTPUT_DATA_DIR / "photos.json"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}

MAX_SIZE = 2400
WEBP_QUALITY = 86
RANDOM_SEED = "portfolio-public-v1"


@dataclass
class PublicPhoto:
    id: str
    filename: str
    url: str
    width: int
    height: int
    order: int


def source_fingerprint(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.name}::{stat.st_size}::{stat.st_mtime_ns}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()


def public_id(path: Path) -> str:
    return source_fingerprint(path)[:12]


def clean_output_folder() -> None:
    OUTPUT_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for item in OUTPUT_PHOTOS_DIR.iterdir():
        if item.name == ".gitkeep":
            continue
        if item.is_file():
            item.unlink()


def export_image(source: Path, destination: Path) -> Tuple[int, int]:
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

        # Nouvelle image sans métadonnées EXIF.
        clean = Image.new("RGBA" if img.mode == "RGBA" else "RGB", img.size)
        clean.paste(img)

        clean.save(destination, "WEBP", quality=WEBP_QUALITY, method=6)
        return clean.size


def find_source_images() -> list[Path]:
    if not SOURCE_DIR.exists():
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Dossier créé : {SOURCE_DIR}")
        print("Mets des photos publiques dedans, puis relance le script.")
        return []

    images = [
        path for path in SOURCE_DIR.rglob("*")
        if path.is_file() and path.suffix.casefold() in ALLOWED_EXTENSIONS
    ]

    # Ordre stable avant le mélange, pour que le résultat soit reproductible.
    images.sort(key=lambda path: str(path.relative_to(SOURCE_DIR)).casefold())

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(images)
    return images


def main() -> int:
    clean_output_folder()
    images = find_source_images()

    if not images:
        OUTPUT_JSON.write_text("[]\n", encoding="utf-8")
        print("Aucune photo à exporter.")
        return 0

    exported: list[PublicPhoto] = []

    for index, source in enumerate(images, start=1):
        output_name = f"photo-{index:04d}.webp"
        output_path = OUTPUT_PHOTOS_DIR / output_name
        width, height = export_image(source, output_path)

        exported.append(
            PublicPhoto(
                id=public_id(source),
                filename=output_name,
                url=f"photos/{output_name}",
                width=width,
                height=height,
                order=index,
            )
        )

    OUTPUT_JSON.write_text(
        json.dumps([asdict(photo) for photo in exported], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"{len(exported)} photo(s) exportée(s).")
    print("Ordre : aléatoire stable")
    print(f"Images : {OUTPUT_PHOTOS_DIR}")
    print(f"Données : {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
