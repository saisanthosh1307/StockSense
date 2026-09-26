from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import Warehouse, Location, LocationType, StockQuant
from app.models.user import RoleEnum, User
from app.schemas.inventory import (
    WarehouseCreate,
    WarehouseOut,
    LocationCreate,
    LocationOut,
)
from app.api.deps import require_role

router = APIRouter(prefix="/warehouses", tags=["3. Warehouses & Locations"])

@router.post("", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.INVENTORY_MANAGER]))
):
    existing = db.query(Warehouse).filter(Warehouse.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Warehouse code already exists.")
    
    wh = Warehouse(
        code=payload.code,
        name=payload.name,
        address=payload.address,
        is_active=payload.is_active
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)

    # Automatically initialize default internal stock location for this warehouse
    default_loc = Location(
        name=f"{wh.name} / Stock",
        code=f"{wh.code}/STOCK",
        warehouse_id=wh.id,
        location_type=LocationType.INTERNAL,
        zone="Zone A",
        aisle="Aisle 1",
        rack="Rack 01",
        shelf="Shelf A",
        max_capacity=2000.0
    )
    db.add(default_loc)
    db.commit()
    db.refresh(wh)
    return wh

@router.get("", response_model=List[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(Warehouse).all()

@router.get("/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found.")
    return wh

# Locations / Racks
@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.INVENTORY_MANAGER]))
):
    existing = db.query(Location).filter(Location.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Location code already exists.")
    
    loc = Location(
        name=payload.name,
        code=payload.code,
        warehouse_id=payload.warehouse_id,
        location_type=payload.location_type,
        zone=payload.zone,
        aisle=payload.aisle,
        rack=payload.rack,
        shelf=payload.shelf,
        max_capacity=payload.max_capacity
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc

@router.get("/locations/all", response_model=List[LocationOut])
def list_locations(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Location)
    if warehouse_id:
        query = query.filter(Location.warehouse_id == warehouse_id)
    return query.all()
