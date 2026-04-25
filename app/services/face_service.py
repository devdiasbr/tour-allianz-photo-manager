import os
import io
import glob
import json
import time
import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from app.services.face_models import prepare_face_recognition_models

prepare_face_recognition_models()
import face_recognition
import cv2
from PIL import Image, ImageOps
from dataclasses import dataclass
from app.config import (
    FACE_TOLERANCE, FACE_DETECTION_MODEL, THUMBNAIL_SIZE,
    FACE_SCAN_MAX_WIDTH, FACE_UPSAMPLE, FACE_SCAN_MODE, FACE_SCAN_WORKERS,
)
from app.services import cache as encoding_cache

log = logging.getLogger(__name__)


@dataclass
class MatchResult:
    file_path: str
    sha: str
    best_distance: float
    face_locations: list


def encode_faces(image_rgb: np.ndarray) -> list[np.ndarray]:
    """Detect and encode all faces in an RGB image (e.g. from webcam)."""
    locations = face_recognition.face_locations(
        image_rgb, number_of_times_to_upsample=FACE_UPSAMPLE, model=FACE_DETECTION_MODEL
    )
    if not locations:
        return []
    return face_recognition.face_encodings(image_rgb, locations)


def get_face_locations(image_rgb: np.ndarray) -> list[tuple]:
    """Get face bounding boxes: list of (top, right, bottom, left)."""
    return face_recognition.face_locations(
        image_rgb, number_of_times_to_upsample=FACE_UPSAMPLE, model=FACE_DETECTION_MODEL
    )


def diagnostics_from_locations(image_rgb: np.ndarray, locations: list) -> dict:
    """Pure-math diagnostics derived from already-computed face locations.

    Splitting this from detection lets `_scan_variant` avoid running
    face_recognition.face_locations twice per pass (once for matching, once
    for the diagnostic log) — that duplicate call dominated scan time.
    """
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    h, w = image_rgb.shape[:2]
    image_area = max(1, h * w)
    largest_face_ratio = 0.0
    if locations:
        largest_face_ratio = max(((b - t) * (r - l)) / image_area for t, r, b, l in locations)
    confidence_score = min(1.0, largest_face_ratio * 8.0 + min(0.2, sharpness / 1200.0))

    return {
        "faces_detected": int(len(locations)),
        "detector_confidence": round(confidence_score, 4),
        "largest_face_ratio": round(largest_face_ratio, 6),
        "brightness": round(brightness, 2),
        "sharpness": round(sharpness, 2),
    }


def get_detection_diagnostics(
    image_rgb: np.ndarray,
    upsample: int = FACE_UPSAMPLE,
    model: str = FACE_DETECTION_MODEL,
) -> dict:
    """Convenience wrapper: detect faces and return diagnostics.

    Prefer `diagnostics_from_locations` when you already have detections.
    """
    locations = face_recognition.face_locations(
        image_rgb, number_of_times_to_upsample=upsample, model=model
    )
    return diagnostics_from_locations(image_rgb, locations)


def load_image_rgb_with_metadata(image_path: str) -> tuple[np.ndarray, dict]:
    with Image.open(image_path) as img:
        exif = img.getexif()
        orientation = exif.get(274)
        capture_timestamp = exif.get(36867) or exif.get(306)
        width = img.width
        height = img.height
        img_fixed = ImageOps.exif_transpose(img).convert("RGB")
        image_rgb = np.array(img_fixed)
    return image_rgb, {
        "orientation_exif": orientation,
        "capture_timestamp": capture_timestamp,
        "size": f"{width}x{height}",
        "rotated": orientation in (3, 6, 8),
    }


def hash_file_sha12(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def enhance_for_detection(image_rgb: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2YCrCb)
    ycrcb[:, :, 0] = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(ycrcb[:, :, 0])
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2RGB)


def _resize_for_scan(image: np.ndarray, max_width: int) -> tuple[np.ndarray, float]:
    """Resize image for scanning, return (resized_image, scale_factor)."""
    h, w = image.shape[:2]
    if w > max_width:
        scale = max_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale
    return image, 1.0


