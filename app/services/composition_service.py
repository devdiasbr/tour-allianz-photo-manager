import os
from PIL import Image
from app.config import (
    TEMPLATE_PATH,
    FOOTER_Y_START,
    LANDSCAPE_W,
    LANDSCAPE_H,
    PORTRAIT_W,
    PORTRAIT_H,
    OUTPUT_DIR,
    PRINT_DPI,
)


def _load_footer_strip() -> Image.Image:
    """Extract the footer bar from the template (bottom strip)."""
    template = Image.open(TEMPLATE_PATH)
    footer = template.crop((0, FOOTER_Y_START, template.width, template.height))
    return footer


def compose_photo(
    photo_path: str,
    orientation: str = "landscape",
    face_locations: list | None = None,
) -> Image.Image:
    """Compose a photo with the footer template at print resolution.

    Args:
        photo_path: Path to the source photo.
        orientation: "landscape" (20x15cm) or "portrait" (15x20cm).
        face_locations: Optional list of (top, right, bottom, left) for smart crop.

    Returns:
        Composed PIL Image at 300 DPI print resolution.
    """
    footer_strip = _load_footer_strip()  # 800 x 99
    source = Image.open(photo_path)

    if orientation == "landscape":
        target_w, target_h = LANDSCAPE_W, LANDSCAPE_H
    else:
        target_w, target_h = PORTRAIT_W, PORTRAIT_H

    # Scale footer strip to target width
    footer_scale = target_w / footer_strip.width
    footer_h = int(footer_strip.height * footer_scale)
    footer_resized = footer_strip.resize((target_w, footer_h), Image.LANCZOS)

    # Photo area dimensions
    photo_area_h = target_h - footer_h
    photo_area_w = target_w

    # Resize source to fill photo area (cover mode: fill, then crop)
    src_w, src_h = source.size
    scale_w = photo_area_w / src_w
    scale_h = photo_area_h / src_h
    scale = max(scale_w, scale_h)  # cover: use the larger scale

    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    resized = source.resize((new_w, new_h), Image.LANCZOS)

    # Smart crop based on face locations
    if new_w > photo_area_w:
        # Horizontal crop needed
        if face_locations:
            face_center_x = _face_center_x(face_locations, src_w, scale)
            left = max(0, min(face_center_x - photo_area_w // 2, new_w - photo_area_w))
        else:
            left = (new_w - photo_area_w) // 2
        resized = resized.crop((left, 0, left + photo_area_w, new_h))

    if new_h > photo_area_h:
        # Vertical crop needed
        if face_locations:
            face_center_y = _face_center_y(face_locations, src_h, scale)
            top = max(0, min(face_center_y - photo_area_h // 2, new_h - photo_area_h))
        else:
            top = (new_h - photo_area_h) // 2
        resized = resized.crop((0, top, resized.width, top + photo_area_h))

    # Ensure exact dimensions after crop
    resized = resized.resize((photo_area_w, photo_area_h), Image.LANCZOS)

    # Compose: photo on top, footer on bottom
    canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    canvas.paste(resized, (0, 0))
    canvas.paste(footer_resized, (0, photo_area_h))

    return canvas


def _face_center_x(face_locations, original_w, scale):
    """Calculate the horizontal center of detected faces after scaling."""
    centers = [(l + r) / 2 * scale for (t, r, b, l) in face_locations]
    return int(sum(centers) / len(centers))


def _face_center_y(face_locations, original_h, scale):
    """Calculate the vertical center of detected faces after scaling."""
    centers = [(t + b) / 2 * scale for (t, r, b, l) in face_locations]
    return int(sum(centers) / len(centers))


def save_composed(image: Image.Image, original_path: str) -> str:
    """Save a composed image to the output directory.

    Returns the output file path.
    """
    filename = os.path.basename(original_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(OUTPUT_DIR, f"{name}_composed{ext}")
    image.save(output_path, "JPEG", quality=95, dpi=(PRINT_DPI, PRINT_DPI))
    return output_path
