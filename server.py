#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Photo Local
Application web locale en Python pour afficher automatiquement les photos contenues
sous les dossiers nommés "Retouché".

Lancement :
    python server.py
ou :
    python server.py --root "C:/Users/Alexis/Documents/Photos"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import webbrowser
from dataclasses import dataclass, asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageOps  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"


def get_local_data_dir() -> Path:
    """Return a writable local folder, so Windows does not require admin rights."""
    if os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "PortfolioPhotoLocal"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "PortfolioPhotoLocal"

    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "PortfolioPhotoLocal"
    return Path.home() / ".local" / "share" / "PortfolioPhotoLocal"


LOCAL_DATA_DIR = get_local_data_dir()
CACHE_DIR = LOCAL_DATA_DIR / "cache" / "thumbnails"
CONFIG_PATH = LOCAL_DATA_DIR / "config.json"
LEGACY_CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG = {
    "photos_root": "",
    "target_folder_name": "Retouché",
    "extensions": [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"],
    "default_sort": "desc",
}

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
    "janvier": 1,
    "janv": 1,
    "fevrier": 2,
    "fev": 2,
    "mars": 3,
    "avril": 4,
    "avr": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "juil": 7,
    "aout": 8,
    "septembre": 9,
    "sept": 9,
    "octobre": 10,
    "oct": 10,
    "novembre": 11,
    "nov": 11,
    "decembre": 12,
    "dec": 12,
}


@dataclass(frozen=True)
class DateCandidate:
    dt: datetime
    source: str


