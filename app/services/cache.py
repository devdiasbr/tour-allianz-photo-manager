"""Disk cache for face encodings and thumbnails, keyed by file sha12."""

import io
import os
import pickle
import threading
from typing import Optional

import numpy as np
from PIL import Image

from app.config import THUMBNAIL_SIZE

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cache")
ENCODINGS_FILE = os.path.join(CACHE_DIR, "encodings.pkl")
THUMBNAILS_DIR = os.path.join(CACHE_DIR, "thumbnails")

os.makedirs(THUMBNAILS_DIR, exist_ok=True)

_lock = threading.Lock()
_encodings: dict[str, list[np.ndarray]] = {}
_loaded = False


def _load() -> None:
    global _encodings, _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        if os.path.isfile(ENCODINGS_FILE):
            try:
                with open(ENCODINGS_FILE, "rb") as f:
                    _encodings = pickle.load(f)
            except Exception:
                _encodings = {}
        _loaded = True


def get_encodings(sha: str) -> Optional[list[np.ndarray]]:
    """Return cached encodings for a file hash, or None on miss."""
    _load()
    with _lock:
        return _encodings.get(sha)


def put_encodings(sha: str, encodings: list[np.ndarray]) -> None:
    """Store encodings under the given file hash and persist atomically."""
    _load()
    with _lock:
        _encodings[sha] = encodings
        _persist_locked()


def _persist_locked() -> None:
    tmp = ENCODINGS_FILE + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(_encodings, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, ENCODINGS_FILE)


def thumbnail_path(sha: str) -> str:
    return os.path.join(THUMBNAILS_DIR, f"{sha}.jpg")


def has_thumbnail(sha: str) -> bool:
    return os.path.isfile(thumbnail_path(sha))


def write_thumbnail(sha: str, source_image_path: str) -> str:
    """Generate (if missing) and write a JPEG thumbnail for the given file. Returns its path."""
    out = thumbnail_path(sha)
    if os.path.isfile(out):
        return out
    with Image.open(source_image_path) as img:
        img = img.convert("RGB")
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        img.save(out, format="JPEG", quality=85)
    return out


def stats() -> dict:
    _load()
    with _lock:
        return {
            "encodings_cached": len(_encodings),
            "thumbnails_cached": sum(1 for _ in os.scandir(THUMBNAILS_DIR) if _.is_file()),
        }
