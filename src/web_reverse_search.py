"""
web_reverse_search.py
----------------------
REAL reverse-image search using SerpApi's Google Lens engine
(https://serpapi.com/google-lens-api). This performs a genuine, live
search of Google's actual visual-match index and returns real pages
(including social media posts) containing a visually similar image.

WHY SERPAPI / WHY IT'S FREE:
- Free plan: 250 searches/month, forever, at $0 — no credit card required
  to sign up (verified against SerpApi's own pricing page as of this
  writing; double-check at signup since terms can change). A hackathon
  demo (a handful of calls) stays well inside this.
- SerpApi's Image API lets you upload a LOCAL file directly (no need to
  host your photo publicly first) and returns an `image_id` you then
  pass to the Google Lens search — so this works straight off your
  laptop with one API key and zero extra infrastructure.

Two-step call:
  1. POST the local image to https://serpapi.com/image -> get image_id
  2. GET https://serpapi.com/search with engine=google_lens&image_id=...
     -> get visual_matches: real pages + real image URLs from the live web

Intended use: point this at a photo you own/have rights to check (e.g.
your own face) to see where it has actually been posted online — a
legitimate content-provenance / "is my photo being used somewhere"
check, not a tool for identifying strangers.

Docs: https://serpapi.com/google-lens-api
      https://serpapi.com/google-lens-upload-an-image
      https://serpapi.com/image-api
"""

import requests
from dataclasses import dataclass
from typing import List

from image_utils import compress_for_upload

SERPAPI_IMAGE_UPLOAD_URL = "https://serpapi.com/image"
SERPAPI_SEARCH_URL = "https://serpapi.com/search"


@dataclass
class WebMatch:
    page_url: str            # the web page (e.g. a social media post) with a matching image
    matching_image_url: str  # the direct image URL found on that page
    match_type: str          # "visual_match"
    title: str = ""          # page title, if available


def _upload_image(image_path: str, api_key: str) -> str:
    """Upload a local image to SerpApi's Image API and return its image_id.
    Accepts ANY input format (JPG/PNG/HEIC/etc — see image_utils) and
    always converts it to a compliant JPEG under SerpApi's 500 KB limit
    before sending, so you never have to manually convert or compress
    your photo first."""
    jpeg_bytes = compress_for_upload(image_path, max_bytes=480_000)
    resp = requests.post(
        SERPAPI_IMAGE_UPLOAD_URL,
        files={"image": ("query.jpg", jpeg_bytes, "image/jpeg")},
        data={"api_key": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "image_id" not in data:
        raise RuntimeError(f"SerpApi image upload failed: {data}")
    return data["image_id"]


def reverse_image_search(image_path: str, api_key: str, max_results: int = 10) -> List[WebMatch]:
    """Genuine live reverse-image search: uploads the local image, then
    queries Google Lens (via SerpApi) for real visual matches across the
    live web. Nothing here is pre-picked — results are whatever Google's
    index actually returns at call time."""
    image_id = _upload_image(image_path, api_key)

    params = {
        "engine": "google_lens",
        "image_id": image_id,
        "api_key": api_key,
    }
    resp = requests.get(SERPAPI_SEARCH_URL, params=params, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if "error" in result:
        raise RuntimeError(f"SerpApi search error: {result['error']}")

    matches: List[WebMatch] = []
    for item in result.get("visual_matches", [])[:max_results]:
        matches.append(
            WebMatch(
                page_url=item.get("link", ""),
                matching_image_url=item.get("image", ""),
                match_type="visual_match",
                title=item.get("title", ""),
            )
        )
    return matches


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python web_reverse_search.py <image_path> <serpapi_api_key>")
        sys.exit(1)

    results = reverse_image_search(sys.argv[1], sys.argv[2])
    print(f"Found {len(results)} visual match(es) on the live web:\n")
    for m in results:
        print(f"- {m.title}")
        print(f"  page:  {m.page_url}")
        print(f"  image: {m.matching_image_url}")
