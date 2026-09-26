from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.trust_chain import TrustChainBlock
from app.schemas.showcase import (
    DigitalTwinWarehouseResponse,
    TrustChainBlockOut,
    TrustChainVerifyResponse,
    AIAssistantRequest,
    AIAssistantResponse,
)
from app.services.digital_twin_service import get_warehouse_digital_twin
from app.services.trust_chain_service import verify_trust_chain_integrity
from app.services.ai_assistant_service import query_ai_assistant

router = APIRouter(prefix="/showcase", tags=["Showcase Features (3 Features)"])

# 1. Digital Twin
@router.get("/digital-twin/{warehouse_id}", response_model=DigitalTwinWarehouseResponse)
def get_digital_twin(warehouse_id: int, db: Session = Depends(get_db)):
    """
    1. Digital Twin: Virtual 2D/3D warehouse mapping, rack slot capacity, and pick frequency heatmaps.
    """
    try:
        return get_warehouse_digital_twin(db, warehouse_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# 2. Trust Chain
@router.get("/trust-chain/blocks", response_model=List[TrustChainBlockOut])
def get_trust_chain_blocks(limit: int = 50, db: Session = Depends(get_db)):
    """
    2a. Trust Chain Blocks: Inspect the cryptographic blockchain blocks sealing stock movements.
    """
    blocks = db.query(TrustChainBlock).order_by(TrustChainBlock.block_index.desc()).limit(limit).all()
    out = []
    for b in blocks:
        try:
            import json
            moves = json.loads(b.move_ids_json)
            count = len(moves)
        except Exception:
            count = 1
        out.append(
            TrustChainBlockOut(
                id=b.id,
                block_index=b.block_index,
                timestamp=b.timestamp,
                previous_hash=b.previous_hash,
                merkle_root=b.merkle_root,
                block_hash=b.block_hash,
                move_count=count,
                nonce=b.nonce
            )
        )
    return out

@router.get("/trust-chain/verify", response_model=TrustChainVerifyResponse)
def verify_trust_chain(db: Session = Depends(get_db)):
    """
    2b. Trust Chain Audit: Mathematically audits all blocks from genesis to tip, verifying zero tampering.
    """
    return verify_trust_chain_integrity(db)

# 3. AI Assistant
@router.post("/ai-assistant/chat", response_model=AIAssistantResponse)
def chat_with_ai_assistant(payload: AIAssistantRequest, db: Session = Depends(get_db)):
    """
    3. AI Assistant: Conversational inventory copilot for stock queries, forecast explanations, and risk advice.
    """
    return query_ai_assistant(db, payload.message)
