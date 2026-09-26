from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services.digital_twin_service import DigitalTwinService

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])

@router.get("/warehouse/{warehouse_id}")
def get_warehouse_digital_twin(
    warehouse_id: int,
    route_id: Optional[int] = Query(None, description="Optional active picking route ID to overlay"),
    db: Session = Depends(get_db)
):
    try:
        return DigitalTwinService.get_warehouse_twin_data(db, warehouse_id, route_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
