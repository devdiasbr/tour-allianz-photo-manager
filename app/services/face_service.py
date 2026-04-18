import os
import io
import glob
import json
import hashlib
import logging
import numpy as np
import face_recognition
import cv2
from PIL import Image, ImageOps
from dataclasses import dataclass
from app.config import (
    FACE_TOLERANCE, FACE_DETECTION_MODEL, THUMBNAIL_SIZE,
    FACE_SCAN_MAX_WIDTH, FACE_UPSAMPLE,
)

log = logging.getLogger(__name__)


@dataclass
class MatchResult:
    file_path: str
    thumbnail_bytes: bytes
    best_distance: float
    face_locations: list


def encode_faces(image_rgb: np.ndarray) -> list[np.ndarray]:
    """Detect and encode all faces in an RGB image (e.g. from webcam)."""
    # Try with upsample for better detection of smaller faces
    locations = face_recognition.face_locations(
        image_rgb, number_of_times_to_upsample=FACE_UPSAMPLE, model=FACE_DETECTION_MODEL
    )
    if not locations:
        return []
    encodings = face_recognition.face_encodings(image_rgb, locations)
    return encodings


def get_face_locations(image_rgb: np.ndarray) -> list[tuple]:
    """Get face bounding boxes: list of (top, right, bottom, left)."""
    return face_recognition.face_locations(
        image_rgb, number_of_times_to_upsample=FACE_UPSAMPLE, model=FACE_DETECTION_MODEL
    )


def get_detection_diagnostics(
    image_rgb: np.ndarray,
    upsample: int = FACE_UPSAMPLE,
    model: str = FACE_DETECTION_MODEL,
) -> dict:
    locations = face_recognition.face_locations(
        image_rgb, number_of_times_to_upsample=upsample, model=model
    )
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


def _make_thumbnail(image_path: str) -> bytes:
    """Create a JPEG thumbnail for grid display."""
    with Image.open(image_path) as img:
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


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
) -> dict:
    passes = []
    matched = False
    best_dist = float("inf")

    small, scale = _resize_for_scan(image, FACE_SCAN_MAX_WIDTH)
    locations = face_recognition.face_locations(
        small, number_of_times_to_upsample=upsample, model=FACE_DETECTION_MODEL
    )
    diag_small = get_detection_diagnostics(small, upsample=upsample, model=FACE_DETECTION_MODEL)
    passes.append({
        "variant": variant_name,
        "stage": "resized",
        "resolution": f"{small.shape[1]}x{small.shape[0]}",
        **diag_small,
    })

    final_locations = locations
    final_scale = scale

    if locations and reference_encodings:
        encodings = face_recognition.face_encodings(small, locations)
        for enc in encodings:
            distances = face_recognition.face_distance(reference_encodings, enc)
            min_dist = float(np.min(distances))
            if min_dist < best_dist:
                best_dist = min_dist
            if min_dist <= tolerance:
                matched = True

    if not matched and scale < 1.0:
        full_upsample = max(1, upsample - 1)
        full_locations = face_recognition.face_locations(
            image, number_of_times_to_upsample=full_upsample, model=FACE_DETECTION_MODEL
        )
        diag_full = get_detection_diagnostics(image, upsample=full_upsample, model=FACE_DETECTION_MODEL)
        passes.append({
            "variant": variant_name,
            "stage": "full",
            "resolution": f"{image.shape[1]}x{image.shape[0]}",
            **diag_full,
        })
        if full_locations and reference_encodings:
            full_encodings = face_recognition.face_encodings(image, full_locations)
            for enc in full_encodings:
                distances = face_recognition.face_distance(reference_encodings, enc)
                min_dist = float(np.min(distances))
                if min_dist < best_dist:
                    best_dist = min_dist
                if min_dist <= tolerance:
                    matched = True
            if matched:
                final_locations = full_locations
                final_scale = 1.0

    return {
        "matched": matched,
        "best_dist": best_dist,
        "final_locations": final_locations,
        "final_scale": final_scale,
        "passes": passes,
    }


