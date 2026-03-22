"""
SIRA Platform - Image Utilities
Fix for Anthropic API error:
  messages.3.content.305.image.source.base64.data:
  At least one of the image dimensions exceed max allowed size
  for many-image requests: 2000 pixels

Resizes and compresses images before base64-encoding them for
use with the Claude API (many-image requests).

Requirements:
    pip install Pillow
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Claude API hard cap for many-image requests is 2000px.
# We use 1568 as a safe conservative limit.
MAX_IMAGE_DIMENSION = 1568
DEFAULT_JPEG_QUALITY = 80
SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "GIF", "WEBP", "BMP", "TIFF"}


def _get_pil():
    """Lazy-import PIL.Image to avoid hard dependency at module load."""
    try:
        from PIL import Image
        return Image
    except ImportError as exc:
        raise ImportError(
            "Pillow is required.  Install with:  pip install Pillow"
        ) from exc


def _resize_if_needed(img, max_dim: int = MAX_IMAGE_DIMENSION):
    """Shrink img so neither dimension exceeds max_dim (aspect-ratio safe)."""
    w, h = img.size
    if w <= max_dim and h <= max_dim:
        return img, False
    img.thumbnail((max_dim, max_dim))
    nw, nh = img.size
    logger.info("Image resized %dx%d -> %dx%d (Claude API 2000px cap).", w, h, nw, nh)
    return img, True


def _to_jpeg_bytes(img, quality: int = DEFAULT_JPEG_QUALITY) -> bytes:
    """Convert img to JPEG bytes, handling RGBA/palette -> RGB conversion."""
    Image = _get_pil()
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        bg.paste(img, mask=mask)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def encode_image_for_claude(
    path: Union[str, Path],
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
) -> Tuple[str, str]:
    """Load a file, resize if needed, compress to JPEG, return (b64, media_type).

    Args:
        path: Filesystem path to the image.
        max_dimension: Max width or height in pixels (default 1568).
        jpeg_quality: JPEG quality 1-95 (default 80).

    Returns:
        Tuple[str, str] -- (base64_string, "image/jpeg")

    Raises:
        FileNotFoundError, ValueError, ImportError
    """
    Image = _get_pil()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    suffix = path.suffix.lstrip(".").upper()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format '{suffix}'.")
    img = Image.open(path)
    img, resized = _resize_if_needed(img, max_dimension)
    jpeg_bytes = _to_jpeg_bytes(img, quality=jpeg_quality)
    b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
    logger.debug("Encoded %s -> %d bytes JPEG (resized=%s).", path, len(jpeg_bytes), resized)
    return b64, "image/jpeg"


def encode_image_bytes_for_claude(
    data: bytes,
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    source_format: Optional[str] = None,
) -> Tuple[str, str]:
    """Like encode_image_for_claude() but accepts raw bytes (e.g. UploadFile)."""
    Image = _get_pil()
    img = Image.open(io.BytesIO(data))
    img, _ = _resize_if_needed(img, max_dimension)
    jpeg_bytes = _to_jpeg_bytes(img, quality=jpeg_quality)
    b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
    return b64, "image/jpeg"


def build_claude_image_block(b64_data: str, media_type: str = "image/jpeg") -> dict:
    """Return a Claude API messages content block for a base64 image."""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": b64_data,
        },
    }


def prepare_image_for_claude(
    source: Union[str, Path, bytes],
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
) -> dict:
    """One-shot helper: load, resize, compress -> Claude API image block.

    Args:
        source: File path (str/Path) or raw image bytes.
        max_dimension: Max pixel dimension (default 1568).
        jpeg_quality: JPEG quality (default 80).

    Returns:
        dict -- Claude API image content block.

    Usage in FastAPI::

        from backend.services.ai.image_utils import prepare_image_for_claude
        import anthropic

        @app.post("/analyse")
        async def analyse(file: UploadFile):
            raw = await file.read()
            block = prepare_image_for_claude(raw)
            client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
            message = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [block, {"type": "text", "text": "Analyse this image."}],
                }],
            )
            return {"result": message.content[0].text}
    """
    if isinstance(source, (str, Path)):
        b64, mt = encode_image_for_claude(source, max_dimension, jpeg_quality)
    elif isinstance(source, bytes):
        b64, mt = encode_image_bytes_for_claude(source, max_dimension, jpeg_quality)
    else:
        raise TypeError(f"source must be str/Path or bytes, got {type(source).__name__}")
    return build_claude_image_block(b64, mt)
