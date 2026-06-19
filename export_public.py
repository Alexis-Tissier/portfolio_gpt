#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export public du portfolio photo.

Structure recommandée :

A_publier/
├── featured/   -> photos mises en avant, toujours affichées en premier
└── random/     -> photos mélangées à chaque chargement du site

Le script génère :
- docs/photos/thumbs/ : miniatures optimisées pour la galerie ;
- docs/photos/full/   : images haute qualité pour la lightbox ;
- docs/data/photos.json.

A_publier/ doit rester ignoré par Git.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageOps

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "A_publier"
FEATURED_DIR = SOURCE_DIR / "featured"
RANDOM_DIR = SOURCE_DIR / "random"

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

# Bon compromis : galerie fluide, lightbox en vraie qualité portfolio.
THUMB_MAX_SIZE = 1400
THUMB_QUALITY = 86

FULL_MAX_SIZE = 3200
FULL_QUALITY = 92


def file_hash(path: Path) -> str:
    """Hash utilisé uniquement en cache-busting dans l'URL, pas dans le nom du fichier."""
    h = hashlib.sha1()
    try:
        h.update(path.name.encode("utf-8", errors="ignore"))
        h.update(str(path.stat().st_size).encode())
        h.update(str(path.stat().st_mtime_ns).encode())
    except Exception:
        h.update(str(path).encode("utf-8", errors="ignore"))
    return h.hexdigest()[:12]


def ensure_source_structure() -> None:
    """Crée la structure A_publier/featured et A_publier/random si elle n'existe pas."""
    FEATURED_DIR.mkdir(parents=True, exist_ok=True)
    RANDOM_DIR.mkdir(parents=True, exist_ok=True)

    for folder in (FEATURED_DIR, RANDOM_DIR):
        gitkeep = folder / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")


def is_supported_image(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS


def collect_images_from(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return sorted(
        [path for path in folder.rglob("*") if is_supported_image(path)],
        key=lambda path: path.name.casefold(),
    )


def collect_loose_images() -> List[Path]:
    """
    Compatibilité : si des photos sont encore directement dans A_publier/,
    elles sont traitées comme des photos random.
    """
    if not SOURCE_DIR.exists():
        return []

    ignored_dirs = {FEATURED_DIR.resolve(), RANDOM_DIR.resolve()}
    loose_images: List[Path] = []

    for path in SOURCE_DIR.iterdir():
        if path.is_dir():
            try:
                if path.resolve() in ignored_dirs:
                    continue
            except Exception:
                continue
        if is_supported_image(path):
            loose_images.append(path)

    return sorted(loose_images, key=lambda path: path.name.casefold())


def collect_images() -> List[Tuple[Path, bool]]:
    """
    Retourne une liste de tuples :
    - (chemin, True)  pour featured ;
    - (chemin, False) pour random.

    featured/ est gardé dans l'ordre alphabétique.
    random/ est mélangé côté navigateur à chaque refresh.
    """
    ensure_source_structure()

    featured = collect_images_from(FEATURED_DIR)
    random_images = collect_images_from(RANDOM_DIR) + collect_loose_images()

    return [(path, True) for path in featured] + [(path, False) for path in random_images]


def reset_output() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    # Nettoyage des nouvelles sorties.
    if THUMBS_DIR.exists():
        shutil.rmtree(THUMBS_DIR)
    if FULL_DIR.exists():
        shutil.rmtree(FULL_DIR)

    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    FULL_DIR.mkdir(parents=True, exist_ok=True)

    # Nettoyage des anciennes sorties placées directement dans docs/photos/.
    for old in PHOTOS_DIR.glob("photo-*.webp"):
        try:
            old.unlink()
        except Exception:
            pass

    gitkeep = PHOTOS_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")


def open_clean_image(source: Path) -> Image.Image:
    """Ouvre l'image, corrige l'orientation EXIF, supprime les métadonnées en repartant d'une image RGB neuve."""
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        img.load()

        if img.mode in ("RGBA", "LA"):
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background

        if img.mode != "RGB":
            img = img.convert("RGB")

        return img.copy()


def resize_to_max(img: Image.Image, max_size: int) -> Image.Image:
    output = img.copy()
    output.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return output


def save_webp(img: Image.Image, target: Path, quality: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    # Pas d'EXIF transmis ici : fichier public nettoyé.
    img.save(target, "WEBP", quality=quality, method=6)


def export_one(source: Path, index: int, featured: bool) -> Dict[str, object]:
    clean_name = f"photo-{index:04d}.webp"
    version = file_hash(source)

    with open_clean_image(source) as img:
        thumb = resize_to_max(img, THUMB_MAX_SIZE)
        full = resize_to_max(img, FULL_MAX_SIZE)

        thumb_path = THUMBS_DIR / clean_name
        full_path = FULL_DIR / clean_name

        save_webp(thumb, thumb_path, THUMB_QUALITY)
        save_webp(full, full_path, FULL_QUALITY)

        width, height = thumb.size
        full_width, full_height = full.size

    return {
        "id": f"photo-{index:04d}",
        "order": index,
        "featured": featured,
        "thumb_url": f"photos/thumbs/{clean_name}?v={version}",
        "full_url": f"photos/full/{clean_name}?v={version}",
        "width": width,
        "height": height,
        "full_width": full_width,
        "full_height": full_height,
    }


def main() -> int:
    images = collect_images()
    reset_output()

    if not images:
        JSON_PATH.write_text("[]\n", encoding="utf-8")
        print("Aucune photo trouvée dans A_publier/featured/ ou A_publier/random/.")
        print(f"Dossiers créés : {FEATURED_DIR} et {RANDOM_DIR}")
        return 0

    exported: List[Dict[str, object]] = []

    for index, (source, featured) in enumerate(images, start=1):
        try:
            exported.append(export_one(source, index, featured))
            tag = "featured" if featured else "random"
            print(f"Export [{tag}] : {source.name}")
        except Exception as exc:
            print(f"Erreur avec {source.name} : {exc}")

    JSON_PATH.write_text(json.dumps(exported, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    featured_count = sum(1 for item in exported if item.get("featured"))
    random_count = len(exported) - featured_count

    print()
    print(f"{len(exported)} photo(s) exportée(s).")
    print(f"Featured  : {featured_count}")
    print(f"Random    : {random_count}")
    print(f"Miniatures : {THUMBS_DIR}")
    print(f"Photos HD  : {FULL_DIR}")
    print(f"Données    : {JSON_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