def normalize_text(value: str) -> str:
    """Compare names without accents and without case sensitivity."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return value.casefold().strip()


def read_json_file(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_config() -> dict:
    """
    Load the local config from AppData.
    If an old config.json exists next to server.py, migrate it automatically once.
    """
    config = dict(DEFAULT_CONFIG)

    if CONFIG_PATH.exists():
        config.update(read_json_file(CONFIG_PATH))
        return config

    if LEGACY_CONFIG_PATH.exists():
        config.update(read_json_file(LEGACY_CONFIG_PATH))
        save_config(config)
        return config

    save_config(config)
    return config


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_resolve_root(path_value: str) -> Optional[Path]:
    if not path_value:
        return None
    path_value = os.path.expandvars(os.path.expanduser(path_value.strip().strip('"')))
    path = Path(path_value)
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path.absolute()
    return resolved


def build_datetime(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> Optional[datetime]:
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def extract_date_from_text(text: str) -> Optional[datetime]:
    """
    Extract a date from a filename, folder name, or full path.

    Supported examples:
    - 20260616-200152-0001-Alexis.jpg
    - IMG_20260616_200152.jpg
    - 2026-06-16-photo.jpg
    - 2026_06_16-photo.jpg
    - 16-06-2026-photo.jpg
    - Juin 2026
    - 2026 Juin
    - 16 Juin 2026
    """
    if not text:
        return None

    normalized = normalize_text(text)

    numeric_patterns = [
        # 20260616, 20260616-200152, 20260616_200152, 20260616200152
        r"(?<!\d)(?P<y>(?:19|20)\d{2})(?P<m>\d{2})(?P<d>\d{2})(?:[-_ .]?(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2}))?(?!\d)",
        # 2026-06-16, 2026_06_16, 2026.06.16, 2026/06/16
        r"(?<!\d)(?P<y>(?:19|20)\d{2})[-_ ./](?P<m>\d{1,2})[-_ ./](?P<d>\d{1,2})(?:[ T._/-](?P<h>\d{1,2})[:._-]?(?P<mi>\d{2})(?:[:._-]?(?P<s>\d{2}))?)?(?!\d)",
        # 16-06-2026, 16_06_2026, 16.06.2026, 16/06/2026
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
        # 16 juin 2026
        rf"(?<!\w)(?P<d>\d{{1,2}})[-_ ./]*(?P<month>{month_names})[-_ ./]+(?P<y>(?:19|20)\d{{2}})(?!\w)",
        # juin 2026
        rf"(?<!\w)(?P<month>{month_names})[-_ ./]+(?P<y>(?:19|20)\d{{2}})(?!\w)",
        # 2026 juin
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


def parse_date_from_filename(filename: str) -> Tuple[Optional[datetime], str]:
    """Backward-compatible helper used by the scanner."""
    dt = extract_date_from_text(filename)
    return dt, "nom du fichier" if dt else "non détectée"


def extract_exif_date(path: Path) -> Optional[datetime]:
    if not PIL_AVAILABLE:
        return None

    try:
        with Image.open(path) as img:
            exif = img.getexif()

            for tag_id in (36867, 36868, 306):  # DateTimeOriginal, DateTimeDigitized, DateTime
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


def choose_photo_date(filename: str, path: Path) -> DateCandidate:
    """
    Choose the best possible date.
    Priority: filename -> folder/path -> EXIF -> modification date.
    """
    filename_dt = extract_date_from_text(filename)
    if filename_dt:
        return DateCandidate(filename_dt, "nom du fichier")

    folder_dt = extract_date_from_text(str(path.parent))
    if folder_dt:
        return DateCandidate(folder_dt, "dossier")

    exif_dt = extract_exif_date(path)
    if exif_dt:
        return DateCandidate(exif_dt, "EXIF")

    return DateCandidate(datetime.fromtimestamp(path.stat().st_mtime), "date de modification")


def month_label(dt: datetime) -> str:
    return f"{FRENCH_MONTHS[dt.month]} {dt.year}"


def stable_id(path: Path) -> str:
    raw = str(path.resolve()).encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:18]


def get_image_dimensions(path: Path) -> Tuple[Optional[int], Optional[int]]:
    """
    Read image dimensions without decoding the full image.
    This keeps the initial scan fast and avoids blocking on large/corrupted files.
    """
    if not PIL_AVAILABLE:
        return None, None

    try:
        with Image.open(path) as img:
            width, height = img.size

            # EXIF orientation can mean the image is displayed rotated.
            # We only swap width/height when needed, without calling ImageOps.exif_transpose().
            try:
                orientation = img.getexif().get(274)
                if orientation in (5, 6, 7, 8):
                    width, height = height, width
            except Exception:
                pass

            return width, height
    except Exception:
        return None, None


@dataclass
class PhotoRecord:
    id: str
    filename: str
    absolute_path: str
    relative_path: str
    folder: str
    date_iso: Optional[str]
    date_label: str
    month_key: str
    month_label: str
    year: Optional[int]
    sort_ts: float
    date_source: str
    media_url: str
    thumb_url: str
    width: Optional[int]
    height: Optional[int]


class PhotoIndex:
    def __init__(self) -> None:
        self.records: List[PhotoRecord] = []
        self.records_by_id: Dict[str, PhotoRecord] = {}
        self.last_scan_at: Optional[float] = None
        self.last_error: Optional[str] = None
        self.config_snapshot: Optional[dict] = None

    def scan(self, force: bool = False) -> None:
        config = load_config()
        root = safe_resolve_root(config.get("photos_root", ""))
        target_name = normalize_text(config.get("target_folder_name", "Retouché"))
        extensions = {ext.casefold() for ext in config.get("extensions", DEFAULT_CONFIG["extensions"])}
        sort_desc = config.get("default_sort", "desc") != "asc"

        # Reuse recent scan unless forced.
        if (
            not force
            and self.last_scan_at
            and self.config_snapshot == config
            and time.time() - self.last_scan_at < 10
        ):
            return

        self.last_error = None
        self.config_snapshot = dict(config)
        found: Dict[str, PhotoRecord] = {}

        if not root or not root.exists() or not root.is_dir():
            self.records = []
            self.records_by_id = {}
            self.last_scan_at = time.time()
            self.last_error = "Le dossier racine n'existe pas ou n'est pas configuré."
            return

        try:
            for current_dir, _dirnames, _filenames in os.walk(root):
                current_path = Path(current_dir)
                if normalize_text(current_path.name) != target_name:
                    continue

                # Once a Retouché folder is found, collect images inside it and all its subfolders.
                for retouche_dir, _subdirs, retouche_files in os.walk(current_path):
                    retouche_path = Path(retouche_dir)
                    for filename in retouche_files:
                        path = retouche_path / filename
                        if path.suffix.casefold() not in extensions:
                            continue

                        try:
                            resolved = path.resolve()
                            if not resolved.is_file():
                                continue

                            photo_id = stable_id(resolved)
                            if photo_id in found:
                                continue

                            date_candidate = choose_photo_date(filename, resolved)
                            parsed_dt = date_candidate.dt
                            relative_path = str(resolved.relative_to(root)).replace("\\", "/")
                            folder = str(resolved.parent.relative_to(root)).replace("\\", "/")
                            image_width, image_height = get_image_dimensions(resolved)

                            found[photo_id] = PhotoRecord(
                                id=photo_id,
                                filename=filename,
                                absolute_path=str(resolved),
                                relative_path=relative_path,
                                folder=folder,
                                date_iso=parsed_dt.isoformat(),
                                date_label=parsed_dt.strftime("%d/%m/%Y"),
                                month_key=parsed_dt.strftime("%Y-%m"),
                                month_label=month_label(parsed_dt),
                                year=parsed_dt.year,
                                sort_ts=parsed_dt.timestamp(),
                                date_source=date_candidate.source,
                                media_url=f"/media/{photo_id}",
                                thumb_url=f"/thumb/{photo_id}",
                                width=image_width,
                                height=image_height,
                            )
                        except Exception:
                            continue
        except Exception as exc:
            self.last_error = f"Erreur pendant le scan : {exc}"

        records = list(found.values())
        records.sort(key=lambda item: item.sort_ts, reverse=sort_desc)
        self.records = records
        self.records_by_id = {record.id: record for record in records}
        self.last_scan_at = time.time()

    def to_payload(self) -> dict:
        config = load_config()
        root = safe_resolve_root(config.get("photos_root", ""))
        years = sorted({record.year for record in self.records if record.year}, reverse=True)
        retouche_folders = sorted({record.folder.split("/")[0] for record in self.records if record.folder})
        return {
            "photos": [asdict(record) | {"absolute_path": None} for record in self.records],
            "count": len(self.records),
            "years": years,
            "root": str(root) if root else "",
            "last_scan_at": self.last_scan_at,
            "last_error": self.last_error,
            "pillow_available": PIL_AVAILABLE,
            "retouche_folders": retouche_folders,
            "config_path": str(CONFIG_PATH),
            "cache_dir": str(CACHE_DIR),
        }


INDEX = PhotoIndex()


def send_json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_file(handler: BaseHTTPRequestHandler, path: Path, content_type: Optional[str] = None) -> None:
    if not path.exists() or not path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND, "Fichier introuvable")
        return
    if content_type is None:
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    try:
        size = path.stat().st_size
        handler.send_response(200)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(size))
        handler.send_header("Cache-Control", "public, max-age=604800")
        handler.end_headers()
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 256)
                if not chunk:
                    break
                handler.wfile.write(chunk)
    except BrokenPipeError:
        pass
    except Exception as exc:
        handler.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))


def create_thumbnail(source: Path, photo_id: str, width: int = 900) -> Optional[Path]:
    if not PIL_AVAILABLE:
        return None
    try:
        stat = source.stat()
        cache_key = hashlib.sha1(f"{source.resolve()}::{stat.st_mtime_ns}::{width}".encode("utf-8", errors="ignore")).hexdigest()
        thumb_path = CACHE_DIR / f"{photo_id}_{cache_key}.webp"
        if thumb_path.exists():
            return thumb_path
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Remove older thumbnails for the same photo id.
        for old in CACHE_DIR.glob(f"{photo_id}_*.webp"):
            try:
                old.unlink()
            except Exception:
                pass

        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((width, width), Image.Resampling.LANCZOS)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.save(thumb_path, "WEBP", quality=82, method=6)
        return thumb_path
    except Exception:
        return None


class PortfolioHandler(BaseHTTPRequestHandler):
    server_version = "PortfolioPhotoLocal/1.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        # Keep the terminal clean.
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            return send_file(self, STATIC_DIR / "index.html", "text/html; charset=utf-8")

        if path.startswith("/static/"):
            name = path.removeprefix("/static/")
            candidate = (STATIC_DIR / name).resolve()
            try:
                candidate.relative_to(STATIC_DIR.resolve())
            except ValueError:
                self.send_error(HTTPStatus.FORBIDDEN, "Accès refusé")
                return
            return send_file(self, candidate)

        if path == "/api/config":
            config = load_config()
            root = safe_resolve_root(config.get("photos_root", ""))
            exists = bool(root and root.exists() and root.is_dir())
            return send_json(
                self,
                {
                    "config": config,
                    "root_exists": exists,
                    "config_path": str(CONFIG_PATH),
                    "cache_dir": str(CACHE_DIR),
                },
            )

        if path == "/api/photos":
            force = query.get("force", ["0"])[0] == "1"
            INDEX.scan(force=force)
            return send_json(self, INDEX.to_payload())

        if path.startswith("/media/"):
            photo_id = path.removeprefix("/media/").strip("/")
            INDEX.scan(force=False)
            record = INDEX.records_by_id.get(photo_id)
            if not record:
                self.send_error(HTTPStatus.NOT_FOUND, "Photo introuvable")
                return
            return send_file(self, Path(record.absolute_path))

        if path.startswith("/thumb/"):
            photo_id = path.removeprefix("/thumb/").strip("/")
            INDEX.scan(force=False)
            record = INDEX.records_by_id.get(photo_id)
            if not record:
                self.send_error(HTTPStatus.NOT_FOUND, "Photo introuvable")
                return
            source = Path(record.absolute_path)
            thumb = create_thumbnail(source, photo_id)
            if thumb:
                return send_file(self, thumb, "image/webp")
            return send_file(self, source)

        self.send_error(HTTPStatus.NOT_FOUND, "Page introuvable")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        if path == "/api/config":
            config = load_config()
            if "photos_root" in payload:
                config["photos_root"] = str(payload.get("photos_root") or "").strip()
            if "target_folder_name" in payload:
                config["target_folder_name"] = str(payload.get("target_folder_name") or "Retouché").strip() or "Retouché"
            if "default_sort" in payload and payload.get("default_sort") in ("asc", "desc"):
                config["default_sort"] = payload["default_sort"]
            save_config(config)
            INDEX.scan(force=True)
            return send_json(self, {"ok": True, "config": config, **INDEX.to_payload()})

        if path == "/api/rescan":
            INDEX.scan(force=True)
            return send_json(self, {"ok": True, **INDEX.to_payload()})

        self.send_error(HTTPStatus.NOT_FOUND, "Page introuvable")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Portfolio Photo Local")
    parser.add_argument("--root", help="Dossier racine à scanner, ex: C:/Users/Alexis/Documents/Photos")
    parser.add_argument("--port", type=int, default=8000, help="Port local, par défaut 8000")
    parser.add_argument("--no-browser", action="store_true", help="Ne pas ouvrir automatiquement le navigateur")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    config = load_config()
    if args.root:
        config["photos_root"] = args.root
        save_config(config)

    # Do not scan at startup.
    # The server must start first so the local address works immediately.
    # Photos are scanned from the web interface through /api/photos.
    address = "127.0.0.1"
    httpd = ThreadingHTTPServer((address, args.port), PortfolioHandler)
    url = f"http://{address}:{args.port}"

    print("Portfolio Photo Local")
    print("----------------------")
    print(f"Adresse : {url}")
    if config.get("photos_root"):
        print(f"Dossier : {config.get('photos_root')}")
    else:
        print("Dossier : à configurer dans l'interface")
    print(f"Config : {CONFIG_PATH}")
    print(f"Cache : {CACHE_DIR}")
    print(f"Miniatures accélérées : {'oui' if PIL_AVAILABLE else 'non (Pillow non installé, l’app fonctionne quand même)'}")
    print("Arrêt : Ctrl+C")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nApplication arrêtée.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
