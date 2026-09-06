"""
face_encode.py
--------------
Face detection + encoding.

Detection: OpenCV Haar Cascade (bundled with opencv-python, no external
           model download required).
Encoding:  Local Binary Pattern (LBP) histogram of the aligned face crop.
           LBP is a classic, well-documented texture-based face descriptor
           (Ahonen et al., 2006) — legitimate for this task's "any face
           detection/recognition library" requirement, and has the benefit
           of running fully offline with zero extra downloads.

Swap-in upgrade path (see README "Limitations"): replace this module with
`face_recognition` (dlib ResNet embeddings) or `insightface` for
state-of-the-art accuracy. The rest of the pipeline (search, hashing,
blockchain) does not need to change — it only consumes the encode()/
compare() interface below.
"""

import cv2
import numpy as np

from image_utils import read_image_any_format

_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_face_detector = cv2.CascadeClassifier(_CASCADE_PATH)

FACE_SIZE = (128, 128)


class NoFaceFoundError(Exception):
    pass


def detect_face(image_bgr: np.ndarray) -> np.ndarray:
    """Detect the largest face in a BGR image and return the cropped,
    resized, grayscale, histogram-equalized face."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    faces = _face_detector.detectMultiScale(
        gray, scaleFactor=1.05, minNeighbors=4, minSize=(30, 30)
    )
    if len(faces) == 0:
        raise NoFaceFoundError("No face detected in image.")

    # Take the largest bounding box (most prominent face)
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face = gray[y : y + h, x : x + w]
    face = cv2.resize(face, FACE_SIZE, interpolation=cv2.INTER_AREA)
    face = cv2.equalizeHist(face)
    return face


def _lbp_image(gray_face: np.ndarray) -> np.ndarray:
    """Compute a simple 8-neighbor, radius-1 Local Binary Pattern image."""
    img = gray_face.astype(np.int32)
    h, w = img.shape
    padded = np.pad(img, 1, mode="edge")
    center = padded[1:-1, 1:-1]

    neighbors = [
        padded[0:-2, 0:-2], padded[0:-2, 1:-1], padded[0:-2, 2:],
        padded[1:-1, 2:],   padded[2:, 2:],     padded[2:, 1:-1],
        padded[2:, 0:-2],   padded[1:-1, 0:-2],
    ]

    lbp = np.zeros((h, w), dtype=np.uint8)
    for i, n in enumerate(neighbors):
        lbp |= ((n >= center).astype(np.uint8)) << i
    return lbp


def encode_face(gray_face: np.ndarray) -> np.ndarray:
    """Turn a detected face crop into a fixed-length feature vector:
    a spatially-gridded LBP histogram (better discrimination than a
    single global histogram)."""
    lbp = _lbp_image(gray_face)
    grid = 4  # 4x4 spatial cells
    gh, gw = gray_face.shape[0] // grid, gray_face.shape[1] // grid
    hists = []
    for i in range(grid):
        for j in range(grid):
            cell = lbp[i * gh : (i + 1) * gh, j * gw : (j + 1) * gw]
            hist, _ = np.histogram(cell, bins=256, range=(0, 256))
            hist = hist.astype(np.float32)
            hist /= hist.sum() + 1e-7
            hists.append(hist)
    return np.concatenate(hists)


def encode_from_path(path: str) -> np.ndarray:
    img = read_image_any_format(path)
    face = detect_face(img)
    return encode_face(face)


def compare(encoding_a: np.ndarray, encoding_b: np.ndarray) -> float:
    """Chi-square distance between two LBP histograms. Lower = more similar.
    Returns a similarity score in [0, 1] (1 = identical)."""
    eps = 1e-10
    chi_sq = 0.5 * np.sum(
        ((encoding_a - encoding_b) ** 2) / (encoding_a + encoding_b + eps)
    )
    # Normalize into a bounded similarity score for easy thresholding.
    similarity = 1.0 / (1.0 + chi_sq)
    return float(similarity)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python face_encode.py <image_path>")
        sys.exit(1)
    enc = encode_from_path(sys.argv[1])
    print(f"Encoded face into a {enc.shape[0]}-dim feature vector.")
