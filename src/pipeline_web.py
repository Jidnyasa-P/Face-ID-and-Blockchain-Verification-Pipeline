"""
pipeline_web.py
-----------------
End-to-end run using REAL web reverse-image search (SerpApi Google Lens)
instead of a manual candidate URL list.

Flow: face scan -> live reverse-image search across the web -> download
each returned image and confirm it's actually the same face (the search
API matches by general visual similarity, not specifically faces, so we
re-verify with our own face encoder) -> anchor the best confirmed match
to the blockchain -> re-verify.

Usage:
    python pipeline_web.py <query_face.jpg> <serpapi_api_key> [chain.json]

Get a free API key: see README.md "Free API key setup".
"""

import sys
import urllib.request

from face_encode import encode_from_path, detect_face, encode_face, compare, NoFaceFoundError
from web_reverse_search import reverse_image_search
from blockchain import SimpleChain
from anchor import anchor_match
from verify import verify_block, fetch_bytes

import cv2
import numpy as np

FACE_MATCH_THRESHOLD = 0.35


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def run_pipeline(query_path: str, api_key: str, chain_path: str = "chain.json"):
    print(f"[1/4] Encoding query face from {query_path} ...")
    query_encoding = encode_from_path(query_path)
    print("      Done.\n")

    print("[2/4] Running LIVE reverse-image search (SerpApi Google Lens) ...")
    web_matches = reverse_image_search(query_path, api_key)
    print(f"      Search returned {len(web_matches)} page(s) with a visually similar image.\n")

    print("[3/4] Confirming each result actually contains the same FACE (search engine "
          "matches by general image similarity, so we re-check with our own face encoder) ...")
    best = None
    for m in web_matches:
        if not m.matching_image_url:
            print(f"  [skip] {m.page_url}: no direct image URL returned")
            continue
        try:
            raw = _download(m.matching_image_url)
            arr = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("could not decode image")
            face = detect_face(img)
            enc = encode_face(face)
            sim = compare(query_encoding, enc)
        except NoFaceFoundError:
            print(f"  [skip] {m.page_url}: no face found in matched image")
            continue
        except Exception as e:
            print(f"  [skip] {m.page_url}: {e}")
            continue

        print(f"  candidate {m.page_url} -> face similarity {sim:.3f}")
        if sim >= FACE_MATCH_THRESHOLD and (best is None or sim > best["similarity"]):
            best = {"page_url": m.page_url, "image_url": m.matching_image_url,
                    "similarity": sim, "image_bytes": raw}

    if best is None:
        print("\n      No web result was confirmed as the same face. Nothing anchored.")
        return None

    print(f"\n      CONFIRMED MATCH: {best['page_url']} (face similarity={best['similarity']:.3f})\n")

    print(f"[4/4] Anchoring confirmed match to blockchain ({chain_path}) ...")
    chain = SimpleChain(chain_path)
    result = anchor_match(
        chain=chain,
        image_bytes=best["image_bytes"],
        post_url=best["page_url"],
        similarity=best["similarity"],
        query_image_path=query_path,
    )
    print(f"      Anchored at block #{result['block_index']}, "
          f"block hash {result['block_hash'][:16]}...\n")

    print("[verify] Re-fetching the matched image and re-checking against the on-chain record ...")
    fresh_bytes = fetch_bytes(best["image_url"])
    verification = verify_block(chain, result["block_index"], fresh_bytes)
    print("         Chain integrity valid:", verification["chain_integrity_valid"])
    print("         Hash matches on-chain record:", verification["hash_matches_onchain_record"])
    print("         => VERIFIED" if verification["ok"] else "         => VERIFICATION FAILED")

    return {"match": best, "anchor": result, "verification": verification}


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("Usage: python pipeline_web.py <query_face.jpg> <serpapi_api_key> [chain.json]")
        sys.exit(1)
    query_path = sys.argv[1]
    api_key = sys.argv[2]
    chain_path = sys.argv[3] if len(sys.argv) == 4 else "chain.json"
    run_pipeline(query_path, api_key, chain_path)