def _scan_variant(
    image: np.ndarray,
    reference_encodings: list[np.ndarray],
    tolerance: float,
    upsample: int,
    variant_name: str,
    sha: str,
) -> dict:
    """Run one detection pipeline (resized → full-res escalation) and return
    detection + encodings + match outcome. Photo-level caching happens one
    layer up in `_process_one_photo`, so this routine always recomputes."""
    passes = []
    matched = False
    best_dist = float("inf")
    needs_enc = bool(reference_encodings)

    small, scale = _resize_for_scan(image, FACE_SCAN_MAX_WIDTH)
    locations = face_recognition.face_locations(
        small, number_of_times_to_upsample=upsample, model=FACE_DETECTION_MODEL
    )
    # Detection runs on the resized image (where HOG is fast), but encoding
    # MUST run on the full-resolution crops — small-scale encodings produce
    # muddy embeddings that collapse distinctions across age/gender/ethnicity.
    # Encoding is cheap once boxes are known, so we pay basically nothing to
    # keep quality. Scale the boxes back to original coordinates first.
    encodings: list[np.ndarray] = []
    if locations and needs_enc:
        if scale < 1.0:
            enc_locations = [
                (int(t / scale), int(r / scale), int(b / scale), int(l / scale))
                for (t, r, b, l) in locations
            ]
            encodings = face_recognition.face_encodings(image, enc_locations)
        else:
            encodings = face_recognition.face_encodings(small, locations)
    diag_small = diagnostics_from_locations(small, locations)
    passes.append({
        "variant": variant_name,
        "stage": "resized",
        "resolution": f"{small.shape[1]}x{small.shape[0]}",
        **diag_small,
    })

    final_locations = locations
    final_scale = scale
    final_encodings = encodings

    if encodings:
        for enc in encodings:
            distances = face_recognition.face_distance(reference_encodings, enc)
            min_dist = float(np.min(distances))
            if min_dist < best_dist:
                best_dist = min_dist
            if min_dist <= tolerance:
                matched = True

    # Escalate to full-resolution whenever the resized pass didn't match.
    # Resized encodings are noticeably less accurate, so even when faces were
    # detected at low res it's worth re-encoding at full res for a tighter
    # distance against the reference. Also, full-res detection sometimes finds
    # faces the resized pass missed entirely.
    # In "fast" mode this escalation is skipped — full-res HOG dominates
    # wall-clock on big folders where most photos are non-matches. Flip the
    # FACE_SCAN_MODE env var to "accurate" to re-enable.
    if not matched and scale < 1.0 and FACE_SCAN_MODE == "accurate":
        full_upsample = max(1, upsample - 1) if upsample > 1 else upsample
        full_locations = face_recognition.face_locations(
            image, number_of_times_to_upsample=full_upsample, model=FACE_DETECTION_MODEL
        )
        full_encodings: list[np.ndarray] = (
            face_recognition.face_encodings(image, full_locations) if full_locations and needs_enc else []
        )
        diag_full = diagnostics_from_locations(image, full_locations)
        passes.append({
            "variant": variant_name,
            "stage": "full",
            "resolution": f"{image.shape[1]}x{image.shape[0]}",
            **diag_full,
        })
        if full_encodings:
            for enc in full_encodings:
                distances = face_recognition.face_distance(reference_encodings, enc)
                min_dist = float(np.min(distances))
                if min_dist < best_dist:
                    best_dist = min_dist
                if min_dist <= tolerance:
                    matched = True
        # Always promote full-res detection results to the canonical output
        # when full-res actually found faces — those encodings are higher
        # quality and what we want in the per-photo cache, regardless of
        # whether they matched the *current* reference.
        if full_locations:
            final_locations = full_locations
            final_scale = 1.0
            final_encodings = full_encodings

    return {
        "matched": matched,
        "best_dist": best_dist,
        "final_locations": final_locations,
        "final_scale": final_scale,
        "final_encodings": final_encodings,
        "passes": passes,
    }


def _photo_cache_key(sha: str) -> str:
    """Per-photo cache key. Includes tunables that affect detection so a config
    change automatically invalidates stale entries. The trailing version tag
    bumps when the encoding pipeline itself changes (e.g. encoding moved from
    resized crops to full-resolution crops); old entries become misses."""
    return f"photo:{sha}:u{FACE_UPSAMPLE}:w{FACE_SCAN_MAX_WIDTH}:m{FACE_DETECTION_MODEL}:s{FACE_SCAN_MODE}:v2"


def _match_against_reference(
    encodings: list[np.ndarray],
    reference_encodings: list[np.ndarray],
    tolerance: float,
) -> tuple[bool, float]:
    if not encodings or not reference_encodings:
        return False, float("inf")
    matched = False
    best = float("inf")
    for enc in encodings:
        distances = face_recognition.face_distance(reference_encodings, enc)
        d = float(np.min(distances))
        if d < best:
            best = d
        if d <= tolerance:
            matched = True
    return matched, best


