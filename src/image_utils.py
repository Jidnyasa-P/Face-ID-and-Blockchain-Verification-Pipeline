"""
image_utils.py
---------------
Universal image loading so the rest of the pipeline doesn't care what
format a photo arrives in. Handles JPG, PNG, BMP, TIFF, WEBP, GIF
(first frame) out of the box via Pillow, and HEIC/HEIF (default iPhone
photo format) if the optional `pillow-heif` package is installed.

Also auto-corrects EXIF rotation (phone photos are often stored
sideways/upside-down with an EXIF orientation tag) and can compress an
image down to a target size for APIs with an upload size limit.

Nothing downstream needs to change: face_encode.py and
candidate_search.py both route through read_image_any_format() instead
of calling cv2.imread/cv2.imdecode directly, so "any format in" is
handled in exactly one place.
"""

import io
from typing import Optional, Union

import cv2
import numpy as np
from PIL import Image, ImageOps

# Enable HEIC/HEIF support if the optional package is installed.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False


def _pil_to_bgr_ndarray(pil_img: Image.Image) -> np.ndarray:
    """Convert a PIL image (any mode) to an OpenCV-style BGR ndarray."""
    pil_img = ImageOps.exif_transpose(pil_img)  # auto-fix phone photo rotation
    pil_img = pil_img.convert("RGB")
    rgb = np.array(pil_img)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def read_image_any_format(source: Union[str, bytes]) -> np.ndarray:
    """Load an image from a file path or raw bytes, in essentially any
    common format, and return an OpenCV BGR ndarray ready for detection.

    Raises a clear error (mentioning pillow-heif) if the format can't be
    opened, e.g. a HEIC file with the optional package not installed.
    """
    try:
        if isinstance(source, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(source))
        else:
            pil_img = Image.open(source)
        pil_img.load()  # force-decode now so format errors surface here
    except Exception as e:
        hint = ""
        if not HEIC_SUPPORTED:
            hint = (
                " If this is a HEIC/HEIF photo (common on iPhones), install "
                "support with: pip install pillow-heif"
            )
        raise ValueError(f"Could not read image ({e}).{hint}") from e

    return _pil_to_bgr_ndarray(pil_img)


def compress_for_upload(source: Union[str, bytes], max_bytes: int = 480_000) -> bytes:
    """Return JPEG-encoded bytes of the image, resized/re-compressed as
    needed to fit under `max_bytes` (SerpApi's Image API caps uploads at
    500 KB). Accepts any input format via read_image_any_format, so
    whatever the user uploaded, what goes out is always a compliant JPEG.
    """
    bgr = read_image_any_format(source)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    quality = 90
    scale = 1.0
    while True:
        w, h = pil_img.size
        resized = pil_img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=quality)
        size = buf.tell()
        if size <= max_bytes or (quality <= 30 and scale <= 0.3):
            return buf.getvalue()
        # Reduce quality first, then start shrinking dimensions too.
        if quality > 40:
            quality -= 10
        else:
            scale *= 0.85
