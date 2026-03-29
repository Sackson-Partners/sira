"""
SIRA Platform - Image Utilities
================================
Fixes Anthropic API error:
  "image dimensions exceed max allowed size: 2000 pixels"

All images are resized, compressed, and base64-encoded before being sent to
any AI API (Claude / OpenAI).  Call ``prepare_image_for_claude()`` as the
single entry-point for one image, or ``process_multiple_images()`` for batches.

Future: When Azure Blob Storage is integrated, functions will return a signed
URL in addition to (or instead of) base64, controlled by ``prefer_url=True``.

Requirements:
    pip install Pillow
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Working resize target — stays well below the 2000-px hard cap.
MAX_IMAGE_DIMENSION: int = 1568

# Claude/OpenAI hard cap.  Any image that still exceeds this after
# preprocessing is REJECTED with ImageProcessingError.
HARD_MAX_DIMENSION: int = 2000

DEFAULT_JPEG_QUALITY: int = 80

SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "GIF", "WEBP", "BMP", "TIFF"}

IMAGE_MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
}


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ImageProcessingError(ValueError):
    """Raised when an image cannot be preprocessed to meet API constraints."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_pil():
    """Lazy-import PIL.Image so the module loads without Pillow installed."""
    try:
        from PIL import Image
        return Image
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for image processing.  "
            "Install with:  pip install Pillow"
        ) from exc


def _open_image(source: Union[str, Path, bytes, io.BytesIO]):
    """Open an image from a file path, raw bytes, or BytesIO object."""
    Image = _get_pil()
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        suffix = path.suffix.lstrip(".").upper()
        if suffix not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format '{suffix}'.")
        return Image.open(path)
    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(source))
    if isinstance(source, io.BytesIO):
        source.seek(0)
        return Image.open(source)
    raise TypeError(
        f"source must be str, Path, bytes, or BytesIO — got {type(source).__name__}"
    )


def _resize_if_needed(img, max_dim: int = MAX_IMAGE_DIMENSION):
    """
    Shrink *img* so that max(width, height) <= *max_dim*, keeping aspect ratio.

    Returns:
        (img, resized: bool, original_size: tuple, new_size: tuple)
    """
    w, h = img.size
    original = (w, h)
    if w <= max_dim and h <= max_dim:
        logger.debug("Image %dx%d is within limit (%dpx) — no resize needed.", w, h, max_dim)
        return img, False, original, original

    img.thumbnail((max_dim, max_dim), _get_pil().LANCZOS)
    nw, nh = img.size
    logger.info(
        "Image resized %dx%d -> %dx%d (max_dim=%dpx, Claude API 2000px cap).",
        w, h, nw, nh, max_dim,
    )
    return img, True, original, (nw, nh)


def _to_jpeg_bytes(img, quality: int = DEFAULT_JPEG_QUALITY) -> bytes:
    """Convert *img* to JPEG bytes, handling RGBA / palette -> RGB conversion."""
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


def _validate_final_dimensions(img):
    """
    Raise ImageProcessingError if the image still exceeds the hard cap.
    This is the safety net — should never trigger if preprocessing succeeded.
    """
    w, h = img.size
    if max(w, h) > HARD_MAX_DIMENSION:
        raise ImageProcessingError(
            f"Image dimensions {w}x{h} exceed the hard limit of "
            f"{HARD_MAX_DIMENSION}px after preprocessing.  "
            "Cannot send this image to the AI API."
        )


# ---------------------------------------------------------------------------
# Public encoding functions
# ---------------------------------------------------------------------------

def encode_image_for_claude(
    path: Union[str, Path],
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
) -> Tuple[str, str]:
    """
    Load an image file, resize if needed, compress to JPEG, return (b64, media_type).

    Args:
        path: Filesystem path to the image.
        max_dimension: Max pixel dimension (default 1568).
        jpeg_quality: JPEG quality 1-95 (default 80).

    Returns:
        Tuple[str, str] — (base64_string, "image/jpeg")

    Raises:
        FileNotFoundError, ValueError, ImageProcessingError, ImportError
    """
    try:
        img = _open_image(path)
        img, resized, orig_size, new_size = _resize_if_needed(img, max_dimension)
        _validate_final_dimensions(img)
        jpeg_bytes = _to_jpeg_bytes(img, quality=jpeg_quality)
        b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        logger.debug(
            "encode_image_for_claude: path=%s original=%s final=%s "
            "resized=%s output_bytes=%d",
            path, orig_size, new_size, resized, len(jpeg_bytes),
        )
        return b64, "image/jpeg"
    except (FileNotFoundError, ValueError, ImageProcessingError):
        raise
    except Exception as exc:
        logger.error("Failed to process image at %s: %s", path, exc)
        raise ImageProcessingError(f"Invalid or corrupt image: {exc}") from exc


