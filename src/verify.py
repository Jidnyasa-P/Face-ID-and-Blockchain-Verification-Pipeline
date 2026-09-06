"""
verify.py
---------
Re-verification: given a post image (fresh download) and a block index
(or the image hash), recompute the SHA-256 hash and compare it against
what's on-chain. This is the "tamper-evident" proof — if the image at
that URL has changed since anchoring, or the on-chain record has been
altered, the hashes will not match and/or the chain integrity check
will fail.
"""

import sys
import urllib.request

from anchor import sha256_bytes
from blockchain import SimpleChain


def fetch_bytes(source: str) -> bytes:
    """Read bytes from a local file path or an http(s) URL."""
    if source.startswith("http://") or source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    with open(source, "rb") as f:
        return f.read()


def verify_block(chain: SimpleChain, block_index: int, current_image_bytes: bytes) -> dict:
    block = chain.get_block(block_index)
    if block is None:
        return {"ok": False, "reason": f"No block with index {block_index}"}

    chain_ok = chain.is_valid()
    recomputed_hash = sha256_bytes(current_image_bytes)
    onchain_hash = block.data.get("image_sha256")
    hash_match = recomputed_hash == onchain_hash

    return {
        "ok": chain_ok and hash_match,
        "chain_integrity_valid": chain_ok,
        "hash_matches_onchain_record": hash_match,
        "onchain_hash": onchain_hash,
        "recomputed_hash": recomputed_hash,
        "block_hash": block.hash,
        "record": block.data,
    }


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python verify.py <chain.json> <block_index> <image_url>")
        sys.exit(1)

    chain_path, block_index, image_url = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    chain = SimpleChain(chain_path)
    img_bytes = fetch_bytes(image_url)
    result = verify_block(chain, block_index, img_bytes)

    print("Chain integrity valid:      ", result["chain_integrity_valid"])
    print("Hash matches on-chain record:", result["hash_matches_onchain_record"])
    print("On-chain hash:  ", result["onchain_hash"])
    print("Recomputed hash:", result["recomputed_hash"])
    print("=> VERIFIED" if result["ok"] else "=> VERIFICATION FAILED")
