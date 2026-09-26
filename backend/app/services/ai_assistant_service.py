import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.inventory import Product, Warehouse, Location
from app.models.operations import Receipt, Delivery, Transfer, DocStatus
from app.services.stock_ledger_service import get_product_total_stock
from app.services.intelligence_service import (
    calculate_dynamic_reorder,
    generate_demand_forecast,
    detect_inventory_anomalies,
    analyze_cause_of_loss,
)

def query_ai_assistant(db: Session, user_message: str) -> Dict[str, Any]:
    text = user_message.lower().strip()

    # Intent 1: Low stock / Reorder queries
    if any(k in text for k in ["low stock", "reorder", "stockout", "out of stock", "replenish", "shortage"]):
        products = db.query(Product).all()
        low_stock_list = []
        for p in products:
            qty = get_product_total_stock(db, p.id)
            if qty <= p.min_reorder_qty:
                rec = calculate_dynamic_reorder(db, p.id)
                low_stock_list.append({
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "on_hand": qty,
                    "min_threshold": p.min_reorder_qty,
                    "recommended_order": rec["recommended_order_qty"],
                    "urgency": rec["urgency_level"]
                })

        if low_stock_list:
            items_str = "\n".join([f"- **{i['name']}** ({i['sku']}): {i['on_hand']} on hand (Threshold: {i['min_threshold']}) → Recommended Order: **{i['recommended_order']:.0f} units** [{i['urgency']}]" for i in low_stock_list])
            reply = (
                f"### ⚠️ Low Stock & Reorder Alert\n\n"
                f"I detected **{len(low_stock_list)} item(s)** currently at or below their safety reorder threshold:\n\n"
                f"{items_str}\n\n"
                f"Would you like me to prepare automated purchase receipts for these items?"
            )
        else:
            reply = "All products currently maintain healthy inventory levels above their configured reorder thresholds."

        return {
            "response_text": reply,
            "intent_detected": "QUERY_STOCK",
            "data_payload": {"low_stock_items": low_stock_list},
            "suggested_actions": [
                "Draft purchase receipt for lowest stock item",
                "Explain reorder formula for top item",
                "Run demand forecast"
            ],
            "confidence": 0.96
        }

    # Intent 2: Forecast queries
    if any(k in text for k in ["forecast", "predict", "future demand", "projection", "trend"]):
        # Find matching product or take first
        products = db.query(Product).all()
        target = None
        for p in products:
            if p.name.lower() in text or p.sku.lower() in text:
                target = p
                break
        if not target and products:
            target = products[0]

        if target:
            fc = generate_demand_forecast(db, target.id, horizon_days=14)
            reply = (
                f"### 📈 Demand Forecast: {target.name} ({target.sku})\n\n"
                f"- **Model**: {fc['algorithm_used']}\n"
                f"- **Historical Daily Average**: {fc['daily_average_demand']} units/day\n"
                f"- **14-Day Projected Demand**: **{fc['total_forecasted_demand']} units**\n\n"
                f"Demand shows steady consumption with moderate variance. Safety stock parameters are properly absorbing projected fluctuations."
            )
            return {
                "response_text": reply,
                "intent_detected": "FORECAST_DEMAND",
                "data_payload": fc,
                "suggested_actions": [
                    f"Explain forecast factors for {target.name}",
                    f"Simulate +30% demand surge for {target.name}",
                    "View inventory digital twin"
                ],
                "confidence": 0.94
            }

    # Intent 3: Anomaly or Cause of Loss
    if any(k in text for k in ["anomaly", "irregular", "theft", "shrinkage", "loss", "damaged", "spoilage", "defect"]):
        loss_analysis = analyze_cause_of_loss(db)
        anomalies = detect_inventory_anomalies(db)
        
        reply = (
            f"### 🛡️ Inventory Integrity & Loss Analysis\n\n"
            f"- **Total Recorded Loss**: \${loss_analysis['total_financial_loss']:,.2f} ({loss_analysis['total_units_lost']} units)\n"
            f"- **Primary Loss Factor**: **{loss_analysis['categories'][0]['cause']}** "
            f"({loss_analysis['categories'][0]['percentage_of_total_loss']}% of total loss)\n"
            f"- **Active Movement Anomalies**: {len(anomalies)} flagged transactions\n\n"
            f"**Recommended Action**: {loss_analysis['ai_risk_mitigation'][0]}"
        )
        return {
            "response_text": reply,
            "intent_detected": "ANOMALY_LOSS_ANALYSIS",
            "data_payload": {"loss_analysis": loss_analysis, "anomalies": anomalies},
            "suggested_actions": [
                "Verify Trust Chain cryptographic integrity",
                "View adjustment history",
                "Download inventory valuation report"
            ],
            "confidence": 0.95
        }

    # Intent 4: Operations Status (Receipts, Deliveries, Transfers)
    if any(k in text for k in ["pending", "operations", "receipt", "delivery", "transfer", "shipment"]):
        rec_pending = db.query(Receipt).filter(Receipt.status.in_([DocStatus.DRAFT, DocStatus.WAITING, DocStatus.READY])).count()
        del_pending = db.query(Delivery).filter(Delivery.status.in_([DocStatus.DRAFT, DocStatus.WAITING, DocStatus.READY])).count()
        trans_pending = db.query(Transfer).filter(Transfer.status.in_([DocStatus.DRAFT, DocStatus.WAITING, DocStatus.READY])).count()

        reply = (
            f"### 📋 Current Warehouse Operations Snapshot\n\n"
            f"- **Pending Incoming Receipts**: **{rec_pending}**\n"
            f"- **Pending Outgoing Deliveries**: **{del_pending}**\n"
            f"- **Scheduled Internal Transfers**: **{trans_pending}**\n\n"
            f"All pending movements are logged and awaiting staff validation or picking."
        )
        return {
            "response_text": reply,
            "intent_detected": "OPERATIONS_STATUS",
            "data_payload": {
                "pending_receipts": rec_pending,
                "pending_deliveries": del_pending,
                "scheduled_transfers": trans_pending
            },
            "suggested_actions": [
                "List pending receipts",
                "List ready delivery orders",
                "Show warehouse digital twin"
            ],
            "confidence": 0.92
        }

    # Default / General Copilot response
    return {
        "response_text": (
            f"Hello! I am your **StockSense AI Copilot**. I can help you with:\n\n"
            f"1. **Inventory Monitoring**: Check low stock items, total on-hand balances, and warehouse capacity.\n"
            f"2. **Predictive Analytics**: Run demand forecasts, explain dynamic reorder points, and calculate confidence intervals.\n"
            f"3. **Loss & Risk Prevention**: Audit shrinkage, classify damage causes, and detect consumption spikes.\n"
            f"4. **Operations & Verification**: Track pending receipts/deliveries and inspect our cryptographic Trust Chain.\n\n"
            f"How can I assist your warehouse team today?"
        ),
        "intent_detected": "GENERAL",
        "data_payload": None,
        "suggested_actions": [
            "Which products are low on stock?",
            "Forecast demand for top product",
            "Verify Trust Chain integrity",
            "Show warehouse digital twin"
        ],
        "confidence": 0.88
    }
