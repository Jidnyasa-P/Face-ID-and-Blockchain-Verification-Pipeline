"""
onchain_testnet.py
-------------------
OPTIONAL upgrade path: anchor the same record to a real public testnet
(Polygon Amoy) instead of the local simulated chain, using a minimal
smart contract that stores hash -> metadata mappings.

This is NOT wired into pipeline.py by default because it requires:
  - an RPC endpoint (e.g. from Alchemy/Infura's free tier)
  - a funded testnet wallet (free faucet ETH/MATIC)
  - deploying the contract below once

If you want to use this for your demo instead of the local chain, deploy
`Anchor.sol`, fill in the constants below, then swap
`from blockchain import SimpleChain` for this module's `TestnetAnchor`
in pipeline.py (both expose an `add_block(data) -> {index/hash}`-shaped
interface so the rest of the pipeline doesn't change).

--------------------------------------------------------------------
Anchor.sol (deploy this first, e.g. via Remix + MetaMask on Amoy):

    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.20;

    contract Anchor {
        struct Record {
            string postUrl;
            string imageSha256;
            uint256 similarityBp; // similarity * 10000, as an integer
            uint256 timestamp;
        }

        Record[] public records;

        event Anchored(uint256 indexed id, string imageSha256, string postUrl);

        function addRecord(
            string calldata postUrl,
            string calldata imageSha256,
            uint256 similarityBp
        ) external returns (uint256) {
            records.push(Record(postUrl, imageSha256, similarityBp, block.timestamp));
            uint256 id = records.length - 1;
            emit Anchored(id, imageSha256, postUrl);
            return id;
        }

        function getRecord(uint256 id) external view returns (Record memory) {
            return records[id];
        }

        function totalRecords() external view returns (uint256) {
            return records.length;
        }
    }
--------------------------------------------------------------------

pip install web3
"""

RPC_URL = "https://rpc-amoy.polygon.technology"  # or your Alchemy/Infura Amoy URL
CONTRACT_ADDRESS = "0xYourDeployedContractAddress"
PRIVATE_KEY = "0xYourTestnetWalletPrivateKey"  # NEVER use a mainnet key here

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "postUrl", "type": "string"},
            {"internalType": "string", "name": "imageSha256", "type": "string"},
            {"internalType": "uint256", "name": "similarityBp", "type": "uint256"},
        ],
        "name": "addRecord",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
        "name": "getRecord",
        "outputs": [
            {
                "components": [
                    {"internalType": "string", "name": "postUrl", "type": "string"},
                    {"internalType": "string", "name": "imageSha256", "type": "string"},
                    {"internalType": "uint256", "name": "similarityBp", "type": "uint256"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                ],
                "internalType": "struct Anchor.Record",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


class TestnetAnchor:
    def __init__(self):
        from web3 import Web3  # imported lazily so this file doesn't hard-require web3

        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
        self.contract = self.w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

    def add_block(self, data: dict) -> dict:
        similarity_bp = int(round(data["similarity_score"] * 10000))
        tx = self.contract.functions.addRecord(
            data["post_url"], data["image_sha256"], similarity_bp
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"tx_hash": tx_hash.hex(), "block_number": receipt.blockNumber}

    def get_record(self, record_id: int):
        return self.contract.functions.getRecord(record_id).call()
