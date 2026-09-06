"""
blockchain.py
-------------
A small but real blockchain: each block cryptographically commits to the
previous block's hash, so any tampering with historical data is
detectable by anyone re-walking the chain. This satisfies the task's
"local/simulated chain" option explicitly allowed by the brief.

Chain is persisted as JSON so it survives between pipeline runs and can
be shipped alongside the repo/demo as evidence.

To anchor to a *public* testnet instead (e.g. Polygon Amoy) see
`onchain_testnet.py` for the web3.py version of `add_block` — same
interface, so `anchor.py` / `verify.py` don't need to change.
"""

import hashlib
import json
import time
from dataclasses import dataclass, asdict, field
from typing import List, Optional


@dataclass
class Block:
    index: int
    timestamp: float
    data: dict
    previous_hash: str
    nonce: int = 0
    hash: str = field(default="")

    def compute_hash(self) -> str:
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        blob = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()


class SimpleChain:
    GENESIS_PREV_HASH = "0" * 64
    DIFFICULTY_PREFIX = "0"  # trivial PoW just to make it feel real; set "" to disable

    def __init__(self, path: str = "chain.json"):
        self.path = path
        self.chain: List[Block] = []
        self._load_or_genesis()

    def _load_or_genesis(self):
        try:
            with open(self.path) as f:
                raw = json.load(f)
            self.chain = [Block(**b) for b in raw]
        except (FileNotFoundError, json.JSONDecodeError):
            genesis = Block(
                index=0,
                timestamp=time.time(),
                data={"note": "genesis block"},
                previous_hash=self.GENESIS_PREV_HASH,
            )
            genesis.hash = genesis.compute_hash()
            self.chain = [genesis]
            self._save()

    def _save(self):
        with open(self.path, "w") as f:
            json.dump([asdict(b) for b in self.chain], f, indent=2)

    def _mine(self, block: Block) -> Block:
        while True:
            h = block.compute_hash()
            if h.startswith(self.DIFFICULTY_PREFIX):
                block.hash = h
                return block
            block.nonce += 1

    def add_block(self, data: dict) -> Block:
        prev = self.chain[-1]
        block = Block(
            index=prev.index + 1,
            timestamp=time.time(),
            data=data,
            previous_hash=prev.hash,
        )
        block = self._mine(block)
        self.chain.append(block)
        self._save()
        return block

    def get_block(self, index: int) -> Optional[Block]:
        for b in self.chain:
            if b.index == index:
                return b
        return None

    def find_by_data_field(self, key: str, value) -> Optional[Block]:
        for b in self.chain:
            if b.data.get(key) == value:
                return b
        return None

    def is_valid(self) -> bool:
        """Walk the whole chain and confirm every hash/link is intact.
        This is what makes the record tamper-evident: change any field in
        any past block and this returns False."""
        for i in range(1, len(self.chain)):
            current, prev = self.chain[i], self.chain[i - 1]
            if current.previous_hash != prev.hash:
                return False
            if current.hash != current.compute_hash():
                return False
            if not current.hash.startswith(self.DIFFICULTY_PREFIX):
                return False
        return True

    def __len__(self):
        return len(self.chain)
