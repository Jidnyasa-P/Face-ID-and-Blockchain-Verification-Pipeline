"""
tamper_demo.py
---------------
Optional but recommended for the screen recording: shows what happens if
someone edits the on-chain record after the fact (e.g. swaps in a
different image hash to fake a different match). Run this AFTER
pipeline.py has produced a chain.json.

Usage:
    python tamper_demo.py <chain.json>
"""

import json
import sys

from blockchain import SimpleChain


def main(chain_path: str):
    chain = SimpleChain(chain_path)
    print("Chain length:", len(chain))
    print("Valid BEFORE tampering:", chain.is_valid())

    # Simulate an attacker editing the raw JSON file on disk directly,
    # e.g. swapping the anchored image hash for a different one.
    with open(chain_path) as f:
        raw = json.load(f)

    if len(raw) < 2:
        print("Need at least one anchored block to demo tampering. Run pipeline.py first.")
        return

    raw[1]["data"]["image_sha256"] = "f" * 64  # forged hash
    with open(chain_path, "w") as f:
        json.dump(raw, f, indent=2)

    tampered_chain = SimpleChain(chain_path)
    print("Valid AFTER tampering:", tampered_chain.is_valid())
    print("(Any re-verifier walking the chain now detects the break in the hash-link,")
    print(" flagging the record as no longer trustworthy.)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tamper_demo.py <chain.json>")
        sys.exit(1)
    main(sys.argv[1])
