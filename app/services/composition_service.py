import math
import os
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.config import (
    DEFAULT_COMPOSE_FIT_MODE,
    DEFAULT_COMPOSE_VERTICAL_ALIGN,
    DEFAULT_TEMPLATE_NAME,
    OUTPUT_DIR,
    PRINT_DPI,
    TEMPLATES_DIR,
)

SUPPORTED_TEMPLATE_EXTS = {".jpg", ".jpeg", ".png"}
FIT_MODES = {"cover", "contain"}
VERTICAL_ALIGNS = {"top", "center", "bottom"}
CONTAIN_BACKGROUND_DARKNESS = 0.72
CONTAIN_BACKGROUND_BLUR_DIVISOR = 28


def _detect_footer_start(template: Image.Image) -> int:
    width, height = template.size
    for y in range(height):
        row = template.crop((0, y, width, y + 1))
        if row.getbbox() is not None:
            return y
    return height


def _template_label(filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    if stem.lower().startswith("template "):
        stem = stem[9:]
    return " ".join(part.capitalize() for part in stem.split()) or filename


def _default_template_path() -> Path:
    return Path(TEMPLATES_DIR) / DEFAULT_TEMPLATE_NAME


def _template_spec_from_path(path: Path) -> dict:
    with Image.open(path) as template:
        width, height = template.size
        footer_start = _detect_footer_start(template.convert("RGBA"))
        dpi = template.info.get("dpi", (PRINT_DPI, PRINT_DPI))
    return {
        "name": path.name,
        "label": _template_label(path.name),
        "width": width,
        "height": height,
        "photo_area_height": footer_start,
        "footer_height": height - footer_start,
        "dpi": [int(round(dpi[0])), int(round(dpi[1]))],
        "is_default": True,
    }


def list_templates() -> list[dict]:
    path = _default_template_path()
    if not path.exists():
        raise ValueError(f"Template padrao nao encontrado: {DEFAULT_TEMPLATE_NAME}")
    if path.suffix.lower() not in SUPPORTED_TEMPLATE_EXTS:
        raise ValueError(f"Template padrao invalido: {DEFAULT_TEMPLATE_NAME}")
    return [_template_spec_from_path(path)]


def get_template_spec(template_name: str | None = None) -> dict:
    templates = list_templates()
    if not templates:
        raise ValueError("Nenhum template disponivel em footer_template/")

    if template_name:
        if template_name != DEFAULT_TEMPLATE_NAME:
            raise ValueError(f"Template invalido: {template_name}")
    return templates[0]


def _vertical_offset(container_h: int, content_h: int, vertical_align: str) -> int:
    if vertical_align == "top":
        return 0
    if vertical_align == "bottom":
        return max(0, container_h - content_h)
    return max(0, (container_h - content_h) // 2)


def _contain_resize(source: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = source.size
    scale = min(target_w / src_w, target_h / src_h)
    resized_w = max(1, int(round(src_w * scale)))
    resized_h = max(1, int(round(src_h * scale)))
    return source.resize((resized_w, resized_h), Image.LANCZOS)


def _cover_crop(
    source: Image.Image,
    target_w: int,
    target_h: int,
    vertical_align: str,
) -> Image.Image:
    src_w, src_h = source.size
    scale = max(target_w / src_w, target_h / src_h)
    resized_w = max(1, int(math.ceil(src_w * scale)))
    resized_h = max(1, int(math.ceil(src_h * scale)))
    resized = source.resize((resized_w, resized_h), Image.LANCZOS)
    offset_x = max(0, (resized_w - target_w) // 2)
    offset_y = _vertical_offset(resized_h, target_h, vertical_align)
    return resized.crop((offset_x, offset_y, offset_x + target_w, offset_y + target_h))


def _contain_with_fill(
    source: Image.Image,
    target_w: int,
    target_h: int,
    vertical_align: str,
) -> Image.Image:
    background = _cover_crop(source, target_w, target_h, vertical_align)
    blur_radius = max(18, min(target_w, target_h) // CONTAIN_BACKGROUND_BLUR_DIVISOR)
    background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    background = ImageEnhance.Brightness(background).enhance(CONTAIN_BACKGROUND_DARKNESS)

    foreground = _contain_resize(source, target_w, target_h)
    offset_x = max(0, (target_w - foreground.width) // 2)
    offset_y = _vertical_offset(target_h, foreground.height, vertical_align)

    canvas = background.copy()
    canvas.paste(foreground, (offset_x, offset_y))
    return canvas


def _fit_photo(
    source: Image.Image,
    target_w: int,
    target_h: int,
    fit_mode: str,
    vertical_align: str,
) -> Image.Image:
    if fit_mode == "contain":
        return _contain_with_fill(source, target_w, target_h, vertical_align)
    return _cover_crop(source, target_w, target_h, vertical_align)


def compose_photo(
    photo_path: str,
    orientation: str = "landscape",
    face_locations: list | None = None,
    template_name: str | None = None,
    fit_mode: str = DEFAULT_COMPOSE_FIT_MODE,
    vertical_align: str = DEFAULT_COMPOSE_VERTICAL_ALIGN,
) -> Image.Image:
    """Compose a photo into the selected template canvas."""
    del orientation, face_locations
    fit_mode = fit_mode if fit_mode in FIT_MODES else DEFAULT_COMPOSE_FIT_MODE
    vertical_align = vertical_align if vertical_align in VERTICAL_ALIGNS else DEFAULT_COMPOSE_VERTICAL_ALIGN
    template = get_template_spec(template_name)

    with Image.open(template_path(template["name"])) as template_img:
        template_layer = template_img.convert("RGBA")
    with Image.open(photo_path) as source_img:
        source = ImageOps.exif_transpose(source_img).convert("RGB")
        fitted = _fit_photo(
            source,
            target_w=template["width"],
            target_h=template["photo_area_height"],
            fit_mode=fit_mode,
            vertical_align=vertical_align,
        )
    canvas = Image.new("RGBA", template_layer.size, (0, 0, 0, 255))
    canvas.paste(fitted.convert("RGBA"), (0, 0))
    canvas.alpha_composite(template_layer)
    return canvas.convert("RGB")


def template_path(template_name: str | None = None) -> str:
    if template_name and template_name != DEFAULT_TEMPLATE_NAME:
        raise ValueError(f"Template invalido: {template_name}")
    return os.path.join(TEMPLATES_DIR, DEFAULT_TEMPLATE_NAME)


def save_composed(
    image: Image.Image,
    original_path: str,
    session_name: str | None = None,
    variant_suffix: str | None = None,
    dpi: tuple[int, int] | None = None,
) -> str:
    """Save a composed image to the output directory."""
    filename = os.path.basename(original_path)
    name, _ext = os.path.splitext(filename)
    if variant_suffix:
        safe_suffix = variant_suffix.replace(" ", "_").replace("/", "_").replace("\\", "_")
        name = f"{name}_composed_{safe_suffix}"
    else:
        name = f"{name}_composed"

    if session_name:
        target_dir = os.path.join(OUTPUT_DIR, session_name)
        os.makedirs(target_dir, exist_ok=True)
    else:
        target_dir = OUTPUT_DIR

    output_path = os.path.join(target_dir, f"{name}.jpg")
    image.save(output_path, "JPEG", quality=95, dpi=dpi or (PRINT_DPI, PRINT_DPI))
    return output_path
