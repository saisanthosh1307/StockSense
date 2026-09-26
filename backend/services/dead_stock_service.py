from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.inventory import Product, Warehouse, Location, StockLevel
from backend.models.ledger import StockLedger, TransactionType
from backend.models.intelligence import (
    DeadStockAnalysis, DeadStockClassification, DeadStockRecommendedAction, ImpactLevel
)
from backend.models.operations import InternalTransfer, OperationStatus
from backend.schemas.advanced import DeadStockRescueItem, DeadStockSummary, DeadStockActionConfirmRequest
from backend.services.impact_score_service import ImpactScoreService

class DeadStockService:
    @staticmethod
    def analyze_dead_stock(db: Session, warehouse_id: Optional[int] = None) -> DeadStockSummary:
        now = datetime.utcnow()
        # Query active stock levels
        query = db.query(StockLevel).join(Product).join(Warehouse)
        if warehouse_id:
            query = query.filter(StockLevel.warehouse_id == warehouse_id)
            
        stock_levels = query.all()
        
        items: List[DeadStockRescueItem] = []
        wh_map: Dict[str, Dict[str, Any]] = {}

        for sl in stock_levels:
            if sl.quantity <= 0:
                continue

            product = sl.product
            wh = sl.warehouse
            stock_val = round(sl.quantity * product.cost_price, 2)

            # Query last movement in stock ledger for this product in this warehouse
            last_ledger = db.query(StockLedger).filter(
                StockLedger.product_id == product.id,
                StockLedger.warehouse_id == wh.id
            ).order_by(StockLedger.timestamp.desc()).first()

            if last_ledger:
                last_move_date = last_ledger.timestamp
                days_inactive = max(0, (now - last_move_date).days)
            else:
                last_move_date = product.created_at
                days_inactive = max(30, (now - product.created_at).days)

            # Query outgoing movements in last 90 days to determine average monthly demand
            ninety_days_ago = now - timedelta(days=90)
            outgoing_txs = db.query(StockLedger).filter(
                StockLedger.product_id == product.id,
                StockLedger.warehouse_id == wh.id,
                StockLedger.change_qty < 0,
                StockLedger.timestamp >= ninety_days_ago
            ).all()

            total_consumed_90d = sum(abs(tx.change_qty) for tx in outgoing_txs)
            monthly_demand = round(total_consumed_90d / 3.0, 1)

            # Inventory age estimate
            first_ledger = db.query(StockLedger).filter(
                StockLedger.product_id == product.id,
                StockLedger.warehouse_id == wh.id
            ).order_by(StockLedger.timestamp.asc()).first()
            inventory_age = (now - first_ledger.timestamp).days if first_ledger else days_inactive

            # Dead Stock Scoring Algorithm (0 - 100)
            # Factors:
            # 1. Inactivity days score (60+ days = critical)
            inactivity_score = min(100.0, (days_inactive / 60.0) * 100.0)
            
            # 2. Stock-to-demand ratio (months of supply)
            months_of_supply = (sl.quantity / (monthly_demand if monthly_demand > 0 else 0.5))
            supply_score = min(100.0, (months_of_supply / 6.0) * 100.0)
            
            # 3. Capital lockup factor
            val_factor = min(100.0, (stock_val / 100000.0) * 100.0)

            dead_stock_score = round(
                (inactivity_score * 0.45) +
                (supply_score * 0.35) +
                (val_factor * 0.20),
                1
            )

            # Classification
            if days_inactive >= 60:
                classification = DeadStockClassification.DEAD_STOCK
            elif sl.quantity > (product.max_stock_level * 1.5) or months_of_supply > 6:
                classification = DeadStockClassification.EXCESS_STOCK
            elif days_inactive >= 30 or monthly_demand < 5:
                classification = DeadStockClassification.SLOW_MOVING
            else:
                classification = DeadStockClassification.NORMAL

            # Recommendations & Rationale
            recommended_action = None
            action_rationale = None
            target_wh_id = None
            target_wh_name = None

            if classification == DeadStockClassification.DEAD_STOCK:
                # Find another warehouse with higher demand for this product
                other_wh_demand = db.query(StockLedger.warehouse_id, func.count(StockLedger.id)).filter(
                    StockLedger.product_id == product.id,
                    StockLedger.warehouse_id != wh.id,
                    StockLedger.change_qty < 0
                ).group_by(StockLedger.warehouse_id).first()

                if other_wh_demand:
                    other_wh = db.query(Warehouse).filter(Warehouse.id == other_wh_demand[0]).first()
                    target_wh_id = other_wh.id
                    target_wh_name = other_wh.name
                    recommended_action = DeadStockRecommendedAction.REDISTRIBUTE_HIGH_DEMAND
                    action_rationale = (
                        f"Transfer to {target_wh_name} where sales velocity is active, avoiding total write-off."
                    )
                elif product.supplier:
                    recommended_action = DeadStockRecommendedAction.RETURN_TO_SUPPLIER
                    action_rationale = (
                        f"Zero movement for {days_inactive} days. Request vendor RMA return to {product.supplier.name}."
                    )
                else:
                    recommended_action = DeadStockRecommendedAction.PROMOTE_CLEAR
                    action_rationale = (
                        f"Liquidate or clearance discount to unlock ₹{stock_val:,.2f} in working capital."
                    )

            elif classification == DeadStockClassification.EXCESS_STOCK:
                recommended_action = DeadStockRecommendedAction.STOP_PURCHASING
                action_rationale = (
                    f"Current stock ({sl.quantity} {product.uom}) exceeds max threshold ({product.max_stock_level}). Freeze purchase orders."
                )
            elif classification == DeadStockClassification.SLOW_MOVING:
                recommended_action = DeadStockRecommendedAction.REDUCE_REORDER
                action_rationale = (
                    f"Consumption has slowed to {monthly_demand}/month. Lower reorder point to prevent excess."
                )

            # Impact Score Calculation (Feature 5 integration)
            impact_res = ImpactScoreService.calculate_impact_score(
                stockout_risk=0.0,
                financial_exposure=stock_val,
                demand_volatility=15.0 if monthly_demand == 0 else 50.0,
                lead_time_days=float(days_inactive),
                supplier_reliability_pct=85.0,
                context_type="DEAD_STOCK"
            )

            # Persist or update DeadStockAnalysis in DB
            analysis = db.query(DeadStockAnalysis).filter(
                DeadStockAnalysis.product_id == product.id,
                DeadStockAnalysis.warehouse_id == wh.id
            ).first()
            if not analysis:
                analysis = DeadStockAnalysis(
                    product_id=product.id,
                    warehouse_id=wh.id
                )
                db.add(analysis)

            analysis.current_stock = sl.quantity
            analysis.stock_value = stock_val
            analysis.days_inactive = days_inactive
            analysis.last_movement_date = last_move_date
            analysis.average_monthly_demand = monthly_demand
            analysis.inventory_age_days = inventory_age
            analysis.dead_stock_score = dead_stock_score
            analysis.classification = classification
            analysis.recommended_action = recommended_action
            analysis.action_rationale = action_rationale
            analysis.target_warehouse_id = target_wh_id
            analysis.updated_at = now
            db.flush()

            item_dto = DeadStockRescueItem(
                id=analysis.id,
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                warehouse_id=wh.id,
                warehouse_name=wh.name,
                current_stock=sl.quantity,
                stock_value=stock_val,
                days_inactive=days_inactive,
                last_movement_date=last_move_date,
                average_monthly_demand=monthly_demand,
                inventory_age_days=inventory_age,
                dead_stock_score=dead_stock_score,
                classification=classification,
                recommended_action=recommended_action,
                action_rationale=action_rationale,
                target_warehouse_id=target_wh_id,
                target_warehouse_name=target_wh_name,
                impact_score=impact_res.overall_score,
                impact_level=impact_res.impact_level,
                is_actioned=analysis.is_actioned
            )
            items.append(item_dto)

            # Warehouse breakdown accumulator
            if wh.name not in wh_map:
                wh_map[wh.name] = {
                    "warehouse_name": wh.name,
                    "warehouse_id": wh.id,
                    "dead_stock_value": 0.0,
                    "dead_stock_count": 0,
                    "excess_stock_count": 0,
                    "slow_moving_count": 0
                }
            if classification == DeadStockClassification.DEAD_STOCK:
                wh_map[wh.name]["dead_stock_value"] += stock_val
                wh_map[wh.name]["dead_stock_count"] += 1
            elif classification == DeadStockClassification.EXCESS_STOCK:
                wh_map[wh.name]["excess_stock_count"] += 1
            elif classification == DeadStockClassification.SLOW_MOVING:
                wh_map[wh.name]["slow_moving_count"] += 1

        db.commit()

        total_dead_val = sum(i.stock_value for i in items if i.classification == DeadStockClassification.DEAD_STOCK)
        dead_count = sum(1 for i in items if i.classification == DeadStockClassification.DEAD_STOCK)
        excess_val = sum(i.stock_value for i in items if i.classification == DeadStockClassification.EXCESS_STOCK)
        slow_count = sum(1 for i in items if i.classification == DeadStockClassification.SLOW_MOVING)

        return DeadStockSummary(
            total_dead_stock_value=round(total_dead_val, 2),
            total_dead_stock_products_count=dead_count,
            total_excess_stock_value=round(excess_val, 2),
            total_slow_moving_count=slow_count,
            warehouse_breakdown=list(wh_map.values()),
            items=sorted(items, key=lambda x: x.dead_stock_score, reverse=True)
        )

    @staticmethod
    def execute_confirmed_action(
        db: Session, req: DeadStockActionConfirmRequest, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        analysis = db.query(DeadStockAnalysis).filter(DeadStockAnalysis.id == req.analysis_id).first()
        if not analysis:
            raise ValueError("Dead stock analysis record not found")

        product = analysis.product
        current_wh = analysis.warehouse

        # Action: Transfer / Redistribution
        if req.action in [
            DeadStockRecommendedAction.TRANSFER,
            DeadStockRecommendedAction.REDISTRIBUTE_HIGH_DEMAND
        ]:
            target_wh_id = req.target_warehouse_id or analysis.target_warehouse_id
            if not target_wh_id:
                raise ValueError("Target warehouse must be specified for transfer")

            target_wh = db.query(Warehouse).filter(Warehouse.id == target_wh_id).first()
            if not target_wh:
                raise ValueError("Target warehouse not found")

            # Source location
            source_loc = db.query(Location).filter(
                Location.warehouse_id == current_wh.id,
                Location.is_active == True
            ).first()
            # Target location
            target_loc = db.query(Location).filter(
                Location.warehouse_id == target_wh.id,
                Location.is_active == True
            ).first()

            transfer_qty = req.quantity or analysis.current_stock
            transfer = InternalTransfer(
                transfer_number=f"TR-RESCUE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                product_id=product.id,
                from_warehouse_id=current_wh.id,
                to_warehouse_id=target_wh.id,
                from_location_id=source_loc.id,
                to_location_id=target_loc.id,
                quantity=transfer_qty,
                status=OperationStatus.DRAFT,
                notes=f"Dead-Stock Rescue transfer approved by user. {req.notes or ''}",
                created_by_id=user_id
            )
            db.add(transfer)
            analysis.is_actioned = True
            db.commit()
            return {
                "success": True,
                "message": f"Created Internal Transfer #{transfer.transfer_number} for {transfer_qty} units of {product.name}",
                "operation_type": "TRANSFER",
                "reference_id": transfer.transfer_number
            }

        elif req.action == DeadStockRecommendedAction.STOP_PURCHASING:
            product.reorder_point = 0
            analysis.is_actioned = True
            db.commit()
            return {
                "success": True,
                "message": f"Reorder point for {product.name} reset to 0 to prevent future purchase orders.",
                "operation_type": "POLICY_UPDATE"
            }

        elif req.action == DeadStockRecommendedAction.REDUCE_REORDER:
            product.reorder_point = max(5, int(product.reorder_point * 0.5))
            analysis.is_actioned = True
            db.commit()
            return {
                "success": True,
                "message": f"Reorder point for {product.name} reduced to {product.reorder_point}.",
                "operation_type": "POLICY_UPDATE"
            }

        elif req.action == DeadStockRecommendedAction.PROMOTE_CLEAR:
            analysis.is_actioned = True
            db.commit()
            return {
                "success": True,
                "message": f"Promotional clearance flagged for {product.name} ({analysis.current_stock} units).",
                "operation_type": "PROMOTION"
            }

        elif req.action == DeadStockRecommendedAction.RETURN_TO_SUPPLIER:
            analysis.is_actioned = True
            db.commit()
            return {
                "success": True,
                "message": f"Supplier return initiated for {product.name} to {product.supplier.name if product.supplier else 'Default Supplier'}.",
                "operation_type": "RMA_RETURN"
            }

        analysis.is_actioned = True
        db.commit()
        return {"success": True, "message": "Action confirmed successfully"}
