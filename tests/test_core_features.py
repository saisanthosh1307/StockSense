import pytest

def test_auth_login(client):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"

def test_products_list(client):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 5
    sku_list = [p["sku"] for p in products]
    assert "SKU-GLUE-850" in sku_list
    assert "SKU-MED-A01" in sku_list

def test_categories_and_warehouses(client):
    resp_cat = client.get("/api/v1/categories")
    assert resp_cat.status_code == 200
    assert len(resp_cat.json()) >= 3

    resp_wh = client.get("/api/v1/warehouses")
    assert resp_wh.status_code == 200
    assert len(resp_wh.json()) >= 3

def test_receipt_creation_and_validation(client):
    # 1. Create Receipt for Steel Rods (product_id=3, warehouse_id=1, location_id=7 Rack C4)
    payload = {
        "supplier_id": 1,
        "warehouse_id": 1,
        "notes": "Incoming supplier delivery of steel rods",
        "items": [
            {
                "product_id": 3,
                "location_id": 7,
                "ordered_qty": 50,
                "received_qty": 50,
                "damaged_qty": 0,
                "unit_cost": 65.0
            }
        ]
    }
    create_resp = client.post("/api/v1/receipts", json=payload)
    assert create_resp.status_code == 200
    receipt_data = create_resp.json()
    rec_id = receipt_data["id"]

    # 2. Validate receipt -> Stock increases automatically
    val_resp = client.post(f"/api/v1/receipts/{rec_id}/validate")
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "DONE"

def test_delivery_order_flow(client):
    # Test pending delivery DEL-1024 exists
    deliv_resp = client.get("/api/v1/deliveries")
    assert deliv_resp.status_code == 200
    deliveries = deliv_resp.json()
    assert any(d["delivery_number"] == "DEL-1024" for d in deliveries)

def test_stock_ledger_and_trust_chain(client):
    # Verify ledger entries are present
    ledger_resp = client.get("/api/v1/ledger")
    assert ledger_resp.status_code == 200
    entries = ledger_resp.json()
    assert len(entries) > 0

    # Verify Cryptographic Trust Chain integrity
    trust_resp = client.get("/api/v1/trust-chain/verify")
    assert trust_resp.status_code == 200
    trust_data = trust_resp.json()
    assert trust_data["is_intact"] is True
    assert "verified" in trust_data["message"].lower() or "intact" in trust_data["message"].lower()

def test_search_and_alerts(client):
    # Search for "glue"
    search_resp = client.get("/api/v1/search?q=glue")
    assert search_resp.status_code == 200
    assert any("Glue" in item["name"] for item in search_resp.json())

    # Alerts check
    alerts_resp = client.get("/api/v1/alerts")
    assert alerts_resp.status_code == 200
    assert len(alerts_resp.json()) > 0
