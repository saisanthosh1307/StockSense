import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.inventory import Product, Warehouse, Location, StockLevel
from backend.models.supplier import Supplier, SupplierMetric
from backend.models.batch import InventoryBatch, BatchStatus
from backend.models.operations import Delivery, OperationStatus
from backend.models.intelligence import DeadStockAnalysis, DeadStockClassification, ImpactLevel
from backend.services.dead_stock_service import DeadStockService
from backend.services.fefo_service import FefoService
from backend.services.supplier_intelligence_service import SupplierIntelligenceService
from backend.services.picking_route_service import PickingRouteService
from backend.services.reorder_service import ReorderService

class AssistantService:
    @staticmethod
    def process_query(db: Session, query_text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        text = query_text.strip().lower()

        # 1. Dead stock queries
        if "dead stock" in text or "not moving" in text or "slow moving" in text:
            summary = DeadStockService.analyze_dead_stock(db)
            dead_items = [i for i in summary.items if i.classification == DeadStockClassification.DEAD_STOCK]
            
            if not dead_items:
                msg = f"No critical dead stock detected across warehouses. Total dead stock value is ₹0."
            else:
                top_3 = dead_items[:3]
                lines = [f"• **{i.product_name}** ({i.current_stock} units, ₹{i.stock_value:,.2f}) at *{i.warehouse_name}* — Inactive for {i.days_inactive} days. Recommended: {i.recommended_action.value if i.recommended_action else 'Review'}." for i in top_3]
                msg = (
                    f"Identified **{len(dead_items)} dead-stock products** totaling **₹{summary.total_dead_stock_value:,.2f}** in locked working capital:\n\n"
                    + "\n".join(lines) +
                    f"\n\n*Safety notice: Automated transfers or write-offs require your explicit confirmation on the Dead-Stock Rescue dashboard.*"
                )

            return {
                "query": query_text,
                "intent": "QUERY_DEAD_STOCK",
                "response": msg,
                "data": {"total_dead_stock_value": summary.total_dead_stock_value, "items_count": len(dead_items)},
                "action_required": False
            }

        # 2. Expiring stock queries
        elif "expir" in text or "fefo" in text or "batch" in text:
            alerts = FefoService.get_expiry_alerts(db, days_threshold=30)
            exp_soon = [b for b in alerts.batches if 0 <= b.days_to_expiry <= 30]
            
            lines = [f"• Batch **{b.batch_number}** ({b.product_name}): **{b.current_quantity} units** at *{b.warehouse_name} / {b.location_code}*, expires in **{b.days_to_expiry} days** (Val: ₹{b.total_value:,.2f})." for b in exp_soon[:4]]
            
            msg = (
                f"Found **{len(exp_soon)} batches expiring within 30 days** (₹{alerts.expiring_30_days_value:,.2f} valuation), "
                f"including **{alerts.expiring_7_days_count} critical batches** expiring within 7 days:\n\n"
                + "\n".join(lines) +
                "\n\nUnder FEFO policy, these batches are automatically prioritized for upcoming outgoing deliveries."
            )
            return {
                "query": query_text,
                "intent": "QUERY_EXPIRING_STOCK",
                "response": msg,
                "data": {"expiring_soon_count": len(exp_soon), "total_value": alerts.expiring_30_days_value},
                "action_required": False
            }

        # 3. Supplier reliability queries
        elif "supplier" in text and ("reliab" in text or "best" in text or "delivery" in text or "lead time" in text):
            comp = SupplierIntelligenceService.get_supplier_comparison(db)
            if not comp.suppliers:
                msg = "No supplier performance data available."
            else:
                top_s = comp.suppliers[0]
                lines = [
                    f"1. **{s.supplier_name}** — Reliability Score: **{s.reliability_score}%** | On-Time: {s.on_time_delivery_pct}% | Avg Lead Time: {s.average_lead_time_days}d | Damage Rate: {s.damage_rate_pct}%"
                    for s in comp.suppliers[:3]
                ]
                msg = (
                    f"Supplier Reliability ranking across our vendor network (Network average: **{comp.average_network_reliability}%**):\n\n"
                    + "\n".join(lines) +
                    f"\n\n**{top_s.supplier_name}** is currently ranked highest with exceptional delivery accuracy and low variance."
                )
            return {
                "query": query_text,
                "intent": "QUERY_SUPPLIER_RELIABILITY",
                "response": msg,
                "data": {"top_supplier": comp.suppliers[0].model_dump() if comp.suppliers else None},
                "action_required": False
            }

        # 4. Picking route creation query: e.g. "Create a picking route for delivery #1024"
        elif "picking route" in text or "pick route" in text or ("route" in text and "delivery" in text):
            match = re.search(r'(?:delivery\s*#?|#)(\d+)', text)
            delivery_id = None
            if match:
                delivery_id = int(match.group(1))
            else:
                # Pick first pending delivery
                first_del = db.query(Delivery).filter(Delivery.status != OperationStatus.DONE).first()
                if first_del:
                    delivery_id = first_del.id

            if not delivery_id:
                return {
                    "query": query_text,
                    "intent": "GENERATE_PICKING_ROUTE",
                    "response": "Could not locate an active delivery order. Please specify a delivery ID, e.g., 'Create picking route for delivery #1'.",
                    "action_required": False
                }

            deliv = db.query(Delivery).filter(Delivery.id == delivery_id).first()
            if not deliv:
                return {
                    "query": query_text,
                    "intent": "GENERATE_PICKING_ROUTE",
                    "response": f"Delivery #{delivery_id} not found in database.",
                    "action_required": False
                }

            route_resp = PickingRouteService.generate_route_for_delivery(db, delivery_id)
            step_summary = " → ".join([s.location_code for s in route_resp.steps])
            msg = (
                f"Generated optimized picking route for **Delivery #{deliv.delivery_number}** ({deliv.customer_name}):\n\n"
                f"**Path**: Start (Dock) → {step_summary} → Packing Station\n\n"
                f"• **Optimized Distance**: {route_resp.estimated_distance_meters} m (Original: {route_resp.original_distance_meters} m)\n"
                f"• **Estimated Time**: {route_resp.estimated_time_minutes} min (**Saved: {route_resp.time_saved_minutes} min**, +{route_resp.efficiency_gain_pct}% efficiency)\n\n"
                f"Visual path is now rendered on the **Digital Twin**. Please confirm each pick on the Smart Picking screen."
            )
            return {
                "query": query_text,
                "intent": "GENERATE_PICKING_ROUTE",
                "response": msg,
                "data": route_resp.model_dump(),
                "action_required": False
            }

        # 5. Impact score explanation query
        elif "impact score" in text or "impact" in text or "why does" in text:
            reorders = ReorderService.get_reorder_recommendations(db)
            if reorders:
                top_r = reorders[0]
                reasons_bullet = "\n".join([f"• {r}" for r in top_r.impact_reasons])
                msg = (
                    f"**Impact Score Explanation for {top_r.product_name} ({top_r.sku})**:\n\n"
                    f"• **Impact Score**: **{top_r.impact_score}/100** ({top_r.impact_level.value} Impact)\n"
                    f"• **Confidence**: {top_r.confidence_score}%\n"
                    f"• **Recommended Reorder**: {top_r.recommended_order_qty} units (Est. Cost: ₹{top_r.estimated_cost:,.2f})\n\n"
                    f"**Key Evaluated Factors**:\n{reasons_bullet}\n\n"
                    f"The score mathematically balances stockout risk ({top_r.current_stock} currently vs {top_r.reorder_point} safety threshold), "
                    f"financial exposure, and supplier reliability ({top_r.supplier_reliability_pct}%)."
                )
            else:
                msg = "Impact Scores range from 0–100, combining real stockout risk, financial exposure, demand variance, and supplier reliability into a unified decision priority."

            return {
                "query": query_text,
                "intent": "EXPLAIN_IMPACT_SCORE",
                "response": msg,
                "data": {"sample_item": reorders[0].model_dump() if reorders else None},
                "action_required": False
            }

        # 6. Excess inventory query: e.g. "Which warehouse has excess inventory?"
        elif "excess" in text or "which warehouse" in text or "surplus" in text:
            summary = DeadStockService.analyze_dead_stock(db)
            lines = []
            for wh in summary.warehouse_breakdown:
                lines.append(f"• **{wh['warehouse_name']}**: {wh['excess_stock_count']} excess items, {wh['dead_stock_count']} dead items (Dead stock value: ₹{wh['dead_stock_value']:,.2f})")
            
            msg = (
                f"Warehouse Inventory Health Breakdown:\n\n"
                + "\n".join(lines) +
                f"\n\nTotal excess inventory across network is valued at **₹{summary.total_excess_stock_value:,.2f}**."
            )
            return {
                "query": query_text,
                "intent": "QUERY_EXCESS_INVENTORY",
                "response": msg,
                "data": {"warehouse_breakdown": summary.warehouse_breakdown},
                "action_required": False
            }

        # General fallthrough
        else:
            total_prods = db.query(Product).count()
            total_wh = db.query(Warehouse).count()
            msg = (
                f"Hello! I am your **StockSense AI Assistant**. I can assist you with:\n\n"
                f"• Dead stock detection & redistribution recommendations\n"
                f"• Expiry dates and FEFO picking status\n"
                f"• Supplier reliability rankings & lead time analytics\n"
                f"• Smart picking route generation with Digital Twin visualization\n"
                f"• AI Impact Score explanations across forecasts & reorders\n\n"
                f"Currently tracking {total_prods} products across {total_wh} connected warehouses."
            )
            return {
                "query": query_text,
                "intent": "GENERAL_HELP",
                "response": msg,
                "data": {},
                "action_required": False
            }
