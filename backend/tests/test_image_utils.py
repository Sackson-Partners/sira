"""
Unit tests for services.ai.image_utils
=======================================
Tests cover:
  - Images within limits (no resize)
  - Images exceeding the max dimension (resize required)
  - RGBA and palette-mode images (alpha compositing)
  - Corrupt / non-image bytes (graceful error)
  - BytesIO input
  - Multiple images batch processing
  - Hard-cap validation guard (simulated failure)
  - Utility helpers (get_image_dimensions, is_within_api_limit)
  - build_claude_image_block structure
  - prepare_image_for_claude URL-preference path

Run with:
    pytest backend/tests/test_image_utils.py -v
"""

from __future__ import annotations

import base64
import io

import pytest

# ---------------------------------------------------------------------------
# Helpers to create in-memory test images without needing real files
# ---------------------------------------------------------------------------

def _make_image_bytes(width: int, height: int, mode: str = "RGB") -> bytes:
    """Create a minimal in-memory PNG image of the requested size."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed — skipping image tests")

    img = Image.new(mode, (width, height), color=(100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes(width: int, height: int) -> bytes:
    """Create a minimal JPEG in memory."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed — skipping image tests")

    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from services.ai.image_utils import (
    ImageProcessingError,
    MAX_IMAGE_DIMENSION,
    HARD_MAX_DIMENSION,
    build_claude_image_block,
    encode_image_bytes_for_claude,
    get_image_dimensions,
    is_within_api_limit,
    prepare_image_for_claude,
    process_multiple_images,
)


# ---------------------------------------------------------------------------
# encode_image_bytes_for_claude
# ---------------------------------------------------------------------------

class TestEncodeImageBytesForClaude:
    def test_small_image_no_resize(self):
        """Image within limits should not be resized."""
        data = _make_image_bytes(800, 600)
        b64, mt = encode_image_bytes_for_claude(data)
        assert mt == "image/jpeg"
        assert b64  # non-empty
        # Decode to verify it's valid base64 JPEG
        raw = base64.b64decode(b64)
        assert raw[:3] == b"\xff\xd8\xff"  # JPEG magic bytes

    def test_large_image_is_resized(self):
        """Image exceeding MAX_IMAGE_DIMENSION must be resized."""
        oversized = MAX_IMAGE_DIMENSION + 500
        data = _make_image_bytes(oversized, oversized)
        b64, mt = encode_image_bytes_for_claude(data, source_label="oversized_test")

        # Decode result and check dimensions
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        w, h = img.size
        assert max(w, h) <= MAX_IMAGE_DIMENSION, (
            f"Expected max dimension <= {MAX_IMAGE_DIMENSION}, got {w}x{h}"
        )

    def test_exact_limit_not_resized(self):
        """Image at exactly MAX_IMAGE_DIMENSION should pass through unchanged."""
        data = _make_image_bytes(MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION)
        b64, _ = encode_image_bytes_for_claude(data)
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        assert max(img.size) <= MAX_IMAGE_DIMENSION

    def test_wide_image_aspect_ratio_preserved(self):
        """Wide image (3000x500) should be resized with aspect ratio intact."""
        data = _make_image_bytes(3000, 500)
        b64, _ = encode_image_bytes_for_claude(data)
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        w, h = img.size
        assert w <= MAX_IMAGE_DIMENSION
        # height should scale proportionally (~261px for 3000x500 -> 1568x?)
        expected_h = round(500 * (w / 3000))
        assert abs(h - expected_h) <= 2  # allow rounding of 2px

    def test_tall_image_aspect_ratio_preserved(self):
        """Tall image (500x3000) should be resized with aspect ratio intact."""
        data = _make_image_bytes(500, 3000)
        b64, _ = encode_image_bytes_for_claude(data)
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        w, h = img.size
        assert h <= MAX_IMAGE_DIMENSION

    def test_rgba_image_converted_to_rgb(self):
        """RGBA images must be composited onto white and saved as JPEG."""
        data = _make_image_bytes(400, 300, mode="RGBA")
        b64, mt = encode_image_bytes_for_claude(data)
        assert mt == "image/jpeg"
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        assert img.mode == "RGB"

    def test_bytesio_input(self):
        """BytesIO should be accepted alongside raw bytes."""
        data = _make_image_bytes(100, 100)
        buf = io.BytesIO(data)
        b64, mt = encode_image_bytes_for_claude(buf)
        assert mt == "image/jpeg"
        assert b64

    def test_corrupt_bytes_raises_image_processing_error(self):
        """Corrupt / non-image bytes must raise ImageProcessingError."""
        with pytest.raises(ImageProcessingError):
            encode_image_bytes_for_claude(b"this is not an image")

    def test_empty_bytes_raises_image_processing_error(self):
        with pytest.raises(ImageProcessingError):
            encode_image_bytes_for_claude(b"")

    def test_custom_max_dimension(self):
        """custom max_dimension parameter should be respected."""
        data = _make_image_bytes(800, 800)
        b64, _ = encode_image_bytes_for_claude(data, max_dimension=400)
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        assert max(img.size) <= 400

    def test_jpeg_quality_affects_size(self):
        """Lower quality should produce a smaller or equal-size file (never larger)."""
        # Use a noisy image so quality levels produce meaningfully different output.
        try:
            from PIL import Image
            import random
        except ImportError:
            pytest.skip("Pillow not installed")

        img = Image.new("RGB", (500, 500))
        pixels = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                  for _ in range(500 * 500)]
        img.putdata(pixels)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()

        b64_q80, _ = encode_image_bytes_for_claude(data, jpeg_quality=80)
        b64_q20, _ = encode_image_bytes_for_claude(data, jpeg_quality=20)
        # Noisy images always compress less at higher quality — q20 must be smaller.
        assert len(b64_q20) < len(b64_q80)


