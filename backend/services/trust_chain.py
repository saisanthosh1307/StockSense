import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.models.ledger import TrustChainBlock

def calculate_sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def calculate_merkle_root(items: List[str]) -> str:
    if not items:
        return calculate_sha256("empty")
    current_level = [calculate_sha256(str(item)) for item in items]
    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])
        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i+1]
            next_level.append(calculate_sha256(combined))
        current_level = next_level
    return current_level[0]

def calculate_block_hash(
    index: int,
    previous_hash: str,
    timestamp_str: str,
    merkle_root: str,
    payload_summary: str,
    nonce: int = 0
) -> str:
    data_string = f"{index}:{previous_hash}:{timestamp_str}:{merkle_root}:{payload_summary}:{nonce}"
    return calculate_sha256(data_string)

class TrustChainService:
    @staticmethod
    def initialize_genesis_block_if_needed(db: Session) -> TrustChainBlock:
        genesis = db.query(TrustChainBlock).filter(TrustChainBlock.block_index == 0).first()
        if not genesis:
            timestamp = datetime.utcnow()
            timestamp_str = timestamp.isoformat()
            prev_hash = "0" * 64
            summary = json.dumps({"event": "Genesis Block", "network": "StockSense Trust Chain"})
            merkle = calculate_merkle_root(["genesis_transaction"])
            b_hash = calculate_block_hash(0, prev_hash, timestamp_str, merkle, summary, 0)
            
            genesis = TrustChainBlock(
                block_index=0,
                timestamp=timestamp,
                previous_hash=prev_hash,
                block_hash=b_hash,
                merkle_root=merkle,
                transaction_count=1,
                payload_summary=summary,
                nonce=0
            )
            db.add(genesis)
            db.commit()
            db.refresh(genesis)
        return genesis

    @staticmethod
    def append_transaction_block(db: Session, transactions: List[Dict[str, Any]], summary_text: str) -> TrustChainBlock:
        TrustChainService.initialize_genesis_block_if_needed(db)
        
        last_block = db.query(TrustChainBlock).order_index = db.query(TrustChainBlock).order_by(TrustChainBlock.block_index.desc()).first()
        next_index = (last_block.block_index + 1) if last_block else 0
        prev_hash = last_block.block_hash if last_block else "0" * 64
        
        tx_strings = [json.dumps(tx, sort_keys=True, default=str) for tx in transactions]
        merkle = calculate_merkle_root(tx_strings)
        
        timestamp = datetime.utcnow()
        timestamp_str = timestamp.isoformat()
        payload_summary = json.dumps({"summary": summary_text, "tx_count": len(transactions), "items": transactions[:3]})
        
        block_hash = calculate_block_hash(next_index, prev_hash, timestamp_str, merkle, payload_summary, 0)
        
        block = TrustChainBlock(
            block_index=next_index,
            timestamp=timestamp,
            previous_hash=prev_hash,
            block_hash=block_hash,
            merkle_root=merkle,
            transaction_count=len(transactions),
            payload_summary=payload_summary,
            nonce=0
        )
        db.add(block)
        db.commit()
        db.refresh(block)
        return block

    @staticmethod
    def verify_chain_integrity(db: Session) -> Tuple[bool, str, List[Dict[str, Any]]]:
        blocks = db.query(TrustChainBlock).order_by(TrustChainBlock.block_index.asc()).all()
        if not blocks:
            return True, "No blocks in trust chain", []
            
        report = []
        for i in range(len(blocks)):
            current = blocks[i]
            expected_hash = calculate_block_hash(
                current.block_index,
                current.previous_hash,
                current.timestamp.isoformat(),
                current.merkle_root,
                current.payload_summary,
                current.nonce
            )
            is_hash_valid = (expected_hash == current.block_hash)
            
            is_prev_valid = True
            if i > 0:
                prev = blocks[i - 1]
                if current.previous_hash != prev.block_hash:
                    is_prev_valid = False
            elif current.block_index == 0:
                if current.previous_hash != "0" * 64:
                    is_prev_valid = False
                    
            status_ok = is_hash_valid and is_prev_valid
            report.append({
                "block_index": current.block_index,
                "block_hash": current.block_hash,
                "previous_hash": current.previous_hash,
                "valid": status_ok,
                "timestamp": current.timestamp.isoformat(),
                "tx_count": current.transaction_count
            })
            
            if not status_ok:
                return False, f"Tampering detected at block {current.block_index}", report
                
        return True, "All trust chain blocks verified cryptographically intact", report
