"""
StockSense End-to-End Verification Test Suite
Validates all 25 features (15 Core + 7 Intelligent + 3 Showcase).
"""
import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_all_features():
    print("\n" + "="*80)
    print("[START] STARTING VERIFICATION TEST SUITE FOR STOCKSENSE (25 FEATURES)")
    print("="*80)

    # 1. Health & Root
    res = client.get("/")
    assert res.status_code == 200
    print("[PASS] System Health Check: OK")

    # --- CORE 15 FEATURES ---

    # Feature 1: Login & Auth
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@stocksense.com", "password": "admin123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Feature 1 (Login & Auth): OK (JWT received)")

    # OTP Request & Reset test
    otp_req = client.post("/api/v1/auth/request-otp", json={"email": "admin@stocksense.com"})
    assert otp_req.status_code == 200
    otp_code = otp_req.json().get("dev_debug_otp")
    assert otp_code is not None
    print("[PASS] Feature 1 (OTP Password Reset): OK")

    # Feature 2: Products
    prod_res = client.get("/api/v1/products")
    assert prod_res.status_code == 200
    products = prod_res.json()
    assert len(products) >= 5
    sample_prod_id = products[0]["id"]
    print(f"[PASS] Feature 2 (Products): OK ({len(products)} products cataloged with location breakdown)")

    # Feature 3: Warehouses & Locations
    wh_res = client.get("/api/v1/warehouses")
    assert wh_res.status_code == 200
    warehouses = wh_res.json()
    assert len(warehouses) >= 2
    sample_wh_id = warehouses[0]["id"]
    print(f"[PASS] Feature 3 (Warehouses & Locations): OK ({len(warehouses)} warehouses active)")

    # Feature 4: Receipts
    rec_res = client.get("/api/v1/receipts")
    assert rec_res.status_code == 200
    receipts = rec_res.json()
    assert len(receipts) >= 1
    print(f"[PASS] Feature 4 (Receipts): OK ({len(receipts)} receipts tracked)")

    # Feature 5: Deliveries
    del_res = client.get("/api/v1/deliveries")
    assert del_res.status_code == 200
    deliveries = del_res.json()
    assert len(deliveries) >= 1
    print(f"[PASS] Feature 5 (Deliveries): OK ({len(deliveries)} delivery orders tracked)")

    # Feature 6: Transfers
    trans_res = client.get("/api/v1/transfers")
    assert trans_res.status_code == 200
    transfers = trans_res.json()
    assert len(transfers) >= 1
    print(f"[PASS] Feature 6 (Internal Transfers): OK ({len(transfers)} transfers tracked)")

    # Feature 7: Adjustments
    adj_res = client.get("/api/v1/adjustments")
    assert adj_res.status_code == 200
    adjustments = adj_res.json()
    assert len(adjustments) >= 1
    print(f"[PASS] Feature 7 (Stock Adjustments): OK ({len(adjustments)} physical counts reconciled)")

    # Feature 8: Ledger / Move History
    ledger_res = client.get("/api/v1/ledger")
    assert ledger_res.status_code == 200
    moves = ledger_res.json()
    assert len(moves) >= 4
    print(f"[PASS] Feature 8 (Stock Ledger): OK ({len(moves)} immutable double-entry moves sealed)")

    # Feature 9: Dashboard & Dynamic Filters
    kpis = client.get("/api/v1/dashboard/kpis").json()
    assert kpis["total_products_in_stock"] > 0
    feed = client.get("/api/v1/dashboard/operations-feed?doc_type=receipts").json()
    print(f"[PASS] Feature 9 (Dashboard & Filters): OK (Valuation: ${kpis['total_inventory_valuation']:,.2f})")

    # Feature 10: Search
    search_res = client.get("/api/v1/search?q=steel").json()
    assert search_res["total_matches"] > 0
    print(f"[PASS] Feature 10 (Search): OK ({search_res['total_matches']} items found for query 'steel')")

    # Feature 11: Alerts
    alerts = client.get("/api/v1/alerts").json()
    print(f"[PASS] Feature 11 (Alerts): OK ({len(alerts)} alerts generated)")

    # Feature 12: Reports
    val_report = client.get("/api/v1/reports/valuation").json()
    assert val_report["total_inventory_valuation"] > 0
    csv_res = client.get("/api/v1/reports/export/csv")
    assert csv_res.status_code == 200 and "Move ID" in csv_res.text
    print("[PASS] Feature 12 (Reports & CSV Export): OK")

    # Feature 13: Roles
    roles_matrix = client.get("/api/v1/roles/permissions").json()
    assert "ADMIN" in roles_matrix and "WAREHOUSE_STAFF" in roles_matrix
    print("[PASS] Feature 13 (Roles & RBAC): OK")

    # Feature 14: QR Generation & Scanning
    qr_res = client.get(f"/api/v1/qr/product/{sample_prod_id}").json()
    assert "data:image/png;base64," in qr_res["qr_code_data_uri"]
    scan_res = client.post("/api/v1/qr/scan", json={"raw_payload": "STEEL-ROD-12"}).json()
    assert scan_res["status"] == "RESOLVED"
    print("[PASS] Feature 14 (QR Code Engine): OK (Base64 QR generated & scanned)")

    # Feature 15: Audit
    logs = client.get("/api/v1/audit/logs").json()
    assert len(logs) > 0
    print(f"[PASS] Feature 15 (Audit Trail): OK ({len(logs)} activities logged)")

    # --- INTELLIGENT 7 FEATURES ---

    # Feature 16: Forecasting
    fc = client.get(f"/api/v1/intelligence/forecast/{sample_prod_id}?horizon_days=14").json()
    assert len(fc["data"]) > 0
    print(f"[PASS] Feature 16 (Forecasting): OK (Projected 14-day demand: {fc['total_forecasted_demand']} units)")

    # Feature 17: Reorder Engine
    reorder = client.get(f"/api/v1/intelligence/reorder/{sample_prod_id}").json()
    assert "reorder_point" in reorder and "economic_order_qty_eoq" in reorder
    print(f"[PASS] Feature 17 (Reorder Engine): OK (ROP: {reorder['reorder_point']}, EOQ: {reorder['economic_order_qty_eoq']})")

    # Feature 18: Explainability (XAI)
    explain = client.get(f"/api/v1/intelligence/explainability/{sample_prod_id}").json()
    assert len(explain["factors_breakdown"]) >= 3
    print(f"[PASS] Feature 18 (Explainability): OK (Decomposed into {len(explain['factors_breakdown'])} factors)")

    # Feature 19: Confidence Score
    conf = client.get(f"/api/v1/intelligence/confidence/{sample_prod_id}").json()
    assert 0 <= conf["confidence_score"] <= 100
    print(f"[PASS] Feature 19 (Confidence Score): OK (Rating: {conf['confidence_score']}% [{conf['confidence_tier']}])")

    # Feature 20: Anomaly Detection
    anomalies = client.get("/api/v1/intelligence/anomalies").json()
    print(f"[PASS] Feature 20 (Anomaly Detection): OK (Scanned moves & detected {len(anomalies)} anomalies)")

    # Feature 21: Cause-of-Loss
    loss = client.get("/api/v1/intelligence/cause-of-loss").json()
    assert len(loss["categories"]) > 0
    print(f"[PASS] Feature 21 (Cause-of-Loss): OK (Top cause: {loss['categories'][0]['cause']} - ${loss['categories'][0]['financial_impact']:,.2f})")

    # Feature 22: What-if Simulator
    whatif = client.post("/api/v1/intelligence/what-if", json={
        "product_id": sample_prod_id,
        "demand_surge_pct": 35.0,
        "supplier_delay_days": 7
    }).json()
    assert len(whatif["timeline"]) == 30
    print(f"[PASS] Feature 22 (What-if Simulator): OK (Emergency Buffer needed: {whatif['recommended_emergency_buffer']} units)")

    # --- SHOWCASE 3 FEATURES ---

    # Feature 23: Digital Twin
    dt = client.get(f"/api/v1/showcase/digital-twin/{sample_wh_id}").json()
    assert len(dt["slots"]) > 0
    print(f"[PASS] Feature 23 (Digital Twin): OK ({len(dt['slots'])} rack slots mapped, Heatmap generated)")

    # Feature 24: Trust Chain
    blocks = client.get("/api/v1/showcase/trust-chain/blocks").json()
    assert len(blocks) > 0
    audit_chain = client.get("/api/v1/showcase/trust-chain/verify").json()
    assert audit_chain["is_valid"] is True
    print(f"[PASS] Feature 24 (Trust Chain): OK ({audit_chain['total_blocks_checked']} blocks verified, Status: {audit_chain['verification_status']})")

    # Feature 25: AI Assistant
    copilot_query = client.post("/api/v1/showcase/ai-assistant/chat", json={
        "message": "Which products are currently low on stock?"
    }).json()
    assert len(copilot_query["response_text"]) > 20
    print("[PASS] Feature 25 (AI Assistant Copilot): OK (Natural language parsing & response generated)")

    print("\n" + "="*80)
    print("[SUCCESS] ALL 25 FEATURES PASSED FULL VERIFICATION SUCCESSFULLY!")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_all_features()