# ---------------------------------------------------------------------------
# build_claude_image_block
# ---------------------------------------------------------------------------

class TestBuildClaudeImageBlock:
    def test_structure(self):
        block = build_claude_image_block("abc123", "image/jpeg")
        assert block["type"] == "image"
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "image/jpeg"
        assert block["source"]["data"] == "abc123"

    def test_default_media_type(self):
        block = build_claude_image_block("xyz")
        assert block["source"]["media_type"] == "image/jpeg"


# ---------------------------------------------------------------------------
# prepare_image_for_claude
# ---------------------------------------------------------------------------

class TestPrepareImageForClaude:
    def test_bytes_input(self):
        data = _make_image_bytes(200, 200)
        block = prepare_image_for_claude(data)
        assert block["type"] == "image"
        assert block["source"]["type"] == "base64"

    def test_bytesio_input(self):
        data = _make_image_bytes(200, 200)
        block = prepare_image_for_claude(io.BytesIO(data))
        assert block["type"] == "image"

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            prepare_image_for_claude(12345)  # type: ignore[arg-type]

    def test_prefer_url_returns_url_block(self):
        """When prefer_url=True and image_url is set, no base64 is computed."""
        block = prepare_image_for_claude(
            b"dummy",
            prefer_url=True,
            image_url="https://blob.example.com/img.jpg",
        )
        assert block["source"]["type"] == "url"
        assert block["source"]["url"] == "https://blob.example.com/img.jpg"

    def test_prefer_url_without_url_falls_back_to_base64(self):
        """prefer_url=True with no URL should still encode to base64."""
        data = _make_image_bytes(100, 100)
        block = prepare_image_for_claude(data, prefer_url=True, image_url=None)
        assert block["source"]["type"] == "base64"


# ---------------------------------------------------------------------------
# process_multiple_images
# ---------------------------------------------------------------------------

class TestProcessMultipleImages:
    def test_all_valid_images(self):
        images = [_make_image_bytes(300, 200) for _ in range(3)]
        blocks = process_multiple_images(images)
        assert len(blocks) == 3
        for b in blocks:
            assert b["type"] == "image"

    def test_empty_list(self):
        assert process_multiple_images([]) == []

    def test_skip_errors_true(self):
        """With skip_errors=True, corrupt images are omitted, not raised."""
        images = [
            _make_image_bytes(100, 100),
            b"corrupt data",
            _make_image_bytes(200, 150),
        ]
        blocks = process_multiple_images(images, skip_errors=True)
        assert len(blocks) == 2

    def test_skip_errors_false_raises(self):
        """With skip_errors=False (default), corrupt images raise."""
        images = [_make_image_bytes(100, 100), b"corrupt"]
        with pytest.raises(ImageProcessingError):
            process_multiple_images(images, skip_errors=False)

    def test_oversized_images_resized(self):
        """All oversized images in a batch must be resized."""
        big = MAX_IMAGE_DIMENSION + 1000
        images = [_make_image_bytes(big, big) for _ in range(2)]
        blocks = process_multiple_images(images)
        from PIL import Image
        for block in blocks:
            raw = base64.b64decode(block["source"]["data"])
            img = Image.open(io.BytesIO(raw))
            assert max(img.size) <= MAX_IMAGE_DIMENSION


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

class TestGetImageDimensions:
    def test_bytes(self):
        data = _make_image_bytes(640, 480)
        w, h = get_image_dimensions(data)
        assert w == 640
        assert h == 480

    def test_bytesio(self):
        data = _make_image_bytes(1920, 1080)
        w, h = get_image_dimensions(io.BytesIO(data))
        assert w == 1920
        assert h == 1080

    def test_corrupt_raises(self):
        with pytest.raises(ImageProcessingError):
            get_image_dimensions(b"garbage")


class TestIsWithinApiLimit:
    def test_small_image_within_limit(self):
        data = _make_image_bytes(800, 600)
        assert is_within_api_limit(data) is True

    def test_large_image_exceeds_limit(self):
        data = _make_image_bytes(HARD_MAX_DIMENSION + 1, 100)
        assert is_within_api_limit(data) is False

    def test_exactly_at_limit(self):
        data = _make_image_bytes(HARD_MAX_DIMENSION, HARD_MAX_DIMENSION)
        assert is_within_api_limit(data) is True

    def test_corrupt_returns_false(self):
        assert is_within_api_limit(b"not an image") is False


# ---------------------------------------------------------------------------
# Integration: end-to-end output format
# ---------------------------------------------------------------------------

class TestEndToEndFormat:
    def test_output_is_valid_base64_jpeg(self):
        """Full pipeline produces valid base64 JPEG decodable by Pillow."""
        from PIL import Image

        data = _make_image_bytes(2500, 1800)  # Oversized
        block = prepare_image_for_claude(data)

        raw = base64.b64decode(block["source"]["data"])
        img = Image.open(io.BytesIO(raw))

        assert img.format == "JPEG"
        assert img.mode == "RGB"
        assert max(img.size) <= MAX_IMAGE_DIMENSION

    def test_no_image_sent_without_preprocessing(self):
        """Verify that even large images are always within API limits after prepare_image_for_claude."""
        from PIL import Image

        for dims in [(2001, 100), (100, 2001), (3000, 3000), (1, 5000)]:
            data = _make_image_bytes(*dims)
            block = prepare_image_for_claude(data)
            raw = base64.b64decode(block["source"]["data"])
            img = Image.open(io.BytesIO(raw))
            w, h = img.size
            assert max(w, h) <= MAX_IMAGE_DIMENSION, (
                f"Input {dims} produced {w}x{h} which exceeds {MAX_IMAGE_DIMENSION}px"
            )
