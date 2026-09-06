"""
candidate_search.py
--------------------
"Search" step of the pipeline.

IMPORTANT DESIGN NOTE (read this before treating this as a generic
people-search tool): this project performs *consent-scoped verification*,
not open-ended reverse-image search across the internet for an unknown
person. You supply:
  1. a query face photo, and
  2. a list of candidate post URLs (images) from an account that has
     already been disclosed/consented to for this check
     (e.g. "does this photo match posts on @this_specific_handle").

The script then does a genuine search over that candidate set: it
downloads each candidate image, detects+encodes any face in it, and
scores it against the query face. Nothing about the match is hardcoded —
the winning candidate (if any) is whichever one actually scores above
the similarity threshold.

To point this at a *real* platform's public API instead of a manual URL
list (e.g. pulling a user's recent public photo posts via the platform's
own API), swap `load_candidates_from_urls` for a call into that
platform's API and feed the returned image URLs into `find_match`.
"""

import io
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np

from face_encode import NoFaceFoundError, detect_face, encode_face, compare
from image_utils import read_image_any_format

MATCH_THRESHOLD = 0.35  # tune based on your encoder; LBP is coarse-grained


@dataclass
class Candidate:
    url: str
    source_note: str = ""  # e.g. "instagram.com/handle, post from 2026-08-01"


@dataclass
class MatchResult:
    candidate: Candidate
    similarity: float
    image_bytes: bytes


def _load_image(source: str):
    """Load an image either from a local file path or an http(s) URL, in
    essentially any common format (JPG/PNG/BMP/TIFF/WEBP/HEIC/...) — see
    image_utils.read_image_any_format. A local path lets you run the
    whole pipeline offline with images you already have (e.g. saved/
    downloaded posts) instead of needing live URLs during a demo."""
    if source.startswith("http://") or source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    else:
        with open(source, "rb") as f:
            raw = f.read()

    img = read_image_any_format(raw)
    return img, raw


def find_match(
    query_encoding: np.ndarray,
    candidates: List[Candidate],
    threshold: float = MATCH_THRESHOLD,
) -> Optional[MatchResult]:
    """Score every candidate post against the query face encoding.
    Returns the best match above `threshold`, or None if nothing matches.
    This is the genuine search step: every candidate is actually
    downloaded and compared — the result is not pre-selected."""
    best: Optional[MatchResult] = None

    for cand in candidates:
        try:
            img, raw = _load_image(cand.url)
            face = detect_face(img)
            enc = encode_face(face)
            sim = compare(query_encoding, enc)
        except NoFaceFoundError:
            continue
        except Exception as e:
            print(f"  [skip] {cand.url}: {e}")
            continue

        print(f"  candidate {cand.url} -> similarity {sim:.3f}")
        if sim >= threshold and (best is None or sim > best.similarity):
            best = MatchResult(candidate=cand, similarity=sim, image_bytes=raw)

    return best


def load_candidates_from_file(path: str) -> List[Candidate]:
    """Load a simple text file of candidate image URLs, one per line,
    optional comma-separated note: `url,note`."""
    candidates = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",", 1)
            url = parts[0].strip()
            note = parts[1].strip() if len(parts) > 1 else ""
            candidates.append(Candidate(url=url, source_note=note))
    return candidates
