"""
Seed script for StockSense - Populates realistic demo data matching the PDF problem statement
with Indian names, Indian manufacturing hubs, and INR (₹) currency.
"""
from datetime import datetime, timedelta
from app.database import SessionLocal, engine, Base
import app.models # registers models
from app.models.user import User, RoleEnum
from app.models.inventory import Product, Category, Warehouse, Location, LocationType, StockQuant
from app.models.operations import (
    Receipt, ReceiptLine, Delivery, DeliveryLine, Transfer, TransferLine,
    Adjustment, AdjustmentLine, DocStatus, LossCauseEnum
)
from app.models.audit import Alert, AlertSeverity, AlertType, AuditLog
from app.services.auth_service import hash_password
from app.services.stock_ledger_service import (
    execute_stock_move,
    validate_receipt_operation,
    validate_delivery_operation,
    validate_transfer_operation,
    validate_adjustment_operation,
    get_or_create_virtual_location
)

def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # If already seeded with old data, wipe and re-seed with Indian context
    existing_user = db.query(User).first()
    if existing_user and "Elena" in existing_user.name:
        print("Migrating database to Indian names and INR currency...")
        db.close()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
    elif existing_user:
        print("Database already seeded with Indian context. Skipping.")
        db.close()
        return

    print("Seeding StockSense database with Indian context (INR Rs.)...")

    # 1. Users (Indian Names & Roles)
    admin_user = User(
        name="Aarav Sharma (Admin)",
        email="admin@stocksense.in",
        hashed_password=hash_password("admin123"),
        role=RoleEnum.ADMIN,
        is_active=True
    )
    manager_user = User(
        name="Priya Patel (Inventory Manager)",
        email="manager@stocksense.in",
        hashed_password=hash_password("manager123"),
        role=RoleEnum.INVENTORY_MANAGER,
        is_active=True
    )
    staff_user = User(
        name="Rohan Verma (Warehouse Staff)",
        email="staff@stocksense.in",
        hashed_password=hash_password("staff123"),
        role=RoleEnum.WAREHOUSE_STAFF,
        is_active=True
    )
    db.add_all([admin_user, manager_user, staff_user])
    db.commit()
    db.refresh(admin_user)
    db.refresh(manager_user)
    db.refresh(staff_user)

    # 2. Categories
    cat_raw = Category(name="Raw Materials", description="Metals, alloys, raw polymers, and fabrication bars")
    cat_parts = Category(name="Components & Parts", description="Motors, fasteners, bearings, and modular brackets")
    cat_finished = Category(name="Finished Goods", description="Ready-to-ship assembled furniture and equipment")
    db.add_all([cat_raw, cat_parts, cat_finished])
    db.commit()

    # 3. Warehouses (Indian Logistics Hubs)
    wh_main = Warehouse(code="WH-MUM", name="Main Warehouse (Bhiwandi Hub)", address="Plot 42, Logistics Park, Bhiwandi, Maharashtra 421302", is_active=1)
    wh_dist = Warehouse(code="WH-BLR", name="Distribution Center 2 (Whitefield Bengaluru)", address="EPIP Zone, Whitefield, Bengaluru, Karnataka 560066", is_active=1)
    db.add_all([wh_main, wh_dist])
    db.commit()
    db.refresh(wh_main)
    db.refresh(wh_dist)

    # Virtual Locations
    vendor_loc = get_or_create_virtual_location(db, LocationType.VENDOR)
    customer_loc = get_or_create_virtual_location(db, LocationType.CUSTOMER)
    loss_loc = get_or_create_virtual_location(db, LocationType.INVENTORY_LOSS)

    # Physical Locations for WH-MUM (Bhiwandi)
    loc_main_store = Location(
        name="Main Store",
        code="WH-MUM/STOCK",
        warehouse_id=wh_main.id,
        location_type=LocationType.INTERNAL,
        zone="Zone A", aisle="Aisle 1", rack="Rack 01", shelf="Shelf A", max_capacity=1000.0
    )
    loc_prod_rack = Location(
        name="Production Rack",
        code="WH-MUM/PROD",
        warehouse_id=wh_main.id,
        location_type=LocationType.INTERNAL,
        zone="Zone B", aisle="Aisle 2", rack="Rack 02", shelf="Shelf B", max_capacity=800.0
    )
    loc_rack_a = Location(
        name="Rack A",
        code="WH-MUM/RACK-A",
        warehouse_id=wh_main.id,
        location_type=LocationType.INTERNAL,
        zone="Zone A", aisle="Aisle 1", rack="Rack 01", shelf="Shelf B", max_capacity=500.0
    )
    loc_rack_b = Location(
        name="Rack B",
        code="WH-MUM/RACK-B",
        warehouse_id=wh_main.id,
        location_type=LocationType.INTERNAL,
        zone="Zone A", aisle="Aisle 1", rack="Rack 02", shelf="Shelf A", max_capacity=500.0
    )
    # Physical Location for WH-BLR
    loc_dist_stock = Location(
        name="Bengaluru Central Stock",
        code="WH-BLR/STOCK",
        warehouse_id=wh_dist.id,
        location_type=LocationType.INTERNAL,
        zone="Zone C", aisle="Aisle 3", rack="Rack 03", shelf="Shelf A", max_capacity=1500.0
    )
    db.add_all([loc_main_store, loc_prod_rack, loc_rack_a, loc_rack_b, loc_dist_stock])
    db.commit()
    db.refresh(loc_main_store)
    db.refresh(loc_prod_rack)
    db.refresh(loc_rack_a)
    db.refresh(loc_rack_b)
    db.refresh(loc_dist_stock)

    # 4. Products (Matches Problem Statement PDF examples in INR ₹)
    p_steel = Product(
        name="Steel",
        sku="RAW-STEEL-KG",
        category_id=cat_raw.id,
        uom="kg",
        barcode="BAR-STL-001",
        description="High tensile construction grade raw steel sheets",
        unit_cost=55.0,     # ₹55 / kg
        unit_price=85.0,    # ₹85 / kg
        min_reorder_qty=40.0,
        max_reorder_qty=300.0,
        lead_time_days=5
    )
    p_rods = Product(
        name="Steel Rods (12mm)",
        sku="STEEL-ROD-12",
        category_id=cat_raw.id,
        uom="Units",
        barcode="BAR-ROD-012",
        description="12mm ribbed reinforced steel rods for structural frames",
        unit_cost=450.0,    # ₹450 / unit
        unit_price=680.0,   # ₹680 / unit
        min_reorder_qty=25.0,
        max_reorder_qty=150.0,
        lead_time_days=7
    )
    p_chair = Product(
        name="Ergonomic Office Chair",
        sku="FURN-CHAIR-01",
        category_id=cat_finished.id,
        uom="Units",
        barcode="BAR-CHR-901",
        description="Executive breathable mesh swivel chair with lumbar support",
        unit_cost=4500.0,   # ₹4,500 / unit
        unit_price=8200.0,  # ₹8,200 / unit
        min_reorder_qty=12.0,
        max_reorder_qty=80.0,
        lead_time_days=10
    )
    p_motor = Product(
        name="Electric Motor 2HP",
        sku="ELEC-MTR-02",
        category_id=cat_parts.id,
        uom="Units",
        barcode="BAR-MTR-202",
        description="Single phase industrial induction electric motor",
        unit_cost=8500.0,   # ₹8,500 / unit
        unit_price=14500.0, # ₹14,500 / unit
        min_reorder_qty=8.0,
        max_reorder_qty=50.0,
        lead_time_days=14
    )
    p_screws = Product(
        name="Industrial Screws M8 (Box of 500)",
        sku="FAST-SCRW-M8",
        category_id=cat_parts.id,
        uom="Boxes",
        barcode="BAR-SCR-088",
        description="Zinc plated countersunk corrosion resistant screws",
        unit_cost=350.0,    # ₹350 / box
        unit_price=650.0,   # ₹650 / box
        min_reorder_qty=30.0,
        max_reorder_qty=200.0,
        lead_time_days=4
    )
    db.add_all([p_steel, p_rods, p_chair, p_motor, p_screws])
    db.commit()
    for p in [p_steel, p_rods, p_chair, p_motor, p_screws]:
        db.refresh(p)

    print("Executing inventory flow steps matching PDF problem statement...")

    # Step 1 : Receive Goods from Vendor (PDF Page 3 & 4)
    # Receive 100 kg Steel -> Stock: +100
    # Receive 50 units "Steel Rods" -> stock +50
    # Receive 30 units Chairs -> stock +30
    rec1 = Receipt(
        reference="REC/2026/0001",
        supplier_name="Tata Steel BSL Limited",
        destination_location_id=loc_main_store.id,
        status=DocStatus.READY,
        notes="PO-8821: Raw metal shipment from Jamshedpur plant",
        created_by_user_id=manager_user.id
    )
    db.add(rec1)
    db.commit()
    db.refresh(rec1)

    rline1 = ReceiptLine(receipt_id=rec1.id, product_id=p_steel.id, quantity_expected=100.0, quantity_received=100.0, unit_cost=p_steel.unit_cost)
    rline2 = ReceiptLine(receipt_id=rec1.id, product_id=p_rods.id, quantity_expected=50.0, quantity_received=50.0, unit_cost=p_rods.unit_cost)
    rline3 = ReceiptLine(receipt_id=rec1.id, product_id=p_chair.id, quantity_expected=30.0, quantity_received=30.0, unit_cost=p_chair.unit_cost)
    rline4 = ReceiptLine(receipt_id=rec1.id, product_id=p_motor.id, quantity_expected=25.0, quantity_received=25.0, unit_cost=p_motor.unit_cost)
    rline5 = ReceiptLine(receipt_id=rec1.id, product_id=p_screws.id, quantity_expected=80.0, quantity_received=80.0, unit_cost=p_screws.unit_cost)
    db.add_all([rline1, rline2, rline3, rline4, rline5])
    db.commit()

    # Validate Receipt 1 -> stock increases automatically!
    validate_receipt_operation(db, rec1.id, user_id=manager_user.id)

    # Step 2 : Internal Transfer: Main Store -> Production Rack (PDF Page 4)
    # Move 20 kg steel: Main Store -> Production Rack (Stock unchanged in total, but new location updated)
    # Move 10 steel rods: Main Store -> Rack A
    trans1 = Transfer(
        reference="INT/2026/0001",
        source_location_id=loc_main_store.id,
        destination_location_id=loc_prod_rack.id,
        status=DocStatus.READY,
        notes="Transfer raw materials for chassis assembly in Pune line",
        created_by_user_id=staff_user.id
    )
    db.add(trans1)
    db.commit()
    db.refresh(trans1)
    tline1 = TransferLine(transfer_id=trans1.id, product_id=p_steel.id, quantity=20.0)
    db.add(tline1)
    db.commit()
    validate_transfer_operation(db, trans1.id, user_id=staff_user.id)

    # Step 3 : Deliver finished goods (PDF Page 3 & 4)
    # Sales order for 10 chairs -> reduces 10
    # Deliver 20 steel
    deliv1 = Delivery(
        reference="DEL/2026/0001",
        customer_name="Godrej Interio Solutions Mumbai",
        source_location_id=loc_main_store.id,
        status=DocStatus.READY,
        notes="Customer SO-5012 priority delivery for BKC office project",
        created_by_user_id=manager_user.id
    )
    db.add(deliv1)
    db.commit()
    db.refresh(deliv1)
    dline1 = DeliveryLine(delivery_id=deliv1.id, product_id=p_chair.id, quantity_demanded=10.0, quantity_done=10.0)
    db.add(dline1)
    db.commit()
    validate_delivery_operation(db, deliv1.id, user_id=staff_user.id)

    # Step 4 : Adjust damaged items (PDF Page 4)
    # 3 kg steel damaged -> Stock: -3
    adj1 = Adjustment(
        reference="ADJ/2026/0001",
        location_id=loc_prod_rack.id,
        status=DocStatus.READY,
        notes="Physical cycle count mismatch: 3 kg damaged during bending operation",
        created_by_user_id=staff_user.id
    )
    db.add(adj1)
    db.commit()
    db.refresh(adj1)
    # Currently prod rack has 20.0 steel, counted is 17.0
    aline1 = AdjustmentLine(
        adjustment_id=adj1.id,
        product_id=p_steel.id,
        recorded_qty=20.0,
        counted_qty=17.0,
        difference_qty=-3.0,
        loss_cause=LossCauseEnum.DAMAGE_HANDLING
    )
    db.add(aline1)
    db.commit()
    validate_adjustment_operation(db, adj1.id, user_id=staff_user.id)

    # Add a pending receipt and delivery for realistic dashboard KPI demoing
    rec_pending = Receipt(
        reference="REC/2026/0002",
        supplier_name="Kirloskar Electric Systems Pune",
        destination_location_id=loc_main_store.id,
        status=DocStatus.WAITING,
        notes="Scheduled motor delivery for next Tuesday",
        created_by_user_id=manager_user.id
    )
    db.add(rec_pending)
    db.commit()
    db.refresh(rec_pending)
    db.add(ReceiptLine(receipt_id=rec_pending.id, product_id=p_motor.id, quantity_expected=20.0, quantity_received=0.0, unit_cost=p_motor.unit_cost))
    db.commit()

    del_pending = Delivery(
        reference="DEL/2026/0002",
        customer_name="Larsen & Toubro Logistics Hub",
        source_location_id=loc_main_store.id,
        status=DocStatus.WAITING,
        notes="Awaiting carrier pickup for Powai facility",
        created_by_user_id=manager_user.id
    )
    db.add(del_pending)
    db.commit()
    db.refresh(del_pending)
    db.add(DeliveryLine(delivery_id=del_pending.id, product_id=p_chair.id, quantity_demanded=5.0, quantity_done=0.0))
    db.commit()

    print("Seed completed successfully! StockSense database initialized with Indian names & INR (Rs.).")
    db.close()

if __name__ == "__main__":
    run_seed()
