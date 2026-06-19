#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export public du portfolio photo.

Usage simple :
    1. Mets uniquement des photos publiables dans le dossier A_publier/
    2. Lance :
        python export_public.py

Le script :
    - lit les images dans A_publier/
    - corrige l'orientation
    - supprime les métadonnées EXIF
    - redimensionne pour le web
    - convertit en .webp
    - renomme les fichiers en photo-0001.webp, photo-0002.webp...
    - génère docs/data/photos.json
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

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

FRENCH_MONTHS = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}

MONTH_NAMES_TO_NUMBERS = {
    "janvier": 1, "janv": 1,
    "fevrier": 2, "fev": 2,
    "mars": 3,
    "avril": 4, "avr": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7, "juil": 7,
    "aout": 8,
    "septembre": 9, "sept": 9,
    "octobre": 10, "oct": 10,
    "novembre": 11, "nov": 11,
    "decembre": 12, "dec": 12,
}


@dataclass
class PublicPhoto:
    id: str
    filename: str
    original_name: str
    url: str
    width: int
    height: int
    date_iso: str
    date_label: str
    day_label: str
    day_key: str
    month_label: str
    month_key: str
    year: int
    sort_ts: float


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return value.casefold().strip()


def build_datetime(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> Optional[datetime]:
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def extract_date_from_text(text: str) -> Optional[datetime]:
    if not text:
        return None

    normalized = normalize_text(text)

    numeric_patterns = [
        r"(?<!\d)(?P<y>(?:19|20)\d{2})(?P<m>\d{2})(?P<d>\d{2})(?:[-_ .]?(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2}))?(?!\d)",
        r"(?<!\d)(?P<y>(?:19|20)\d{2})[-_ ./](?P<m>\d{1,2})[-_ ./](?P<d>\d{1,2})(?:[ T._/-](?P<h>\d{1,2})[:._-]?(?P<mi>\d{2})(?:[:._-]?(?P<s>\d{2}))?)?(?!\d)",
        r"(?<!\d)(?P<d>\d{1,2})[-_ ./](?P<m>\d{1,2})[-_ ./](?P<y>(?:19|20)\d{2})(?:[ T._/-](?P<h>\d{1,2})[:._-]?(?P<mi>\d{2})(?:[:._-]?(?P<s>\d{2}))?)?(?!\d)",
    ]

    for pattern in numeric_patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue

        try:
            year = int(match.group("y"))
            month = int(match.group("m"))
            day = int(match.group("d"))
            hour = int(match.group("h") or 0)
            minute = int(match.group("mi") or 0)
            second = int(match.group("s") or 0)
        except (TypeError, ValueError):
            continue

        parsed = build_datetime(year, month, day, hour, minute, second)
        if parsed:
            return parsed

    month_names = "|".join(sorted(MONTH_NAMES_TO_NUMBERS.keys(), key=len, reverse=True))
    month_patterns = [
        rf"(?<!\w)(?P<d>\d{{1,2}})[-_ ./]*(?P<month>{month_names})[-_ ./]+(?P<y>(?:19|20)\d{{2}})(?!\w)",
        rf"(?<!\w)(?P<month>{month_names})[-_ ./]+(?P<y>(?:19|20)\d{{2}})(?!\w)",
        rf"(?<!\w)(?P<y>(?:19|20)\d{{2}})[-_ ./]+(?P<month>{month_names})(?!\w)",
    ]

    for pattern in month_patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue

        try:
            year = int(match.group("y"))
            month = MONTH_NAMES_TO_NUMBERS[match.group("month")]
            day = int(match.groupdict().get("d") or 1)
        except (KeyError, TypeError, ValueError):
            continue

        parsed = build_datetime(year, month, day)
        if parsed:
            return parsed

    return None


def extract_exif_date(path: Path) -> Optional[datetime]:
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            for tag_id in (36867, 36868, 306):
                value = exif.get(tag_id)
                if not value:
                    continue
                try:
                    return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
    except Exception:
        pass
    return None


def choose_date(path: Path) -> datetime:
    return (
        extract_date_from_text(path.name)
        or extract_date_from_text(str(path.parent))
        or extract_exif_date(path)
        or datetime.fromtimestamp(path.stat().st_mtime)
    )


def photo_id(path: Path) -> str:
    raw = f"{path.resolve()}::{path.stat().st_mtime_ns}::{path.stat().st_size}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:12]


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
        if img.mode == "RGBA":
            clean = Image.new("RGBA", img.size)
        else:
            clean = Image.new("RGB", img.size)
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

    images.sort(key=lambda path: choose_date(path).timestamp(), reverse=True)
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
        dt = choose_date(source)
        output_name = f"photo-{index:04d}.webp"
        output_path = OUTPUT_PHOTOS_DIR / output_name
        width, height = export_image(source, output_path)

        exported.append(
            PublicPhoto(
                id=photo_id(source),
                filename=output_name,
                original_name=source.name,
                url=f"photos/{output_name}",
                width=width,
                height=height,
                date_iso=dt.isoformat(),
                date_label=dt.strftime("%d/%m/%Y"),
                day_label=f"{dt.day} {FRENCH_MONTHS[dt.month].lower()} {dt.year}",
                day_key=dt.strftime("%Y-%m-%d"),
                month_label=f"{FRENCH_MONTHS[dt.month]} {dt.year}",
                month_key=dt.strftime("%Y-%m"),
                year=dt.year,
                sort_ts=dt.timestamp(),
            )
        )

    OUTPUT_JSON.write_text(
        json.dumps([asdict(photo) for photo in exported], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"{len(exported)} photo(s) exportée(s).")
    print(f"Images : {OUTPUT_PHOTOS_DIR}")
    print(f"Données : {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
