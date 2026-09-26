from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, RoleEnum
from app.schemas.auth import UserOut, UserRoleUpdate
from app.api.deps import require_role, require_auth

router = APIRouter(prefix="/roles", tags=["13. Roles & RBAC"])

ROLE_PERMISSIONS_MATRIX = {
    RoleEnum.ADMIN.value: {
        "description": "Full access to inventory, users, system settings, blockchain audit, and configurations.",
        "permissions": [
            "manage_users", "create_products", "delete_products", "manage_warehouses",
            "validate_receipts", "validate_deliveries", "validate_transfers", "validate_adjustments",
            "view_audit_logs", "view_reports", "run_simulations", "verify_trust_chain"
        ]
    },
    RoleEnum.INVENTORY_MANAGER.value: {
        "description": "Manages incoming & outgoing stock, reorder rules, approvals, and AI forecasting.",
        "permissions": [
            "create_products", "update_products", "create_receipts", "validate_receipts",
            "create_deliveries", "validate_deliveries", "run_intelligence_forecasting",
            "view_reports", "view_audit_logs"
        ]
    },
    RoleEnum.WAREHOUSE_STAFF.value: {
        "description": "Performs physical warehouse operations: internal transfers, picking, packing, shelving, counting.",
        "permissions": [
            "view_products", "create_transfers", "validate_transfers",
            "pick_deliveries", "pack_deliveries", "perform_stock_counts",
            "scan_qr_codes", "view_digital_twin"
        ]
    }
}

@router.get("/permissions")
def get_role_permissions_matrix():
    """
    Returns RBAC capability definition mapping roles to allowed operations.
    """
    return ROLE_PERMISSIONS_MATRIX

@router.get("/users", response_model=List[UserOut])
def list_system_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role([RoleEnum.ADMIN]))
):
    return db.query(User).all()

@router.put("/users/{user_id}", response_model=UserOut)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role([RoleEnum.ADMIN]))
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")
    target_user.role = payload.role
    db.commit()
    db.refresh(target_user)
    return target_user
