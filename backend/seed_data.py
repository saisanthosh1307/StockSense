from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session
from backend.database import Base, engine, SessionLocal
from backend.models.user import User, UserRole
from backend.models.inventory import Category, Warehouse, Location, Product, StockLevel
from backend.models.supplier import Supplier, SupplierMetric
from backend.models.batch import InventoryBatch, BatchStatus
from backend.models.operations import (
    Receipt, ReceiptItem, Delivery, DeliveryItem, InternalTransfer, StockAdjustment,
    OperationStatus, AdjustmentReason
)
from backend.models.ledger import StockLedger, TransactionType, AuditLog
from backend.services.auth_service import get_password_hash
from backend.services.trust_chain import TrustChainService
from backend.services.dead_stock_service import DeadStockService

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already seeded. Skipping initial seeding.")
            return

        print("Seeding StockSense database with comprehensive realistic data...")

        # 1. Users
        users = [
            User(username="admin", email="admin@stocksense.io", full_name="System Administrator", hashed_password=get_password_hash("admin123"), role=UserRole.ADMIN),
            User(username="manager", email="manager@stocksense.io", full_name="Inventory Operations Lead", hashed_password=get_password_hash("manager123"), role=UserRole.INVENTORY_MANAGER),
            User(username="staff", email="staff@stocksense.io", full_name="Warehouse Associate", hashed_password=get_password_hash("staff123"), role=UserRole.WAREHOUSE_STAFF),
        ]
        db.add_all(users)
        db.flush()
        admin_user = users[0]

        # 2. Genesis block
        TrustChainService.initialize_genesis_block_if_needed(db)

        # 3. Categories
        categories = [
            Category(name="Industrial Supplies", code="CAT-IND", description="Tools, fasteners, adhesives, and workshop consumables"),
            Category(name="Pharmaceuticals & Health", code="CAT-MED", description="Drugs, clinical supplies, and temperature-controlled items"),
            Category(name="Raw Materials", code="CAT-RAW", description="Metals, polymers, and structural stock"),
            Category(name="Office & Facility", code="CAT-OFF", description="Furniture, ergonomic fittings, and stationery"),
            Category(name="Electronics & Sensors", code="CAT-ELEC", description="Batteries, microcontrollers, and precision sensors")
        ]
        db.add_all(categories)
        db.flush()

        # 4. Warehouses
        warehouses = [
            Warehouse(name="Central Distribution Facility", code="WH-BLR-01", address="Industrial Corridor 4, Bengaluru, KA", capacity=25000),
            Warehouse(name="North Regional Depot", code="WH-DEL-02", address="Logistics Park Sector 8, New Delhi", capacity=18000),
            Warehouse(name="Western Port Hub", code="WH-MUM-03", address="Bhiwandi Freight Center, Mumbai, MH", capacity=20000),
        ]
        db.add_all(warehouses)
        db.flush()
        wh1, wh2, wh3 = warehouses[0], warehouses[1], warehouses[2]

        # 5. Locations (Coordinates for 2D/3D map & picking TSP routing)
        # Warehouse 1 Locations: Rack A1, A2, A3, B1, B2, C3, C4, D1, D2
        loc_defs = [
            # code, aisle, rack, shelf, x, y, z, capacity
            ("Rack A1", "A", "1", "1", 4.0, 4.0, 1.0, 1500),
            ("Rack A2", "A", "2", "1", 4.0, 8.0, 1.0, 1500),
            ("Rack A3", "A", "3", "1", 4.0, 14.0, 1.0, 1500),
            ("Rack B1", "B", "1", "1", 10.0, 4.0, 1.0, 1500),
            ("Rack B2", "B", "2", "1", 10.0, 9.0, 1.0, 1500),
            ("Rack C3", "C", "3", "1", 16.0, 11.0, 1.0, 1500),
            ("Rack C4", "C", "4", "1", 16.0, 16.0, 1.0, 1500),
            ("Rack D1", "D", "1", "1", 22.0, 5.0, 1.0, 1500),
            ("Rack D2", "D", "2", "1", 22.0, 12.0, 1.0, 1500),
        ]
        wh1_locations = {}
        for code, aisle, rack, shelf, x, y, z, cap in loc_defs:
            loc = Location(
                warehouse_id=wh1.id, code=code, aisle=aisle, rack=rack, shelf=shelf,
                x_coord=x, y_coord=y, z_coord=z, capacity=cap
            )
            db.add(loc)
            db.flush()
            wh1_locations[code] = loc

        # Secondary warehouses locations
        wh2_loc = Location(warehouse_id=wh2.id, code="Rack N1", aisle="N", rack="1", shelf="1", x_coord=5.0, y_coord=5.0, capacity=2000)
        wh3_loc = Location(warehouse_id=wh3.id, code="Rack W1", aisle="W", rack="1", shelf="1", x_coord=5.0, y_coord=5.0, capacity=2000)
        db.add_all([wh2_loc, wh3_loc])
        db.flush()

        # 6. Suppliers (matches specification exact example: ABC Metals, 94% on-time, 6.2d lead time, 98% accuracy, 1.4% damage)
        suppliers = [
            Supplier(name="ABC Metals", code="SUP-ABC", contact_name="Rajesh Sharma", email="rajesh@abcmetals.in", phone="+91 98450 11223", address="Peenya Industrial Estate, Bengaluru", expected_lead_time_days=6.0, rating=4.8),
            Supplier(name="Apex Pharma Supplies", code="SUP-APX", contact_name="Dr. Sunita Rao", email="orders@apexpharma.com", phone="+91 99801 33445", address="Genome Valley, Hyderabad", expected_lead_time_days=4.0, rating=4.9),
            Supplier(name="ChemiCraft Polymers", code="SUP-CCP", contact_name="Vikram Mehta", email="vikram@chemicraft.com", phone="+91 91234 56789", address="GIDC Estate, Vadodara", expected_lead_time_days=10.0, rating=3.9),
            Supplier(name="VoltTech Components", code="SUP-VTC", contact_name="Anita Sen", email="anita@volttech.in", phone="+91 98112 99887", address="Okhla Phase III, New Delhi", expected_lead_time_days=7.0, rating=4.4)
        ]
        db.add_all(suppliers)
        db.flush()
        sup_metals, sup_pharma, sup_chemi, sup_elec = suppliers[0], suppliers[1], suppliers[2], suppliers[3]

        # Seed supplier metrics
        # ABC Metals: on-time 94%, lead time 6.2 days, accuracy 98%, damage rate 1.4%
        metric_abc = SupplierMetric(
            supplier_id=sup_metals.id,
            total_orders=24,
            completed_orders=24,
            on_time_orders=22,
            delayed_orders=2,
            total_ordered_qty=5000.0,
            total_received_qty=4900.0,
            total_damaged_qty=68.6,
            average_lead_time_days=6.2,
            expected_avg_lead_time_days=6.0,
            on_time_delivery_pct=94.0,
            quantity_accuracy_pct=98.0,
            damage_rate_pct=1.4,
            reliability_score=94.5
        )
        metric_apx = SupplierMetric(
            supplier_id=sup_pharma.id,
            total_orders=30,
            completed_orders=30,
            on_time_orders=29,
            delayed_orders=1,
            total_ordered_qty=6200.0,
            total_received_qty=6180.0,
            total_damaged_qty=18.5,
            average_lead_time_days=4.2,
            expected_avg_lead_time_days=4.0,
            on_time_delivery_pct=96.7,
            quantity_accuracy_pct=99.2,
            damage_rate_pct=0.3,
            reliability_score=97.8
        )
        metric_chemi = SupplierMetric(
            supplier_id=sup_chemi.id,
            total_orders=18,
            completed_orders=18,
            on_time_orders=14,
            delayed_orders=4,
            total_ordered_qty=4200.0,
            total_received_qty=3850.0,
            total_damaged_qty=123.2,
            average_lead_time_days=11.4,
            expected_avg_lead_time_days=10.0,
            on_time_delivery_pct=77.8,
            quantity_accuracy_pct=91.6,
            damage_rate_pct=3.2,
            reliability_score=78.2
        )
        db.add_all([metric_abc, metric_apx, metric_chemi])
        db.flush()

        # 7. Products
        # 1) Industrial Glue: Stock 850, ₹150 cost, last movement 74 days ago, Value: ₹1,27,500, DEAD STOCK! (Exact spec)
        # 2) Medicine A: Perishable, FEFO Batches A (20 u, 12d), B (50 u, 60d), C (100 u, 120d)! (Exact spec)
        # 3) Steel Rods: Raw materials (from prompt)
        # 4) Ergonomic Office Chairs: Office supplies (from prompt)
        # 5) Nitrile Medical Gloves: Perishable, critical batch expiring in 6 days
        # 6) High Precision Bearing 6205
        # 7) Lithium Polymer Battery Pack
        now = datetime.utcnow()
        products = [
            Product(
                name="Industrial Glue",
                sku="SKU-GLUE-850",
                barcode="890123456001",
                category_id=categories[0].id,
                uom="Litre",
                min_stock_level=50,
                max_stock_level=200,
                reorder_point=80,
                cost_price=150.0,
                selling_price=220.0,
                is_perishable=True,
                shelf_life_days=180,
                default_supplier_id=sup_chemi.id,
                created_at=now - timedelta(days=120)
            ),
            Product(
                name="Medicine A (Amoxicillin 500mg)",
                sku="SKU-MED-A01",
                barcode="890123456002",
                category_id=categories[1].id,
                uom="Boxes",
                min_stock_level=40,
                max_stock_level=300,
                reorder_point=60,
                cost_price=350.0,
                selling_price=520.0,
                is_perishable=True,
                shelf_life_days=365,
                default_supplier_id=sup_pharma.id,
                created_at=now - timedelta(days=90)
            ),
            Product(
                name="Steel Rods 12mm TMT",
                sku="SKU-ROD-012",
                barcode="890123456003",
                category_id=categories[2].id,
                uom="kg",
                min_stock_level=100,
                max_stock_level=2000,
                reorder_point=250,
                cost_price=65.0,
                selling_price=85.0,
                is_perishable=False,
                default_supplier_id=sup_metals.id,
                created_at=now - timedelta(days=90)
            ),
            Product(
                name="Ergonomic Mesh Office Chair",
                sku="SKU-CHR-099",
                barcode="890123456004",
                category_id=categories[3].id,
                uom="Units",
                min_stock_level=15,
                max_stock_level=80,
                reorder_point=25,
                cost_price=4200.0,
                selling_price=6500.0,
                is_perishable=False,
                created_at=now - timedelta(days=90)
            ),
            Product(
                name="Nitrile Examination Gloves",
                sku="SKU-GLV-001",
                barcode="890123456005",
                category_id=categories[1].id,
                uom="Boxes",
                min_stock_level=50,
                max_stock_level=500,
                reorder_point=100,
                cost_price=220.0,
                selling_price=340.0,
                is_perishable=True,
                shelf_life_days=180,
                default_supplier_id=sup_pharma.id,
                created_at=now - timedelta(days=90)
            ),
            Product(
                name="High Precision Bearing 6205",
                sku="SKU-BRG-6205",
                barcode="890123456006",
                category_id=categories[0].id,
                uom="Units",
                min_stock_level=30,
                max_stock_level=250,
                reorder_point=45,
                cost_price=310.0,
                selling_price=480.0,
                is_perishable=False,
                default_supplier_id=sup_metals.id,
                created_at=now - timedelta(days=90)
            ),
            Product(
                name="Lithium Polymer Battery 5000mAh",
                sku="SKU-BAT-5000",
                barcode="890123456007",
                category_id=categories[4].id,
                uom="Units",
                min_stock_level=25,
                max_stock_level=150,
                reorder_point=40,
                cost_price=850.0,
                selling_price=1350.0,
                is_perishable=True,
                shelf_life_days=270,
                default_supplier_id=sup_elec.id,
                created_at=now - timedelta(days=90)
            )
        ]
        db.add_all(products)
        db.flush()

        prod_glue = products[0]
        prod_med = products[1]
        prod_rods = products[2]
        prod_chair = products[3]
        prod_gloves = products[4]
        prod_bearing = products[5]
        prod_battery = products[6]

        # 8. Stock Levels & Batches
        # Industrial Glue: 850 units in WH1 Rack A1 (74 days inactive)
        sl_glue = StockLevel(product_id=prod_glue.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack A1"].id, quantity=850, reserved_quantity=0)
        
        # Medicine A: 170 units total in WH1 Rack B2 across 3 batches:
        # Batch A -> 20 units -> Expires in 12 days
        # Batch B -> 50 units -> Expires in 60 days
        # Batch C -> 100 units -> Expires in 120 days
        sl_med = StockLevel(product_id=prod_med.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack B2"].id, quantity=170, reserved_quantity=0)
        
        batch_a = InventoryBatch(batch_number="BATCH-MED-A", product_id=prod_med.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack B2"].id, initial_quantity=20, current_quantity=20, reserved_quantity=0, manufacturing_date=now - timedelta(days=350), expiry_date=now + timedelta(days=12), cost_per_unit=350.0, status=BatchStatus.ACTIVE)
        batch_b = InventoryBatch(batch_number="BATCH-MED-B", product_id=prod_med.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack B2"].id, initial_quantity=50, current_quantity=50, reserved_quantity=0, manufacturing_date=now - timedelta(days=180), expiry_date=now + timedelta(days=60), cost_per_unit=350.0, status=BatchStatus.ACTIVE)
        batch_c = InventoryBatch(batch_number="BATCH-MED-C", product_id=prod_med.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack B2"].id, initial_quantity=100, current_quantity=100, reserved_quantity=0, manufacturing_date=now - timedelta(days=90), expiry_date=now + timedelta(days=120), cost_per_unit=350.0, status=BatchStatus.ACTIVE)

        # Nitrile Gloves: Batch expiring in 5 days (Critical Alert)
        sl_gloves = StockLevel(product_id=prod_gloves.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack A3"].id, quantity=110, reserved_quantity=0)
        batch_glv1 = InventoryBatch(batch_number="BATCH-GLV-CRIT", product_id=prod_gloves.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack A3"].id, initial_quantity=45, current_quantity=45, reserved_quantity=0, manufacturing_date=now - timedelta(days=175), expiry_date=now + timedelta(days=5), cost_per_unit=220.0, status=BatchStatus.ACTIVE)
        batch_glv2 = InventoryBatch(batch_number="BATCH-GLV-SAFE", product_id=prod_gloves.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack A3"].id, initial_quantity=65, current_quantity=65, reserved_quantity=0, manufacturing_date=now - timedelta(days=30), expiry_date=now + timedelta(days=150), cost_per_unit=220.0, status=BatchStatus.ACTIVE)

        # Steel rods: 420 kg in WH1 Rack C4
        sl_rods = StockLevel(product_id=prod_rods.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack C4"].id, quantity=420, reserved_quantity=0)
        
        # Office chairs: 18 units in WH1 Rack D1
        sl_chair = StockLevel(product_id=prod_chair.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack D1"].id, quantity=18, reserved_quantity=0)

        # Bearings: 15 units (Low stock!) in WH1 Rack A2
        sl_bearing = StockLevel(product_id=prod_bearing.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack A2"].id, quantity=15, reserved_quantity=0)

        # Batteries: 35 units in WH1 Rack D2
        sl_batt = StockLevel(product_id=prod_battery.id, warehouse_id=wh1.id, location_id=wh1_locations["Rack D2"].id, quantity=35, reserved_quantity=0)

        # WH2 and WH3 stock levels
        sl_wh2_glue = StockLevel(product_id=prod_glue.id, warehouse_id=wh2.id, location_id=wh2_loc.id, quantity=0, reserved_quantity=0)
        sl_wh2_rods = StockLevel(product_id=prod_rods.id, warehouse_id=wh2.id, location_id=wh2_loc.id, quantity=650, reserved_quantity=0)

        db.add_all([
            sl_glue, sl_med, sl_gloves, sl_rods, sl_chair, sl_bearing, sl_batt,
            batch_a, batch_b, batch_c, batch_glv1, batch_glv2,
            sl_wh2_glue, sl_wh2_rods
        ])
        db.flush()

        # 9. Stock Ledger entries (Create realistic movement history spanning 90 days)
        # Industrial glue: Movement happened 74 days ago! Zero movement since.
        db.add(StockLedger(
            timestamp=now - timedelta(days=74),
            product_id=prod_glue.id,
            warehouse_id=wh1.id,
            location_id=wh1_locations["Rack A1"].id,
            change_qty=-10,
            balance_after=850,
            transaction_type=TransactionType.DELIVERY,
            reference_type="DELIVERY",
            reference_id="DEL-HIST-901",
            notes="Factory workshop bulk dispatch"
        ))

        # Recent transactions for other products (Medicine, Rods, Chairs, Bearings)
        for d in range(1, 45, 3):
            # Steel rods delivery
            db.add(StockLedger(
                timestamp=now - timedelta(days=d),
                product_id=prod_rods.id,
                warehouse_id=wh1.id,
                location_id=wh1_locations["Rack C4"].id,
                change_qty=-random.randint(15, 30),
                balance_after=420 + (d * 5),
                transaction_type=TransactionType.DELIVERY,
                reference_type="DELIVERY",
                reference_id=f"DEL-AUTO-{d}"
            ))
            # Medicine A delivery
            db.add(StockLedger(
                timestamp=now - timedelta(days=d + 1),
                product_id=prod_med.id,
                warehouse_id=wh1.id,
                location_id=wh1_locations["Rack B2"].id,
                change_qty=-random.randint(2, 6),
                balance_after=170 + (d * 2),
                transaction_type=TransactionType.DELIVERY,
                reference_type="DELIVERY",
                reference_id=f"DEL-CLINIC-{d}"
            ))

        # Stock adjustments (Damages & count discrepancies for Cause-of-Loss analysis)
        adj1 = StockAdjustment(
            adjustment_number="ADJ-2026-001",
            warehouse_id=wh1.id,
            location_id=wh1_locations["Rack C4"].id,
            product_id=prod_rods.id,
            recorded_qty=423,
            counted_qty=420,
            variance_qty=-3,
            reason_type=AdjustmentReason.DAMAGE,
            notes="3 kg steel damaged during forklift transit",
            status=OperationStatus.DONE,
            approved_by_id=admin_user.id,
            created_at=now - timedelta(days=12)
        )
        adj2 = StockAdjustment(
            adjustment_number="ADJ-2026-002",
            warehouse_id=wh1.id,
            location_id=wh1_locations["Rack B2"].id,
            product_id=prod_med.id,
            recorded_qty=172,
            counted_qty=170,
            variance_qty=-2,
            reason_type=AdjustmentReason.EXPIRY,
            notes="Expired sample ampoules destroyed per protocol",
            status=OperationStatus.DONE,
            approved_by_id=admin_user.id,
            created_at=now - timedelta(days=20)
        )
        adj3 = StockAdjustment(
            adjustment_number="ADJ-2026-003",
            warehouse_id=wh1.id,
            location_id=wh1_locations["Rack A2"].id,
            product_id=prod_bearing.id,
            recorded_qty=16,
            counted_qty=15,
            variance_qty=-1,
            reason_type=AdjustmentReason.THEFT,
            notes="Missing bearing unit from unsealed carton",
            status=OperationStatus.DONE,
            approved_by_id=admin_user.id,
            created_at=now - timedelta(days=8)
        )
        db.add_all([adj1, adj2, adj3])

        # 10. Sample Completed Receipts (To back supplier metrics)
        rec1 = Receipt(
            receipt_number="REC-2026-101",
            supplier_id=sup_metals.id,
            warehouse_id=wh1.id,
            status=OperationStatus.DONE,
            order_date=now - timedelta(days=22),
            expected_date=now - timedelta(days=16),
            received_date=now - timedelta(days=16),
            notes="Bulk steel rods shipment"
        )
        db.add(rec1)
        db.flush()
        db.add(ReceiptItem(
            receipt_id=rec1.id, product_id=prod_rods.id, location_id=wh1_locations["Rack C4"].id,
            ordered_qty=200, received_qty=200, damaged_qty=2, unit_cost=65.0
        ))

        # 11. Sample Pending Delivery with multiple rack locations!
        # Matches exact prompt scenario:
        # Items across Rack A1, Rack C4, Rack B2, Rack A3, Rack D1
        deliv1024 = Delivery(
            delivery_number="DEL-1024",
            customer_name="Metro Infrastructure & Healthcare Ltd",
            warehouse_id=wh1.id,
            status=OperationStatus.READY,
            order_date=now - timedelta(hours=3),
            scheduled_date=now + timedelta(hours=4),
            notes="Urgent site replenishment order requiring optimized picking route"
        )
        db.add(deliv1024)
        db.flush()

        deliv_items = [
            DeliveryItem(delivery_id=deliv1024.id, product_id=prod_glue.id, location_id=wh1_locations["Rack A1"].id, requested_qty=10, unit_price=220.0),
            DeliveryItem(delivery_id=deliv1024.id, product_id=prod_gloves.id, location_id=wh1_locations["Rack A3"].id, batch_id=batch_glv1.id, requested_qty=20, unit_price=340.0),
            DeliveryItem(delivery_id=deliv1024.id, product_id=prod_med.id, location_id=wh1_locations["Rack B2"].id, batch_id=batch_a.id, requested_qty=15, unit_price=520.0),
            DeliveryItem(delivery_id=deliv1024.id, product_id=prod_rods.id, location_id=wh1_locations["Rack C4"].id, requested_qty=50, unit_price=85.0),
            DeliveryItem(delivery_id=deliv1024.id, product_id=prod_chair.id, location_id=wh1_locations["Rack D1"].id, requested_qty=4, unit_price=6500.0),
        ]
        db.add_all(deliv_items)
        db.commit()

        # Run initial Dead Stock analysis to populate tables
        DeadStockService.analyze_dead_stock(db)
        print("StockSense database successfully initialized with rich seed data!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