def encode_image_bytes_for_claude(
    data: Union[bytes, io.BytesIO],
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    source_label: str = "<bytes>",
) -> Tuple[str, str]:
    """
    Same as encode_image_for_claude() but accepts raw bytes or BytesIO.

    Compatible with FastAPI ``UploadFile`` (pass ``await file.read()``).

    Args:
        data: Raw image bytes or BytesIO object.
        max_dimension: Max pixel dimension (default 1568).
        jpeg_quality: JPEG quality 1-95 (default 80).
        source_label: Label for log messages (e.g. filename).

    Returns:
        Tuple[str, str] — (base64_string, "image/jpeg")
    """
    try:
        img = _open_image(data)
        img, resized, orig_size, new_size = _resize_if_needed(img, max_dimension)
        _validate_final_dimensions(img)
        jpeg_bytes = _to_jpeg_bytes(img, quality=jpeg_quality)
        b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        logger.debug(
            "encode_image_bytes_for_claude: source=%s original=%s final=%s "
            "resized=%s output_bytes=%d",
            source_label, orig_size, new_size, resized, len(jpeg_bytes),
        )
        return b64, "image/jpeg"
    except ImageProcessingError:
        raise
    except Exception as exc:
        logger.error("Failed to process image bytes (%s): %s", source_label, exc)
        raise ImageProcessingError(f"Invalid or corrupt image data: {exc}") from exc


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
    source: Union[str, Path, bytes, io.BytesIO],
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    prefer_url: bool = False,
    image_url: Optional[str] = None,
) -> dict:
    """
    One-shot helper: load, resize, compress -> Claude API image block.

    Designed for direct use in FastAPI endpoints::

        from services.ai.image_utils import prepare_image_for_claude

        @app.post("/analyse")
        async def analyse(file: UploadFile):
            raw = await file.read()
            block = prepare_image_for_claude(raw, source_label=file.filename)
            ...

    Args:
        source: File path (str/Path), raw image bytes, or BytesIO.
        max_dimension: Max pixel dimension (default 1568).
        jpeg_quality: JPEG quality (default 80).
        prefer_url: If True and image_url is provided, return a URL-based block
                    instead of base64 (prepared for Azure Blob integration).
        image_url: Public/signed URL for the image (Azure Blob, S3, etc.).

    Returns:
        dict — Claude API image content block.

    Raises:
        ImageProcessingError: if the image cannot be safely preprocessed.
    """
    # Future: Azure Blob / S3 URL-based blocks skip base64 entirely.
    if prefer_url and image_url:
        logger.debug("Returning URL-based image block for %s", image_url)
        return {
            "type": "image",
            "source": {
                "type": "url",
                "url": image_url,
            },
        }

    if isinstance(source, (str, Path)):
        b64, mt = encode_image_for_claude(source, max_dimension, jpeg_quality)
    elif isinstance(source, (bytes, bytearray, io.BytesIO)):
        b64, mt = encode_image_bytes_for_claude(source, max_dimension, jpeg_quality)
    else:
        raise TypeError(
            f"source must be str, Path, bytes, bytearray, or BytesIO — "
            f"got {type(source).__name__}"
        )
    return build_claude_image_block(b64, mt)


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_multiple_images(
    sources: List[Union[str, Path, bytes, io.BytesIO]],
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    skip_errors: bool = False,
) -> List[dict]:
    """
    Resize and encode a list of images, returning Claude API content blocks.

    Every image is processed individually.  If ``skip_errors=True``, corrupt
    or oversized images are logged and omitted rather than raising.

    Args:
        sources: List of file paths, bytes objects, or BytesIO objects.
        max_dimension: Applied to each image independently.
        jpeg_quality: JPEG quality for each image.
        skip_errors: If True, skip bad images instead of raising.

    Returns:
        List of Claude API image content blocks (one per successfully processed image).
    """
    blocks: List[dict] = []
    for i, source in enumerate(sources):
        label = str(source) if isinstance(source, (str, Path)) else f"image[{i}]"
        try:
            block = prepare_image_for_claude(source, max_dimension, jpeg_quality)
            blocks.append(block)
            logger.debug("Processed %s (%d/%d)", label, i + 1, len(sources))
        except ImageProcessingError as exc:
            if skip_errors:
                logger.warning("Skipping %s — %s", label, exc)
            else:
                raise
        except Exception as exc:
            if skip_errors:
                logger.warning("Unexpected error for %s — %s", label, exc)
            else:
                raise ImageProcessingError(
                    f"Failed to process image {label}: {exc}"
                ) from exc

    logger.info(
        "process_multiple_images: %d/%d images processed successfully.",
        len(blocks), len(sources),
    )
    return blocks


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def get_image_dimensions(source: Union[str, Path, bytes, io.BytesIO]) -> Tuple[int, int]:
    """
    Return (width, height) of an image without full encoding.
    Useful for a quick pre-check before committing to processing.
    """
    try:
        img = _open_image(source)
        return img.size  # (width, height)
    except Exception as exc:
        raise ImageProcessingError(f"Cannot read image dimensions: {exc}") from exc


def is_within_api_limit(source: Union[str, Path, bytes, io.BytesIO]) -> bool:
    """Return True if the image is already within the API hard cap (no resize needed)."""
    try:
        w, h = get_image_dimensions(source)
        return max(w, h) <= HARD_MAX_DIMENSION
    except ImageProcessingError:
        return False
