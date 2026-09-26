import pytest

def test_demand_forecasting_with_impact(client):
    # Forecast for Steel Rods (product_id=3)
    resp = client.post("/api/v1/intelligence/forecast", json={"product_id": 3, "days_ahead": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == 3
    assert len(data["daily_forecasts"]) == 30
    assert 0 <= data["confidence_score"] <= 100
    assert 0 <= data["impact_score"] <= 100
    assert data["impact_level"] in ["Low", "Medium", "High", "Critical"]
    assert len(data["explainability"]) > 0

def test_dynamic_reorder_with_supplier_intelligence(client):
    resp = client.get("/api/v1/intelligence/reorder")
    assert resp.status_code == 200
    reorders = resp.json()
    assert len(reorders) > 0
    top = reorders[0]
    assert "recommended_order_qty" in top
    assert "impact_score" in top
    assert 0 <= top["impact_score"] <= 100
    assert len(top["impact_reasons"]) > 0
    assert "supplier_lead_time_days" in top
    assert "supplier_reliability_pct" in top

def test_anomaly_detection_and_cause_of_loss(client):
    # Anomalies
    anom_resp = client.get("/api/v1/intelligence/anomalies")
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()
    assert isinstance(anomalies, list)

    # Cause of loss
    col_resp = client.get("/api/v1/intelligence/cause-of-loss")
    assert col_resp.status_code == 200
    col_data = col_resp.json()
    assert len(col_data) > 0
    assert any("Damage" in item["reason"] for item in col_data)

def test_what_if_simulator(client):
    payload = {
        "product_id": 3,
        "demand_change_pct": 25.0,
        "lead_time_change_days": 5.0,
        "supplier_reliability_pct": 80.0
    }
    resp = client.post("/api/v1/intelligence/what-if", json=payload)
    assert resp.status_code == 200
    sim = resp.json()
    assert sim["simulated_stockout_risk_pct"] >= 0
    assert sim["simulated_safety_stock"] >= sim["baseline_safety_stock"]
    assert 0 <= sim["impact_score"] <= 100
    assert len(sim["insights"]) > 0