def scan_session(
    session_path: str,
    reference_encodings: list[np.ndarray],
    tolerance: float = FACE_TOLERANCE,
    progress_callback=None,
) -> list[MatchResult]:
    """Scan all photos in a session folder and return matches.

    A photo matches if ANY face in it matches ANY reference encoding.
    Uses two-pass approach: first at normal scale, then at higher res for missed faces.
    """
    # Use a set to deduplicate (Windows is case-insensitive)
    seen = set()
    photo_files = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        for f in glob.glob(os.path.join(session_path, ext)):
            normalized = os.path.normcase(os.path.abspath(f))
            if normalized not in seen:
                seen.add(normalized)
                photo_files.append(f)
    photo_files.sort()

    results = []
    total = len(photo_files)
    log.info(f"Scanning {total} photos with tolerance={tolerance}, max_width={FACE_SCAN_MAX_WIDTH}, upsample={FACE_UPSAMPLE}")

    for i, photo_path in enumerate(photo_files):
        try:
            image, metadata = load_image_rgb_with_metadata(photo_path)
            sha12 = hash_file_sha12(photo_path)

            base_result = _scan_variant(
                image=image,
                reference_encodings=reference_encodings,
                tolerance=tolerance,
                upsample=FACE_UPSAMPLE,
                variant_name="base",
            )

            selected_result = base_result
            enhanced_result = None
            has_any_face = any(p["faces_detected"] > 0 for p in base_result["passes"])

            if not base_result["matched"] and not has_any_face:
                enhanced_image = enhance_for_detection(image)
                enhanced_result = _scan_variant(
                    image=enhanced_image,
                    reference_encodings=reference_encodings,
                    tolerance=tolerance,
                    upsample=min(FACE_UPSAMPLE + 1, 3),
                    variant_name="clahe",
                )
                if enhanced_result["matched"] or any(p["faces_detected"] > 0 for p in enhanced_result["passes"]):
                    selected_result = enhanced_result

            matched = selected_result["matched"]
            best_dist = selected_result["best_dist"]
            final_locations = selected_result["final_locations"]
            final_scale = selected_result["final_scale"]

            diagnostic_payload = {
                "file": os.path.basename(photo_path),
                "hash": sha12,
                "capture_timestamp": metadata.get("capture_timestamp"),
                "orientation_exif": metadata.get("orientation_exif"),
                "rotated": metadata.get("rotated"),
                "size": metadata.get("size"),
                "matched": matched,
                "best_distance": None if best_dist == float("inf") else round(best_dist, 6),
                "passes": base_result["passes"] + ([] if not enhanced_result else enhanced_result["passes"]),
            }
            log.info("SCAN_DIAG %s", json.dumps(diagnostic_payload, ensure_ascii=False))

            if matched:
                orig_locations = [
                    (int(t / final_scale), int(r / final_scale), int(b / final_scale), int(l / final_scale))
                    for t, r, b, l in final_locations
                ]
                thumb = _make_thumbnail(photo_path)
                results.append(MatchResult(
                    file_path=photo_path,
                    thumbnail_bytes=thumb,
                    best_distance=best_dist,
                    face_locations=orig_locations,
                ))
                log.info(f"  MATCH: {os.path.basename(photo_path)} (dist={best_dist:.3f})")
            else:
                visible_faces = max((p["faces_detected"] for p in diagnostic_payload["passes"]), default=0)
                if visible_faces > 0:
                    if best_dist == float("inf"):
                        log.info(f"  NO MATCH: {os.path.basename(photo_path)} (best_dist=inf, faces={visible_faces})")
                    else:
                        log.info(f"  NO MATCH: {os.path.basename(photo_path)} (best_dist={best_dist:.3f}, faces={visible_faces})")
                else:
                    log.info(f"  NO FACE: {os.path.basename(photo_path)}")

        except Exception as e:
            log.warning(f"  ERROR: {os.path.basename(photo_path)}: {e}")

        if progress_callback:
            progress_callback(i + 1, total)

    # Sort by best match (lowest distance first)
    results.sort(key=lambda r: r.best_distance)
    log.info(f"Scan complete: {len(results)}/{total} matches")
    return results
