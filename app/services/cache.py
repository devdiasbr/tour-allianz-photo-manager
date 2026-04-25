"""Disk cache for face encodings and thumbnails, keyed by file sha12."""

import io
import logging
import os
import pickle
import threading
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from app.config import THUMBNAIL_SIZE

log = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cache")
# v2 schema stores {"locs": [...], "encs": [...]} per key — caches the slow
# face_locations call too, not just encodings. Old v1 file is ignored.
DETECTIONS_FILE = os.path.join(CACHE_DIR, "detections.pkl")
THUMBNAILS_DIR = os.path.join(CACHE_DIR, "thumbnails")

os.makedirs(THUMBNAILS_DIR, exist_ok=True)

_lock = threading.Lock()
_detections: dict[str, dict] = {}
_loaded = False
_dirty = False


def _load() -> None:
    global _detections, _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        if os.path.isfile(DETECTIONS_FILE):
            try:
                with open(DETECTIONS_FILE, "rb") as f:
                    _detections = pickle.load(f)
            except Exception:
                _detections = {}
        _loaded = True


def get_detection(key: str) -> Optional[dict]:
    """Return cached {"locs": [...], "encs": [...]} for a key, or None on miss."""
    _load()
    with _lock:
        return _detections.get(key)


def put_detection(key: str, locations: list, encodings: list[np.ndarray]) -> None:
    """Buffer detection results (locations + encodings) under the given key.

    Persistence is deferred to `flush()` to avoid I/O contention and OneDrive
    file-lock errors during the atomic rename.
    """
    global _dirty
    _load()
    with _lock:
        _detections[key] = {"locs": list(locations), "encs": list(encodings)}
        _dirty = True


def flush() -> None:
    """Persist the in-memory detection cache to disk if dirty.

    Safe to call repeatedly; tolerates transient OS errors (e.g. OneDrive
    holding the file open) by logging and continuing — the in-memory cache
    survives until the next successful flush.
    """
    global _dirty
    _load()
    with _lock:
        if not _dirty:
            return
        try:
            tmp = DETECTIONS_FILE + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(_detections, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, DETECTIONS_FILE)
            _dirty = False
        except OSError as e:
            log.warning(f"cache flush failed (will retry next flush): {e}")


def _thumbnail_session_name(session_name: str | None = None) -> str | None:
    if not session_name:
        return None
    normalized = os.path.basename(str(session_name).strip().rstrip("\\/"))
    if not normalized or normalized in (".", ".."):
        return None
    return normalized


def thumbnail_dir(session_name: str | None = None) -> str:
    normalized = _thumbnail_session_name(session_name)
    if not normalized:
        return THUMBNAILS_DIR
    return os.path.join(THUMBNAILS_DIR, normalized)


def thumbnail_path(sha: str, session_name: str | None = None) -> str:
    return os.path.join(thumbnail_dir(session_name), f"{sha}.jpg")


def legacy_thumbnail_path(sha: str) -> str:
    return os.path.join(THUMBNAILS_DIR, f"{sha}.jpg")


def resolve_thumbnail_path(sha: str, session_name: str | None = None) -> str:
    preferred = thumbnail_path(sha, session_name)
    if os.path.isfile(preferred):
        return preferred
    return legacy_thumbnail_path(sha)


def has_thumbnail(sha: str, session_name: str | None = None) -> bool:
    return os.path.isfile(resolve_thumbnail_path(sha, session_name))


def write_thumbnail(sha: str, source_image_path: str, session_name: str | None = None) -> str:
    """Generate (if missing) and write a JPEG thumbnail for the given file. Returns its path."""
    out_dir = thumbnail_dir(session_name)
    os.makedirs(out_dir, exist_ok=True)
    out = thumbnail_path(sha, session_name)
    if os.path.isfile(out):
        return out
    with Image.open(source_image_path) as img:
        # Bake EXIF orientation into the pixels so the thumbnail looks upright
        # in the browser without relying on EXIF being preserved on save (PIL
        # drops it by default), which would otherwise show phone portraits
        # sideways in the gallery.
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        img.save(out, format="JPEG", quality=85)
    return out


def stats() -> dict:
    _load()
    thumbnails_cached = 0
    for _root, _dirs, files in os.walk(THUMBNAILS_DIR):
        thumbnails_cached += sum(1 for name in files if name.lower().endswith(".jpg"))
    with _lock:
        return {
            "detections_cached": len(_detections),
            "thumbnails_cached": thumbnails_cached,
        }