def _process_one_photo(
    photo_path: str,
    reference_encodings: list[np.ndarray],
    tolerance: float,
) -> tuple[str, dict]:
    """Worker body for a single photo. Returns (photo_path, payload).

    Fast path: hash the file (no decode), check the per-photo cache. On hit
    we already have the encodings + original-resolution face boxes — just
    match them against the current reference set and return. Re-opening a
    folder that was previously scanned costs only the file hash per photo.

    Slow path (cache miss): decode the image, run the base/full/CLAHE
    pipeline, persist the best-available encodings + boxes for next time.
    """
    try:
        sha12 = hash_file_sha12(photo_path)
        key = _photo_cache_key(sha12)
        cached = encoding_cache.get_detection(key)

        if cached is not None:
            encs = cached.get("encs", []) or []
            orig_locs = cached.get("locs", []) or []
            matched, best_dist = _match_against_reference(encs, reference_encodings, tolerance)
            return photo_path, {
                "ok": True,
                "sha": sha12,
                "source": "cache",
                "matched": matched,
                "best_dist": best_dist,
                "orig_locations": orig_locs,
                "faces_detected": len(encs),
                "passes": [{"variant": "cache", "stage": "hit",
                            "faces_detected": len(encs),
                            "resolution": "(from cache)"}],
                "metadata": {},
            }

        image, metadata = load_image_rgb_with_metadata(photo_path)

        base_result = _scan_variant(
            image=image,
            reference_encodings=reference_encodings,
            tolerance=tolerance,
            upsample=FACE_UPSAMPLE,
            variant_name="base",
            sha=sha12,
        )

        selected_result = base_result
        enhanced_result = None

        # Run CLAHE whenever base didn't match — even when base detected faces.
        # CLAHE-enhanced encodings are sometimes a better fit for low-light or
        # backlit subjects, and the cost is one extra pipeline run on the
        # cache-miss path only (cache hits skip this entirely).
        # Skipped in "fast" mode: CLAHE+upsample+1 is expensive and only helps
        # the low-light minority of event photos.
        if not base_result["matched"] and FACE_SCAN_MODE == "accurate":
            enhanced_image = enhance_for_detection(image)
            enhanced_result = _scan_variant(
                image=enhanced_image,
                reference_encodings=reference_encodings,
                tolerance=tolerance,
                upsample=min(FACE_UPSAMPLE + 1, 3),
                variant_name="clahe",
                sha=sha12,
            )
            # Prefer CLAHE result if it matched, or if it found more faces
            # (better recall to cache for future scans).
            base_face_count = len(base_result["final_encodings"])
            clahe_face_count = len(enhanced_result["final_encodings"])
            if enhanced_result["matched"] or clahe_face_count > base_face_count:
                selected_result = enhanced_result

        # Compute original-resolution boxes once and cache them. Also cache
        # the encodings (or [] for "scanned, no face") so a rescan with any
        # reference set can match instantly.
        final_locations = selected_result["final_locations"]
        final_scale = selected_result["final_scale"]
        orig_locs = [
            (int(t / final_scale), int(r / final_scale), int(b / final_scale), int(l / final_scale))
            for (t, r, b, l) in final_locations
        ]

        encs_used = selected_result["final_encodings"]
        encoding_cache.put_detection(key, orig_locs, encs_used)

        return photo_path, {
            "ok": True,
            "sha": sha12,
            "source": "computed",
            "matched": selected_result["matched"],
            "best_dist": selected_result["best_dist"],
            "orig_locations": orig_locs,
            "faces_detected": len(encs_used),
            "passes": base_result["passes"] + ([] if not enhanced_result else enhanced_result["passes"]),
            "metadata": metadata,
        }
    except Exception as e:
        return photo_path, {"ok": False, "error": str(e)}


