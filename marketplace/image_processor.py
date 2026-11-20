import io
import os
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageOps
from django.core.files.base import ContentFile

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def _load_watermark_font(size: int):
    """Loads a clean TrueType font available in Linux/Docker or Windows, falling back gracefully."""
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def process_and_watermark_image(
    uploaded_file,
    seller_name: str = "",
    add_watermark: bool = True,
    max_dimension: int = 1200,
    target_max_kb: int = 165,
):
    """
    Enterprise Jiji-Grade Image Pipeline:
1. Supports JPEG, PNG, WebP, and iPhone HEIC/HEIF photos automatically.
2. Fixes sideways phone camera rotation (EXIF transpose).
3. Resizes massive multi-MB photos to crisp 1200px max dimension.
4. Stamps a subtle, centered Jiji-style 'Posted on Naijasale / by Seller Name' watermark.
5. Compresses down to ultra-fast WebP (~85KB - 165KB) for instant page loads.
    """
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)

    # 1. Fix sideways iPhone / Samsung EXIF rotation
    img = ImageOps.exif_transpose(img)

    # Convert palette/RGBA to RGB cleanly (flattening transparency on white)
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 2. Smart resize while preserving exact aspect ratio
    width, height = img.size
    if max(width, height) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        width, height = img.size

    # 3. Centered Jiji-Style Watermark ("Posted on Naijasale" + Seller Name)
    if add_watermark:
        base_rgba = img.convert("RGBA")
        overlay = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Proportional font sizing so centered watermark looks clean and un-croppable
        primary_size = max(18, int(min(width, height) * 0.036))
        secondary_size = max(13, int(primary_size * 0.78))

        font_main = _load_watermark_font(primary_size)
        font_sub = _load_watermark_font(secondary_size)

        line1 = "Posted on Naijasale"
        clean_seller = (seller_name or "").strip()
        if len(clean_seller) > 26:
            clean_seller = clean_seller[:24].rstrip() + "..."
        line2 = f"by {clean_seller}" if clean_seller else ""

        bbox1 = draw.textbbox((0, 0), line1, font=font_main)
        w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]

        if line2:
            bbox2 = draw.textbbox((0, 0), line2, font=font_sub)
            w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
        else:
            w2, h2 = 0, 0

        line_gap = max(4, int(primary_size * 0.28))
        block_h = h1 + (line_gap + h2 if line2 else 0)

        # Center horizontally and vertically in the exact middle of the image
        x1 = max(8, (width - w1) // 2)
        y1 = max(8, (height - block_h) // 2)

        # Subtle drop shadow + semi-transparent light white text (like Jiji)
        shadow_alpha = 85
        text_alpha = 135

        draw.text((x1 + 1, y1 + 1), line1, font=font_main, fill=(0, 0, 0, shadow_alpha))
        draw.text((x1, y1), line1, font=font_main, fill=(255, 255, 255, text_alpha))

        if line2:
            x2 = max(8, (width - w2) // 2)
            y2 = y1 + h1 + line_gap
            draw.text((x2 + 1, y2 + 1), line2, font=font_sub, fill=(0, 0, 0, shadow_alpha))
            draw.text((x2, y2), line2, font=font_sub, fill=(255, 255, 255, text_alpha))

        img = Image.alpha_composite(base_rgba, overlay).convert("RGB")

    # 4. Iterative WebP Compression down to fast KB target (~85KB - 165KB)
    output = io.BytesIO()
    quality = 78
    while quality >= 42:
        output.seek(0)
        output.truncate(0)
        img.save(output, format="WEBP", quality=quality, method=6)
        size_kb = output.tell() / 1024.0
        if size_kb <= target_max_kb:
            break
        quality -= 8

    output.seek(0)
    unique_name = f"naijasale_{uuid.uuid4().hex[:12]}.webp"
    return ContentFile(output.read(), name=unique_name)