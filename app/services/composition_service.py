import os
from PIL import Image, ImageOps
from app.config import (
    TEMPLATE_PATH,
    FOOTER_Y_START,
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
    """Compose a photo with the footer template at the photo's native size.

    The source photo is NOT resized or cropped — it's kept at its original
    pixel dimensions. The footer strip is scaled to match the photo's width
    and appended below, so the output canvas is `(photo_w, photo_h + footer_h)`.

    Args:
        photo_path: Path to the source photo.
        orientation: Kept for API compatibility — ignored (output orientation
            follows the photo's own aspect ratio).
        face_locations: Kept for API compatibility — ignored (no crop happens).

    Returns:
        Composed PIL Image with the photo's original dimensions plus footer.
    """
    footer_strip = _load_footer_strip()  # 800 x 99 in template px
    # Honor EXIF orientation so phone portraits aren't composed sideways.
    source = ImageOps.exif_transpose(Image.open(photo_path)).convert("RGB")

    src_w, src_h = source.size
    footer_h = int(footer_strip.height * (src_w / footer_strip.width))
    footer_resized = footer_strip.resize((src_w, footer_h), Image.LANCZOS)

    canvas = Image.new("RGB", (src_w, src_h + footer_h), (0, 0, 0))
    canvas.paste(source, (0, 0))
    canvas.paste(footer_resized, (0, src_h))

    return canvas


def save_composed(
    image: Image.Image,
    original_path: str,
    session_name: str | None = None,
) -> str:
    """Save a composed image to the output directory.

    When `session_name` is given, the file is placed in
    `OUTPUT_DIR/<session_name>/`, isolating outputs per event.
    Returns the output file path.
    """
    filename = os.path.basename(original_path)
    name, ext = os.path.splitext(filename)
    if session_name:
        target_dir = os.path.join(OUTPUT_DIR, session_name)
        os.makedirs(target_dir, exist_ok=True)
    else:
        target_dir = OUTPUT_DIR
    output_path = os.path.join(target_dir, f"{name}_composed{ext}")
    image.save(output_path, "JPEG", quality=95, dpi=(PRINT_DPI, PRINT_DPI))
    return output_path
