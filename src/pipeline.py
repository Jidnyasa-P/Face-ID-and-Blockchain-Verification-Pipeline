"""
pipeline.py
-----------
End-to-end run: face scan -> candidate search/match -> blockchain anchor.

Usage:
    python pipeline.py <query_face.jpg> <candidates.txt> [chain.json]

`candidates.txt` is a plain text file, one candidate post image URL per
line (see demo/candidates.example.txt). These should be posts from an
account/source the subject has disclosed for this check — see
candidate_search.py docstring for why.
"""

import sys

from face_encode import encode_from_path
from candidate_search import load_candidates_from_file, find_match
from blockchain import SimpleChain
from anchor import anchor_match
from verify import verify_block, fetch_bytes


def run_pipeline(query_path: str, candidates_path: str, chain_path: str = "chain.json"):
    print(f"[1/3] Encoding query face from {query_path} ...")
    query_encoding = encode_from_path(query_path)
    print("      Done: encoded to a", query_encoding.shape[0], "-dim feature vector.\n")

    print(f"[2/3] Searching {candidates_path} candidate posts for a match ...")
    candidates = load_candidates_from_file(candidates_path)
    match = find_match(query_encoding, candidates)

    if match is None:
        print("      No matching post found above the similarity threshold.")
        return None

    print(f"      MATCH FOUND: {match.candidate.url} "
          f"(similarity={match.similarity:.3f}, note='{match.candidate.source_note}')\n")

    print(f"[3/3] Anchoring match to blockchain ({chain_path}) ...")
    chain = SimpleChain(chain_path)
    result = anchor_match(
        chain=chain,
        image_bytes=match.image_bytes,
        post_url=match.candidate.url,
        similarity=match.similarity,
        query_image_path=query_path,
    )
    print(f"      Anchored at block #{result['block_index']}, "
          f"block hash {result['block_hash'][:16]}...\n")

    print("[verify] Re-fetching the post and re-checking against the on-chain record ...")
    fresh_bytes = fetch_bytes(match.candidate.url)
    verification = verify_block(chain, result["block_index"], fresh_bytes)
    print("         Chain integrity valid:", verification["chain_integrity_valid"])
    print("         Hash matches on-chain record:", verification["hash_matches_onchain_record"])
    print("         => VERIFIED" if verification["ok"] else "         => VERIFICATION FAILED")

    return {
        "match": match,
        "anchor": result,
        "verification": verification,
    }


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("Usage: python pipeline.py <query_face.jpg> <candidates.txt> [chain.json]")
        sys.exit(1)
    query_path = sys.argv[1]
    candidates_path = sys.argv[2]
    chain_path = sys.argv[3] if len(sys.argv) == 4 else "chain.json"
    run_pipeline(query_path, candidates_path, chain_path)
