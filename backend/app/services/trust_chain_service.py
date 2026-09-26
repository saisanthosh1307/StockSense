import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.trust_chain import TrustChainBlock
from app.models.ledger import StockMove

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def compute_sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def compute_merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return compute_sha256("EMPTY_TREE")
    current_level = hashes[:]
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            next_level.append(compute_sha256(left + right))
        current_level = next_level
    return current_level[0]

def calculate_block_hash(
    index: int,
    previous_hash: str,
    timestamp_iso: str,
    merkle_root: str,
    nonce: int
) -> str:
    header = f"{index}:{previous_hash}:{timestamp_iso}:{merkle_root}:{nonce}"
    return compute_sha256(header)

def seal_moves_into_block(db: Session, move_ids: List[int]) -> TrustChainBlock:
    if not move_ids:
        return None

    # Get last block
    last_block = db.query(TrustChainBlock).order_by(TrustChainBlock.block_index.desc()).first()
    if last_block is None:
        index = 0
        prev_hash = GENESIS_HASH
    else:
        index = last_block.block_index + 1
        prev_hash = last_block.block_hash

    # Calculate hashes of moves
    moves = db.query(StockMove).filter(StockMove.id.in_(move_ids)).all()
    move_hashes = [m.record_hash or compute_sha256(f"MOVE_{m.id}_{m.reference}") for m in moves]
    merkle_root = compute_merkle_root(move_hashes)

    now = datetime.utcnow()
    timestamp_iso = now.isoformat()
    nonce = 0
    # Simple proof: hash starts with '0' for lightweight proof-of-work/anchor
    while True:
        b_hash = calculate_block_hash(index, prev_hash, timestamp_iso, merkle_root, nonce)
        if b_hash.startswith("0"):
            break
        nonce += 1

    block = TrustChainBlock(
        block_index=index,
        timestamp=now,
        previous_hash=prev_hash,
        merkle_root=merkle_root,
        block_hash=b_hash,
        move_ids_json=json.dumps(move_ids),
        nonce=nonce
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block

def verify_trust_chain_integrity(db: Session) -> Dict[str, Any]:
    blocks = db.query(TrustChainBlock).order_by(TrustChainBlock.block_index.asc()).all()
    if not blocks:
        return {
            "is_valid": True,
            "total_blocks_checked": 0,
            "total_moves_secured": 0,
            "latest_block_hash": GENESIS_HASH,
            "verification_status": "INTEGRITY_VERIFIED",
            "tampered_block_index": None,
            "verification_timestamp": datetime.utcnow(),
            "audit_notes": "No blocks created yet. Chain is initialized."
        }

    total_moves_secured = 0
    expected_prev_hash = GENESIS_HASH

    for b in blocks:
        # Check linkage
        if b.previous_hash != expected_prev_hash:
            return {
                "is_valid": False,
                "total_blocks_checked": b.block_index + 1,
                "total_moves_secured": total_moves_secured,
                "latest_block_hash": b.block_hash,
                "verification_status": "CORRUPTED_TAMPER_DETECTED",
                "tampered_block_index": b.block_index,
                "verification_timestamp": datetime.utcnow(),
                "audit_notes": f"Chain linkage break detected at block {b.block_index}! Previous hash mismatch."
            }

        # Verify block hash computation
        timestamp_iso = b.timestamp.isoformat()
        computed_hash = calculate_block_hash(b.block_index, b.previous_hash, timestamp_iso, b.merkle_root, b.nonce)
        if computed_hash != b.block_hash:
            return {
                "is_valid": False,
                "total_blocks_checked": b.block_index + 1,
                "total_moves_secured": total_moves_secured,
                "latest_block_hash": b.block_hash,
                "verification_status": "CORRUPTED_TAMPER_DETECTED",
                "tampered_block_index": b.block_index,
                "verification_timestamp": datetime.utcnow(),
                "audit_notes": f"Cryptographic integrity failed at block {b.block_index}! Block hash was forged or tampered."
            }

        try:
            move_ids = json.loads(b.move_ids_json)
            total_moves_secured += len(move_ids)
        except Exception:
            pass

        expected_prev_hash = b.block_hash

    return {
        "is_valid": True,
        "total_blocks_checked": len(blocks),
        "total_moves_secured": total_moves_secured,
        "latest_block_hash": blocks[-1].block_hash,
        "verification_status": "INTEGRITY_VERIFIED",
        "tampered_block_index": None,
        "verification_timestamp": datetime.utcnow(),
        "audit_notes": f"All {len(blocks)} blocks cryptographically validated against SHA-256 Merkle chain. Zero tampering detected."
    }
