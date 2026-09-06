<div align="center">

# 🔍 Face Match → Blockchain Verification Pipeline

**Face scan → live web/social search → tamper-evident blockchain record**

</div>

---

## 📌 What this is

A pipeline that takes a face photo, genuinely searches the live web for a
matching social media post, and — once it finds one — writes a
tamper-evident, cryptographically verifiable record of that match to a
blockchain.

```
 ┌─────────────┐      ┌──────────────────────┐      ┌────────────────────┐      ┌─────────────┐
 │  Face scan  │ ───▶ │  Live web/social      │ ───▶ │  Hash + anchor to  │ ───▶ │  Re-verify  │
 │  (any image │      │  search (SerpApi /    │      │  blockchain         │      │  on-chain   │
 │   format)   │      │  Google Lens)         │      │  (local hash-chain) │      │  record     │
 └─────────────┘      └──────────────────────┘      └────────────────────┘      └─────────────┘
```

Every stage is real and independently tested — nothing is mocked or
pre-picked. See **[✅ Requirements checklist](#-requirements-checklist)** below.

---

## ⚠️ A note on scope (read this first)

The brief describes searching the web for "who posted this face." Built
as an open-ended tool — arbitrary face in, stranger's identity/location
out — that's the same capability as Clearview AI / PimEyes: a
facial-recognition search engine that can be used to track people
without consent.

This project runs the same technical pipeline, but is intended for
**checking a photo you own** (e.g. your own face) to see where it's
actually been posted online — a legitimate content-provenance /
"is my photo being used somewhere" check, not a people-search tool.
The search step is still 100% genuine (see below) — it's just aimed at
a use case that doesn't enable stalking or doxxing.

---

## 🧩 How it works, stage by stage

| # | Stage | File | What happens |
|---|-------|------|---------------|
| 1 | **Face detection & encoding** | `face_encode.py` | OpenCV Haar Cascade detects the face; a spatially-gridded Local Binary Pattern (LBP) histogram encodes it into a 4096-dim fingerprint. Zero external model downloads. |
| 2 | **Live web search** | `web_reverse_search.py` | Uploads your photo to **SerpApi's Google Lens engine** and gets back real pages/posts from the live web with visually similar images. Genuinely queried at runtime — not hardcoded. |
| 3 | **Face-match confirmation** | `pipeline_web.py` | Google Lens matches by general visual similarity (any object/scene), so every result is re-downloaded and re-checked with our own face encoder before being trusted. |
| 4 | **Blockchain anchor** | `anchor.py`, `blockchain.py` | SHA-256-hashes the confirmed matching image + metadata (URL, similarity score, timestamp) and writes it as a new block in a hash-chained, tamper-evident local blockchain. |
| 5 | **Re-verification** | `verify.py` | Re-downloads the post, re-hashes it, and checks it against the on-chain record — plus walks the whole chain to confirm nothing historical was altered. |

---

## ⛓️ Which blockchain

**Local/simulated hash-chain** (`blockchain.py`) — a genuine SHA-256
hash-chain with a small proof-of-work step, persisted to `chain.json`.
Chosen so the demo runs end-to-end with **zero API keys, zero testnet
faucets, zero network dependency** on a live chain during recording —
explicitly allowed by the brief ("local/simulated chain").

**Optional upgrade: public testnet** (`onchain_testnet.py`) — a
ready-to-deploy Solidity contract + `web3.py` client for anchoring the
same record to **Polygon Amoy** instead. Same `add_block()` interface,
so swapping it in is a one-line change in `pipeline_web.py`.

---

## 🖼️ Supported input formats

**Any common image format works** — JPG, PNG, BMP, TIFF, WEBP, GIF, and
HEIC/HEIF (iPhone photos, if `pillow-heif` is installed). Format
detection and normalization happens in one place (`image_utils.py`) and
is used by every other module, so nothing else in the pipeline needs to
know or care what format your photo is in.

If you use the live web-search path, your photo is also automatically
compressed to a compliant JPEG under SerpApi's 500 KB upload limit — no
manual conversion needed.

---

## 🚀 Setup

```bash
git clone <this-repo>
cd face-id-blockchain-verify
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Optional — only if you'll be using iPhone HEIC photos:
pip install pillow-heif
```

---

## ▶️ Running it

### Option A (recommended) — real live web search

Uses **SerpApi's Google Lens engine** — free, no credit card required.

**One-time setup:**
1. Sign up free at [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up) (email only)
2. Grab your key at [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key)
3. Free plan: **250 searches/month, forever, $0**

**Run:**
```bash
cd src
python pipeline_web.py ../demo/query/query_face.jpg YOUR_SERPAPI_KEY ../demo/chain.json
```

This will: encode your face → search the live web → confirm the match
is really the same face → anchor it on-chain → re-verify. All printed
to the terminal step by step.

### Option B — offline / candidate-list mode

No API key needed. Instead of a live search, you supply a list of
candidate image paths/URLs to check against — good for fully offline
testing.

```bash
cd src
python pipeline.py ../demo/query/query_face.jpg ../demo/candidates.example.txt ../demo/chain.json
```

### 🔨 Bonus: prove tamper-evidence

```bash
python tamper_demo.py ../demo/chain.json
```

Simulates someone editing the on-chain JSON directly, then shows
`chain.is_valid()` flip from `True` → `False`. Great for a screen
recording.

---

## 📁 Repo layout

```
src/
  image_utils.py          # universal image loader (any format → normalized)
  face_encode.py           # face detection + LBP encoding
  web_reverse_search.py    # REAL live search (SerpApi Google Lens)
  pipeline_web.py           # end-to-end run, live search (recommended)
  candidate_search.py      # offline candidate-list search (Option B)
  pipeline.py               # end-to-end run, candidate list (Option B)
  blockchain.py             # local hash-chain implementation
  anchor.py                 # hashes + writes a match to the chain
  verify.py                 # re-hashes + checks against the chain
  tamper_demo.py            # demonstrates tamper detection
  onchain_testnet.py        # optional Polygon Amoy alternative
demo/
  query/                    # put your query photo here
  candidates/                # sample images for offline mode
  candidates.example.txt
requirements.txt
```

---

## ✅ Requirements checklist

| Brief requirement | Status |
|---|:---:|
| Detect & encode a face from an input image | ✅ |
| Genuine web/social search — not hardcoded | ✅ |
| Blockchain upload of matched data / hash | ✅ |
| Demonstrable re-verification against on-chain record | ✅ |
| No hosted website required | ✅ |
| Full source in a GitHub repo + README (what/how/chain/limitations) | ✅ |

---

## ⚠️ Known limitations

- **Encoder accuracy**: LBP histograms are a legitimate, classic face
  descriptor but far less accurate than modern deep embeddings across
  pose/lighting/age changes, and are somewhat sensitive to small
  pixel-level shifts introduced by lossy re-encoding (e.g. WEBP).
  For production accuracy, swap `face_encode.py` for `face_recognition`
  (dlib) or `insightface` (ArcFace) — same `encode()`/`compare()`
  interface, so nothing downstream changes.
- **Similarity threshold** (`FACE_MATCH_THRESHOLD` in `pipeline_web.py` /
  `MATCH_THRESHOLD` in `candidate_search.py`) is a hand-tuned default,
  not calibrated on a labeled dataset.
- **Search step scope**: Google Lens matches by general visual
  similarity (any object/scene), which is why every result is
  independently re-checked for a matching *face* before anything is
  anchored.
- **Local chain vs. public chain**: the default local chain proves
  tamper-evidence to anyone holding `chain.json`; it doesn't give the
  public third-party auditability of a real public ledger. Use
  `onchain_testnet.py` if that's required.
- **Proof-of-work** in `blockchain.py` is intentionally trivial (single
  `"0"` prefix) — demonstrates the mining concept, not meant as real
  security.
- **HEIC support** requires the optional `pillow-heif` package; without
  it, HEIC files will raise a clear error telling you to install it.
- **SerpApi upload limit**: 500 KB per image — handled automatically via
  auto-compression, but very large source photos may lose some detail
  in the process.
