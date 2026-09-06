# Face Match → Blockchain Verification Pipeline

A pipeline that takes a face photo, checks it against a set of candidate
social-media posts, and — when it finds a genuine match — writes a
tamper-evident, verifiable record of that match to a blockchain.

Pipeline shape: **face scan → candidate post search & match → blockchain
anchor → re-verification**

## Important scoping note

The task brief describes searching "the web/social media" for a matching
post. Built as an open-ended tool that takes an arbitrary face and finds
*whoever that is* across the internet, this is the same category of
capability as Clearview AI / PimEyes — a facial-recognition search
engine that can be used to identify and track strangers without their
knowledge, i.e. a stalking/doxxing risk.

This implementation instead does **consent-scoped verification**: you
supply a query face **and** a specific list of candidate post URLs from
an account that has already been disclosed for this check (e.g. "does
this photo match posts on this specific, known account?"). The search
step is still genuine — every candidate is actually downloaded, a face
is actually detected and encoded, and the match is decided by a
similarity score, not hardcoded — it's just scoped to sources the
subject agreed to be checked against, rather than crawling arbitrary
social media for an unknown person. This satisfies the same end-to-end
shape (face → search/match → blockchain) while keeping the tool aimed at
a legitimate content-provenance use case: "is this really the same
person/post it claims to be."

If you have a legitimate reason to widen the search step (with
consent/authorization), swap `candidate_search.py`'s URL list for calls
into a real reverse-image-search API or a platform's public API — the
rest of the pipeline (encoding, hashing, blockchain, verify) doesn't
need to change.

## How it works

1. **Face detection & encoding** (`src/face_encode.py`)
   OpenCV Haar Cascade detects the face; a spatially-gridded Local Binary
   Pattern (LBP) histogram encodes it into a 4096-dim feature vector.
   Chosen because it needs zero external model downloads and runs fully
   offline — good for a reliable demo. See "Limitations" for upgrading
   to a deep embedding model.

2. **Candidate search & match** (`src/candidate_search.py`)
   Downloads each candidate post image, detects+encodes any face found,
   and scores it against the query encoding. Returns the best match
   above a similarity threshold, or `None`.

3. **Blockchain anchor** (`src/blockchain.py`, `src/anchor.py`)
   On a match, SHA-256-hashes the matched image, bundles it with
   metadata (post URL, similarity score, timestamp), and writes it as a
   new block in a hash-chained, tamper-evident local blockchain
   (persisted to `chain.json`). Includes a small proof-of-work step so
   it behaves like a real chain, not just a log file.

4. **Re-verification** (`src/verify.py`)
   Re-downloads the post, re-hashes it, and checks that hash against
   the on-chain record — plus walks the entire chain to confirm no
   historical block has been altered.

## Which blockchain

**Local/simulated hash-chain** (`src/blockchain.py`) — a genuine,
tamper-evident SHA-256 hash chain with a small proof-of-work step,
persisted to JSON. Used by default because it's demoable end-to-end with
no API keys, no testnet faucet, and no network dependency on a live
chain during the recording — the task brief explicitly allows this
option.

**Optional: public testnet** (`src/onchain_testnet.py`) — a ready-to-use
`web3.py` client plus a Solidity contract (`Anchor.sol`, in that file's
docstring) for anchoring the same record to Polygon Amoy instead. Not
wired in by default since it needs an RPC endpoint and funded testnet
wallet; both modules expose the same `add_block(data)` interface so
swapping one for the other in `pipeline.py` is a one-line change.

## Setup

```bash
git clone <this-repo>
cd face-id-blockchain-verify
pip install -r requirements.txt
```

## Running it

1. Put your query face photo somewhere, e.g. `demo/query/query_face.jpg`.
2. Create a candidates file listing image URLs to check against — see
   `demo/candidates.example.txt`:

   ```
   https://example.com/path/to/post1.jpg, instagram.com/handle post from 2026-08-01
   https://example.com/path/to/post2.jpg, same account, another post
   ```

3. Run the pipeline:

   ```bash
   cd src
   python pipeline.py ../demo/query/query_face.jpg ../demo/candidates.example.txt ../demo/chain.json
   ```

   This will: encode the face → search the candidates → anchor the best
   match on-chain → re-verify it. All printed to stdout.

4. (Optional, good for the screen recording) Show tamper-evidence:

   ```bash
   python tamper_demo.py ../demo/chain.json
   ```

   This edits the on-chain JSON directly to simulate an attacker, then
   shows `chain.is_valid()` flip from `True` to `False`.

## Repo layout

```
src/
  face_encode.py       # detection + LBP encoding
  candidate_search.py  # downloads + scores candidate posts
  blockchain.py         # local hash-chain implementation
  anchor.py             # hashes + writes a match to the chain
  verify.py             # re-hashes + checks against the chain
  pipeline.py           # orchestrates the full run
  tamper_demo.py        # demonstrates tamper detection
  onchain_testnet.py    # optional Polygon Amoy alternative
demo/
  query/                # put your query photo here
  candidates.example.txt
requirements.txt
```

## Known limitations

- **Encoder accuracy**: LBP histograms are a classic, legitimate face
  descriptor but far less accurate than modern deep embeddings,
  especially across pose/lighting/age changes. For production accuracy,
  swap `face_encode.py` for `face_recognition` (dlib ResNet, 128-d
  embeddings) or `insightface` (ArcFace) — same `encode()`/`compare()`
  interface, so nothing downstream changes. This was a deliberate
  build-time tradeoff to keep the demo runnable with zero extra model
  downloads.
- **Similarity threshold** (`MATCH_THRESHOLD` in `candidate_search.py`)
  is a coarse default tuned by hand on a couple of test images, not
  calibrated on a labeled dataset — expect to need to adjust it per
  image quality/encoder.
- **Search step is consent-scoped, not open web crawling** — see the
  "Important scoping note" above. It is a genuine search over a
  supplied candidate set, not a general-purpose people search engine.
- **Local chain vs. public chain**: the default local chain proves
  tamper-evidence to anyone who has (or is given) `chain.json`; it does
  not give the public, third-party auditability of a real public
  ledger. Use `onchain_testnet.py` if that's required.
- **Proof-of-work** in `blockchain.py` is trivial (single `"0"` prefix)
  — enough to demonstrate the mining concept, not meant as real security.
- Single-face-per-image assumption: `detect_face` takes only the
  largest detected face per image; multi-face candidate posts only
  match on their most prominent face.
