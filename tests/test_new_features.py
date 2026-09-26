import pytest

# --- 1. Dead-Stock Rescue Tests ---
def test_dead_stock_rescue_detection(client):
    resp = client.get("/api/v1/advanced/dead-stock")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_dead_stock_value"] >= 127000.0
    assert data["total_dead_stock_products_count"] >= 1
    
    # Verify Industrial Glue is detected as Dead Stock
    glue_item = next((i for i in data["items"] if "Industrial Glue" in i["product_name"]), None)
    assert glue_item is not None
    assert glue_item["classification"] == "Dead Stock"
    assert glue_item["days_inactive"] >= 60
    assert glue_item["current_stock"] == 850
    assert glue_item["stock_value"] == 127500.0
    assert glue_item["recommended_action"] is not None
    assert 0 <= glue_item["impact_score"] <= 100

def test_dead_stock_confirmation_requirement(client):
    # Action requires user confirmation
    resp = client.get("/api/v1/advanced/dead-stock")
    glue_item = next((i for i in resp.json()["items"] if "Industrial Glue" in i["product_name"]), None)
    analysis_id = glue_item["id"]

    confirm_payload = {
        "analysis_id": analysis_id,
        "action": "Transfer to another warehouse",
        "target_warehouse_id": 2,
        "quantity": 200,
        "notes": "Redistribute 200 units to North Depot"
    }
    action_resp = client.post("/api/v1/advanced/dead-stock/confirm-action", json=confirm_payload)
    assert action_resp.status_code == 200
    res = action_resp.json()
    assert res["success"] is True
    assert "TRANSFER" in res["operation_type"]


# --- 2. Supplier Intelligence Tests ---
def test_supplier_intelligence_metrics(client):
    resp = client.get("/api/v1/advanced/suppliers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suppliers"]) >= 3
    
    # Check ABC Metals
    abc = next((s for s in data["suppliers"] if s["supplier_name"] == "ABC Metals"), None)
    assert abc is not None
    assert abc["on_time_delivery_pct"] >= 90.0
    assert abc["average_lead_time_days"] == pytest.approx(6.2, 0.5)
    assert abc["quantity_accuracy_pct"] >= 95.0
    assert abc["damage_rate_pct"] <= 2.0
    assert abc["reliability_score"] >= 90.0


# --- 3. Expiry / FEFO Management Tests ---
def test_expiry_alerts_and_batches(client):
    resp = client.get("/api/v1/advanced/expiry/alerts?days_threshold=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["expiring_7_days_count"] >= 1  # Nitrile gloves expiring in 5 days
    assert data["expiring_30_days_count"] >= 1 # Medicine A batch A expiring in 12 days
    assert len(data["batches"]) >= 4

def test_fefo_picking_allocation_order(client):
    # Medicine A (product_id=2, WH=1). Order 40 units.
    # Should pick Batch A (20 units, expires in 12d) first, then Batch B (20 units from 50, expires in 60d) second.
    resp = client.get("/api/v1/advanced/fefo/plan?product_id=2&warehouse_id=1&requested_qty=40")
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["fulfilled_quantity"] == 40
    assert len(plan["picking_steps"]) == 2
    
    # Step 1 must be Batch A
    assert plan["picking_steps"][0]["batch_number"] == "BATCH-MED-A"
    assert plan["picking_steps"][0]["recommended_pick_qty"] == 20
    # Step 2 must be Batch B
    assert plan["picking_steps"][1]["batch_number"] == "BATCH-MED-B"
    assert plan["picking_steps"][1]["recommended_pick_qty"] == 20


# --- 4. Smart Picking Route Tests ---
def test_smart_picking_route_generation(client):
    # Delivery 1 (DEL-1024) contains items across Rack A1, A3, B2, C4, D1
    delivs = client.get("/api/v1/deliveries").json()
    deliv_id = delivs[0]["id"]

    resp = client.get(f"/api/v1/advanced/picking-route/{deliv_id}")
    assert resp.status_code == 200
    route = resp.json()
    assert route["total_locations"] >= 4
    assert route["estimated_distance_meters"] > 0
    assert route["estimated_time_minutes"] > 0
    assert len(route["steps"]) >= 4
    assert route["steps"][0]["is_confirmed"] is False

    # Test Step confirmation
    step_resp = client.post(
        f"/api/v1/advanced/picking-route/{deliv_id}/confirm-step",
        json={"step_order": 1, "picked_quantity": route["steps"][0]["pick_quantity"]}
    )
    assert step_resp.status_code == 200
    assert step_resp.json()["is_confirmed"] is True


# --- 5. Impact Score Tests ---
def test_impact_score_endpoint(client):
    resp = client.get("/api/v1/intelligence/impact?stockout_risk=85.0&financial_exposure=120000&lead_time_days=10&supplier_reliability_pct=80")
    assert resp.status_code == 200
    data = resp.json()
    assert 60.0 <= data["overall_score"] <= 100.0
    assert data["impact_level"] in ["High", "Critical"]
    assert len(data["reasons"]) >= 2


# --- 6. Digital Twin Integration Tests ---
def test_digital_twin_warehouse_layout_and_overlays(client):
    resp = client.get("/api/v1/digital-twin/warehouse/1")
    assert resp.status_code == 200
    dt = resp.json()
    assert "locations" in dt
    assert len(dt["locations"]) >= 9
    
    # Check that status_color includes dead_stock and expiring tags
    statuses = [loc["status_color"] for loc in dt["locations"]]
    assert "dead_stock" in statuses
    assert "expiring" in statuses


# --- 7. AI Assistant Integration Tests ---
def test_ai_assistant_responses(client):
    # Test Dead stock query
    r1 = client.post("/api/v1/assistant/chat", json={"message": "Show me dead stock."})
    assert r1.status_code == 200
    assert "dead-stock" in r1.json()["response"].lower() or "industrial glue" in r1.json()["response"].lower()

    # Test Expiry query
    r2 = client.post("/api/v1/assistant/chat", json={"message": "Which products are expiring this month?"})
    assert r2.status_code == 200
    assert "expir" in r2.json()["response"].lower()

    # Test Supplier query
    r3 = client.post("/api/v1/assistant/chat", json={"message": "Which supplier has the best delivery reliability?"})
    assert r3.status_code == 200
    assert "reliability" in r3.json()["response"].lower()

    # Test Picking route query
    r4 = client.post("/api/v1/assistant/chat", json={"message": "Create a picking route for delivery #1."})
    assert r4.status_code == 200
    assert "picking route" in r4.json()["response"].lower() or "distance" in r4.json()["response"].lower()

    # Test Impact score explanation query
    r5 = client.post("/api/v1/assistant/chat", json={"message": "Why does this reorder recommendation have a high impact score?"})
    assert r5.status_code == 200
    assert "impact score" in r5.json()["response"].lower()
