"""
anchor.py
---------
Takes a confirmed match (image bytes + metadata) and writes a
tamper-evident record of it to the blockchain.

We anchor a SHA-256 fingerprint of the image plus match metadata rather
than the raw image itself — this keeps the on-chain record small and
still lets anyone re-verify by re-hashing the original image and
comparing digests.
"""

import hashlib
import time

from blockchain import SimpleChain


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def anchor_match(
    chain: SimpleChain,
    image_bytes: bytes,
    post_url: str,
    similarity: float,
    query_image_path: str,
) -> dict:
    image_hash = sha256_bytes(image_bytes)

    record = {
        "type": "face_match_verification",
        "post_url": post_url,
        "image_sha256": image_hash,
        "similarity_score": round(similarity, 4),
        "query_image": query_image_path,
        "anchored_at": time.time(),
    }

    block = chain.add_block(record)
    return {
        "block_index": block.index,
        "block_hash": block.hash,
        "record": record,
    }