def scan_session(
    session_path: str,
    reference_encodings: list[np.ndarray],
    tolerance: float = FACE_TOLERANCE,
    progress_callback=None,
) -> list[MatchResult]:
    """Scan all photos in a session folder and return matches.

    A photo matches if ANY face in it matches ANY reference encoding.
    Sequential by default — dlib HOG detection crashes natively when called
    from multiple threads in this setup (Windows + dlib 19.24). Encodings
    are memoized on disk per-photo by sha12+config, so rescans cost only
    a file hash per photo. Set env `FACE_SCAN_WORKERS=N` (N>=2) to opt in
    to threaded scanning at your own risk.
    """
    seen = set()
    photo_files = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        for f in glob.glob(os.path.join(session_path, ext)):
            normalized = os.path.normcase(os.path.abspath(f))
            if normalized not in seen:
                seen.add(normalized)
                photo_files.append(f)
    photo_files.sort()

    total = len(photo_files)
    workers = max(1, min(FACE_SCAN_WORKERS, total or 1))
    scan_started = time.perf_counter()
    log.info(
        f"Scanning {total} photos workers={workers} mode={FACE_SCAN_MODE} "
        f"tolerance={tolerance} max_width={FACE_SCAN_MAX_WIDTH} "
        f"upsample={FACE_UPSAMPLE}"
    )

    results: list[MatchResult] = []
    cache_hits = {"n": 0}
    session_name = os.path.basename(os.path.normpath(session_path))

    def _consume(photo_path: str, payload: dict, done_n: int) -> None:
        if not payload["ok"]:
            log.warning(f"  ERROR: {os.path.basename(photo_path)}: {payload['error']}")
            return

        sha12 = payload["sha"]
        metadata = payload.get("metadata") or {}
        matched = payload["matched"]
        best_dist = payload["best_dist"]
        orig_locations = payload["orig_locations"]
        source = payload.get("source", "computed")
        if source == "cache":
            cache_hits["n"] += 1

        diagnostic_payload = {
            "file": os.path.basename(photo_path),
            "hash": sha12,
            "source": source,
            "capture_timestamp": metadata.get("capture_timestamp"),
            "orientation_exif": metadata.get("orientation_exif"),
            "rotated": metadata.get("rotated"),
            "size": metadata.get("size"),
            "matched": matched,
            "best_distance": None if best_dist == float("inf") else round(best_dist, 6),
            "passes": payload["passes"],
        }
        log.info("SCAN_DIAG %s", json.dumps(diagnostic_payload, ensure_ascii=False))

        if matched:
            try:
                encoding_cache.write_thumbnail(sha12, photo_path, session_name=session_name)
            except Exception:
                log.warning(f"thumbnail write failed for {os.path.basename(photo_path)}", exc_info=True)
            results.append(MatchResult(
                file_path=photo_path,
                sha=sha12,
                best_distance=best_dist,
                face_locations=orig_locations,
            ))
            tag = "MATCH*" if source == "cache" else "MATCH"
            log.info(f"  {tag} ({done_n}/{total}): {os.path.basename(photo_path)} (dist={best_dist:.3f})")
        else:
            visible_faces = payload.get("faces_detected", 0)
            if visible_faces > 0:
                if best_dist == float("inf"):
                    log.info(f"  NO MATCH ({done_n}/{total}): {os.path.basename(photo_path)} (best_dist=inf, faces={visible_faces})")
                else:
                    log.info(f"  NO MATCH ({done_n}/{total}): {os.path.basename(photo_path)} (best_dist={best_dist:.3f}, faces={visible_faces})")
            else:
                log.info(f"  NO FACE ({done_n}/{total}): {os.path.basename(photo_path)}")

    if workers <= 1:
        for i, photo_path in enumerate(photo_files, 1):
            try:
                _, payload = _process_one_photo(photo_path, reference_encodings, tolerance)
                _consume(photo_path, payload, i)
            except Exception:
                log.exception(f"  CRASH: {os.path.basename(photo_path)}")
            if progress_callback:
                try:
                    progress_callback(i, total)
                except Exception:
                    log.debug("progress_callback raised; ignoring", exc_info=True)
            # Persist incrementally so a mid-scan crash doesn't lose all work.
            if i % 5 == 0:
                try:
                    encoding_cache.flush()
                except Exception:
                    log.warning("encoding_cache.flush failed mid-scan", exc_info=True)
    else:
        progress_lock = threading.Lock()
        done_count = {"n": 0}
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="photo") as pool:
            futures = {
                pool.submit(_process_one_photo, p, reference_encodings, tolerance): p
                for p in photo_files
            }
            for fut in as_completed(futures):
                photo_path = futures[fut]
                try:
                    payload = fut.result()[1]
                except Exception:
                    log.exception(f"  CRASH: {os.path.basename(photo_path)}")
                    payload = {"ok": False, "error": "worker crashed"}
                with progress_lock:
                    done_count["n"] += 1
                    n = done_count["n"]
                _consume(photo_path, payload, n)
                if progress_callback:
                    try:
                        progress_callback(n, total)
                    except Exception:
                        log.debug("progress_callback raised; ignoring", exc_info=True)

    results.sort(key=lambda r: r.best_distance)
    try:
        encoding_cache.flush()
    except Exception:
        log.warning("encoding_cache.flush failed", exc_info=True)
    elapsed = time.perf_counter() - scan_started
    rate = (total / elapsed) if elapsed > 0 else 0.0
    log.info(
        f"Scan complete: {len(results)}/{total} matches "
        f"in {elapsed:.1f}s ({rate:.2f} photos/s, "
        f"cache_hits={cache_hits['n']}/{total}, workers={workers}, "
        f"mode={FACE_SCAN_MODE})"
    )
    return results
