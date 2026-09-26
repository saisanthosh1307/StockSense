from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["15. Audit Trail & Activity Logs"])

@router.get("/logs", response_model=List[AuditLogOut])
def get_audit_trail_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return [
        AuditLogOut(
            id=log.id,
            user_id=log.user_id,
            user_name=log.user.name if log.user else "System / Automated",
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            timestamp=log.timestamp
        )
        for log in logs
    ]
