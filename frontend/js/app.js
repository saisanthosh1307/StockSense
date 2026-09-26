class StockSenseApp {
  constructor() {
    this.currentView = 'dashboard';
    this.digitalTwin = null;
    this.assistant = null;
    this.activeRouteDeliveryId = null;
  }

  async init() {
    this.setupNavigation();
    this.digitalTwin = new DigitalTwinVisualizer('digitalTwinCanvas');
    this.assistant = new AIAssistant();
    window.app = this;

    // Load initial view
    await this.switchView('dashboard');
  }

  setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const viewName = item.getAttribute('data-view');
        if (viewName) {
          this.switchView(viewName);
        }
      });
    });

    // Global Search Bar
    const searchInput = document.getElementById('globalSearchInput');
    searchInput?.addEventListener('keypress', async (e) => {
      if (e.key === 'Enter') {
        const q = searchInput.value.trim();
        if (q) {
          await this.performGlobalSearch(q);
        }
      }
    });

    // Dashboard Warehouse Filter
    document.getElementById('dashboardWhFilter')?.addEventListener('change', (e) => {
      this.loadDashboard(e.target.value);
    });

    // Operations Filters
    document.getElementById('docTypeFilter')?.addEventListener('change', () => this.filterOperations());
    document.getElementById('docStatusFilter')?.addEventListener('change', () => this.filterOperations());
  }

  async switchView(viewName) {
    this.currentView = viewName;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${viewName}"]`)?.classList.add('active');

    document.querySelectorAll('.page-view').forEach(el => el.classList.remove('active'));
    const targetPage = document.getElementById(`view-${viewName}`);
    if (targetPage) {
      targetPage.classList.add('active');
    }

    // View data loader
    switch (viewName) {
      case 'dashboard':
        await this.loadDashboard();
        break;
      case 'products':
        await this.loadProducts();
        break;
      case 'operations':
        await this.loadOperations();
        break;
      case 'ledger':
        await this.loadLedger();
        break;
      case 'dead-stock':
        await this.loadDeadStockView();
        break;
      case 'suppliers':
        await this.loadSuppliersView();
        break;
      case 'expiry-fefo':
        await this.loadExpiryFefoView();
        break;
      case 'smart-picking':
        await this.loadSmartPickingView();
        break;
      case 'forecast':
        await this.loadForecastView();
        break;
      case 'reorder':
        await this.loadReorderView();
        break;
      case 'anomalies':
        await this.loadAnomaliesView();
        break;
      case 'what-if':
        await this.loadWhatIfView();
        break;
      case 'digital-twin':
        await this.loadDigitalTwinView();
        break;
      case 'trust-chain':
        await this.loadTrustChainView();
        break;
    }
  }

  // --- 1. Dashboard View ---
  async loadDashboard(whId = '') {
    try {
      const summary = await api.getDashboardSummary(whId);
      const kpis = summary.kpis;

      // Existing KPIs
      document.getElementById('kpiTotalProducts').innerText = kpis.total_products;
      document.getElementById('kpiLowStock').innerText = `${kpis.low_stock_count} / ${kpis.out_of_stock_count}`;
      document.getElementById('kpiPendingReceipts').innerText = kpis.pending_receipts;
      document.getElementById('kpiPendingDeliveries').innerText = kpis.pending_deliveries;
      document.getElementById('kpiScheduledTransfers').innerText = kpis.scheduled_transfers;

      // 4 NEW REQUIRED SPEC KPIS:
      document.getElementById('kpiDeadStockValue').innerText = `₹${(kpis.dead_stock_value / 100000).toFixed(2)}L`;
      document.getElementById('kpiDeadStockSubtext').innerText = `${kpis.dead_stock_count} products holding idle capital`;

      document.getElementById('kpiExpiringStock').innerText = kpis.expiring_soon_count;
      document.getElementById('kpiExpiringSubtext').innerText = `Valued at ₹${(kpis.expiring_soon_value / 1000).toFixed(1)}k (FEFO alert)`;

      document.getElementById('kpiSupplierReliability').innerText = `${kpis.supplier_reliability_pct}%`;
      document.getElementById('kpiSupplierSubtext').innerText = `Across active vendor supply network`;

      document.getElementById('kpiHighestImpact').innerText = `${kpis.highest_impact_score}/100`;
      document.getElementById('kpiImpactSubtext').innerText = kpis.highest_impact_decision;

      // Recent Activity Feed
      const feedTbody = document.getElementById('recentActivityTbody');
      if (feedTbody) {
        feedTbody.innerHTML = summary.recent_activities.map(a => `
          <tr>
            <td><span class="badge ${a.change_qty > 0 ? 'badge-done' : 'badge-danger'}">${a.type}</span></td>
            <td><strong>${a.product_name}</strong></td>
            <td>${a.warehouse_name} (${a.location_code})</td>
            <td style="font-weight: 700; color: ${a.change_qty > 0 ? '#10b981' : '#ef4444'}">${a.change_qty > 0 ? `+${a.change_qty}` : a.change_qty}</td>
            <td>${a.balance_after}</td>
            <td><code>${a.reference}</code></td>
            <td style="color: var(--text-muted)">${a.timestamp}</td>
          </tr>
        `).join('');
      }
    } catch (err) {
      console.error("Dashboard load failed", err);
    }
  }

  // --- 2. Dead-Stock Rescue View (Feature 1) ---
  async loadDeadStockView() {
    try {
      const summary = await api.getDeadStock();
      document.getElementById('deadStockTotalVal').innerText = `₹${summary.total_dead_stock_value.toLocaleString('en-IN')}`;
      document.getElementById('deadStockCount').innerText = summary.total_dead_stock_products_count;
      document.getElementById('excessStockVal').innerText = `₹${summary.total_excess_stock_value.toLocaleString('en-IN')}`;

      // Table of Dead Stock Items
      const tbody = document.getElementById('deadStockTableTbody');
      tbody.innerHTML = summary.items.map(item => {
        let badgeClass = 'badge-done';
        if (item.classification === 'Dead Stock') badgeClass = 'badge-danger';
        else if (item.classification === 'Excess Stock') badgeClass = 'badge-waiting';
        else if (item.classification === 'Slow Moving') badgeClass = 'badge-ready';

        return `
          <tr>
            <td>
              <strong>${item.product_name}</strong>
              <div style="font-size: 0.75rem; color: var(--text-muted)">${item.sku}</div>
            </td>
            <td>${item.warehouse_name}</td>
            <td><strong>${item.current_stock}</strong></td>
            <td>₹${item.stock_value.toLocaleString('en-IN')}</td>
            <td><span style="color: ${item.days_inactive >= 60 ? '#ef4444' : '#f59e0b'}; font-weight: bold">${item.days_inactive} days</span></td>
            <td>${item.average_monthly_demand} / mo</td>
            <td><span class="badge ${badgeClass}">${item.classification}</span></td>
            <td>
              <span class="impact-badge impact-${item.impact_level.toLowerCase()}">
                ${item.impact_score}/100 (${item.impact_level})
              </span>
            </td>
            <td>
              <div style="font-size: 0.82rem; margin-bottom: 6px;">${item.recommended_action || 'Review stock'}</div>
              <button class="btn btn-sm btn-primary" onclick="app.openDeadStockModal(${item.id}, '${item.product_name.replace(/'/g, "\\'")}', '${item.recommended_action}', ${item.target_warehouse_id || 'null'}, ${item.current_stock})">
                Rescue Action
              </button>
            </td>
          </tr>
        `;
      }).join('');

      // Warehouse Breakdown Cards
      const whBreakdownContainer = document.getElementById('deadStockWhCards');
      if (whBreakdownContainer) {
        whBreakdownContainer.innerHTML = summary.warehouse_breakdown.map(wb => `
          <div class="kpi-card highlight-danger">
            <div class="kpi-title">${wb.warehouse_name}</div>
            <div class="kpi-value">₹${(wb.dead_stock_value / 1000).toFixed(1)}k</div>
            <div class="kpi-subtext">${wb.dead_stock_count} dead SKUs | ${wb.excess_stock_count} excess SKUs</div>
          </div>
        `).join('');
      }
    } catch (err) {
      console.error("Dead Stock load error", err);
    }
  }

  openDeadStockModal(analysisId, productName, recommendedAction, targetWhId, stockQty) {
    document.getElementById('rescueModalAnalysisId').value = analysisId;
    document.getElementById('rescueModalTitle').innerText = `Rescue Action: ${productName}`;
    document.getElementById('rescueActionSelect').value = recommendedAction;
    document.getElementById('rescueQtyInput').value = stockQty;
    document.getElementById('deadStockConfirmModal').classList.add('active');
  }

  closeDeadStockModal() {
    document.getElementById('deadStockConfirmModal').classList.remove('active');
  }

  async confirmDeadStockRescueAction() {
    const analysisId = parseInt(document.getElementById('rescueModalAnalysisId').value);
    const action = document.getElementById('rescueActionSelect').value;
    const targetWhId = parseInt(document.getElementById('rescueWhSelect').value);
    const qty = parseInt(document.getElementById('rescueQtyInput').value);
    const notes = document.getElementById('rescueNotesInput').value;

    try {
      const res = await api.confirmDeadStockAction({
        analysis_id: analysisId,
        action: action,
        target_warehouse_id: targetWhId,
        quantity: qty,
        notes: notes
      });
      alert(res.message);
      this.closeDeadStockModal();
      await this.loadDeadStockView();
    } catch (err) {
      alert(`Error executing action: ${err.message}`);
    }
  }

  // --- 3. Supplier Intelligence View (Feature 2) ---
  async loadSuppliersView() {
    try {
      const data = await api.getSuppliersComparison();
      document.getElementById('suppNetworkReliability').innerText = `${data.average_network_reliability}%`;
      document.getElementById('suppNetworkLeadTime').innerText = `${data.average_network_lead_time} days`;
      document.getElementById('suppNetworkAccuracy').innerText = `${data.average_network_accuracy}%`;
      document.getElementById('suppNetworkDamage').innerText = `${data.average_network_damage_rate}%`;

      const tbody = document.getElementById('suppliersTableTbody');
      tbody.innerHTML = data.suppliers.map(s => {
        let trendBadge = s.historical_trend === 'IMPROVING' ? 'badge-done' : (s.historical_trend === 'DECLINING' ? 'badge-danger' : 'badge-waiting');
        return `
          <tr>
            <td>
              <strong>${s.supplier_name}</strong>
              <div style="font-size: 0.75rem; color: var(--text-muted)">${s.supplier_code}</div>
            </td>
            <td>
              <span style="font-weight: 800; font-size: 1.05rem; color: ${s.reliability_score >= 90 ? '#10b981' : (s.reliability_score >= 80 ? '#f59e0b' : '#ef4444')}">
                ${s.reliability_score}%
              </span>
            </td>
            <td>${s.on_time_delivery_pct}%</td>
            <td>${s.average_lead_time_days} days <span style="font-size: 0.75rem; color: var(--text-muted)">(Exp: ${s.expected_avg_lead_time_days}d)</span></td>
            <td>${s.quantity_accuracy_pct}%</td>
            <td>${s.damage_rate_pct}%</td>
            <td>${s.total_orders} (${s.purchase_frequency_monthly}/mo)</td>
            <td><span class="badge ${trendBadge}">${s.historical_trend}</span></td>
            <td style="font-size: 0.8rem; color: var(--text-muted)">${s.performance_summary}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error("Supplier intelligence load error", err);
    }
  }

  // --- 4. Expiry / FEFO Management View (Feature 3) ---
  async loadExpiryFefoView() {
    try {
      const alerts = await api.getExpiryAlerts(30);
      document.getElementById('fefoExpiredCount').innerText = alerts.expired_count;
      document.getElementById('fefoCritCount').innerText = alerts.expiring_7_days_count;
      document.getElementById('fefoCritVal').innerText = `₹${alerts.expiring_7_days_value.toLocaleString('en-IN')}`;
      document.getElementById('fefoSoonCount').innerText = alerts.expiring_30_days_count;

      const tbody = document.getElementById('batchesTableTbody');
      tbody.innerHTML = alerts.batches.map(b => {
        let badge = 'badge-done';
        let statusText = `${b.days_to_expiry} days left`;
        if (b.is_expired) {
          badge = 'badge-danger';
          statusText = 'EXPIRED';
        } else if (b.is_critical) {
          badge = 'badge-danger';
          statusText = `CRITICAL (${b.days_to_expiry}d)`;
        } else if (b.is_expiring_soon) {
          badge = 'badge-waiting';
          statusText = `Expiring Soon (${b.days_to_expiry}d)`;
        }

        return `
          <tr>
            <td><code>${b.batch_number}</code></td>
            <td><strong>${b.product_name}</strong></td>
            <td>${b.warehouse_name} / <code>${b.location_code}</code></td>
            <td>${b.current_quantity} (Avail: ${b.available_quantity})</td>
            <td>${b.expiry_date.substring(0, 10)}</td>
            <td><span class="badge ${badge}">${statusText}</span></td>
            <td>₹${b.total_value.toLocaleString('en-IN')}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error("Expiry/FEFO view load error", err);
    }
  }

  async runFefoSimulation() {
    const prodId = document.getElementById('fefoSimProductSelect').value;
    const whId = document.getElementById('fefoSimWhSelect').value;
    const qty = parseInt(document.getElementById('fefoSimQtyInput').value);

    try {
      const plan = await api.getFefoPlan(prodId, whId, qty);
      const resContainer = document.getElementById('fefoSimulationResults');
      resContainer.style.display = 'block';

      document.getElementById('fefoPlanExplanation').innerText = plan.fefo_explanation;
      const stepsTbody = document.getElementById('fefoStepsTbody');
      stepsTbody.innerHTML = plan.picking_steps.map(s => `
        <tr>
          <td><strong>Step ${s.step_number}</strong></td>
          <td><code>${s.batch_number}</code></td>
          <td><code>${s.location_code}</code></td>
          <td>${s.expiry_date.substring(0, 10)} (${s.days_to_expiry}d remaining)</td>
          <td>${s.available_in_batch}</td>
          <td><strong style="color: var(--success); font-size: 1.05rem;">Pick ${s.recommended_pick_qty}</strong></td>
        </tr>
      `).join('');
    } catch (err) {
      alert(`FEFO Planning error: ${err.message}`);
    }
  }

  // --- 5. Smart Picking Route View (Feature 4) ---
  async loadSmartPickingView() {
    try {
      const deliveries = await api.getDeliveries();
      const select = document.getElementById('pickingDeliverySelect');
      select.innerHTML = deliveries.map(d => `
        <option value="${d.id}">${d.delivery_number} — ${d.customer_name} (${d.items.length} items, Status: ${d.status})</option>
      `).join('');

      if (deliveries.length > 0) {
        await this.loadPickingRouteView(deliveries[0].id);
      }
    } catch (err) {
      console.error("Smart picking load error", err);
    }
  }

  async loadPickingRouteView(deliveryId) {
    this.activeRouteDeliveryId = deliveryId;
    try {
      const route = await api.getPickingRoute(deliveryId);

      document.getElementById('routeTotalLocs').innerText = route.total_locations;
      document.getElementById('routeDistance').innerText = `${route.estimated_distance_meters} m`;
      document.getElementById('routeOrigDist').innerText = `Original: ${route.original_distance_meters} m`;
      document.getElementById('routeTime').innerText = `${route.estimated_time_minutes} min`;
      document.getElementById('routeTimeSaved').innerText = `Saved: ${route.time_saved_minutes} min (+${route.efficiency_gain_pct}%)`;

      // Visual sequence flow boxes
      const seqBox = document.getElementById('routeSequenceFlow');
      seqBox.innerHTML = `
        <div class="route-step-node"><strong>Start</strong><br><small>Inbound Dock</small></div>
        <div class="route-step-arrow">→</div>
      ` + route.steps.map(s => `
        <div class="route-step-node ${s.is_confirmed ? 'completed' : ''}">
          <strong>${s.location_code}</strong><br>
          <small>${s.product_name}</small><br>
          <span style="color: var(--primary); font-weight: bold;">Qty: ${s.pick_quantity}</span>
        </div>
        <div class="route-step-arrow">→</div>
      `).join('') + `
        <div class="route-step-node"><strong>Packing Area</strong><br><small>Station 1</small></div>
      `;

      // Step-by-step confirmation table
      const tbody = document.getElementById('routeStepsTbody');
      tbody.innerHTML = route.steps.map(s => `
        <tr style="${s.is_confirmed ? 'opacity: 0.6; background: rgba(16, 185, 129, 0.05);' : ''}">
          <td><strong>#${s.step_order}</strong></td>
          <td><code style="font-size: 0.95rem;">${s.location_code}</code></td>
          <td>(X: ${s.x_coord}m, Y: ${s.y_coord}m)</td>
          <td><strong>${s.product_name}</strong> (${s.product_sku})</td>
          <td>${s.batch_number ? `<code>${s.batch_number}</code>` : 'Standard'}</td>
          <td><strong>${s.pick_quantity}</strong></td>
          <td>
            ${s.is_confirmed 
              ? '<span class="badge badge-done">✓ Confirmed</span>' 
              : `<button class="btn btn-sm btn-success" onclick="app.confirmPickStep(${s.step_order}, ${s.pick_quantity})">Confirm Pick</button>`
            }
          </td>
        </tr>
      `).join('');

      // Also render onto Digital Twin Canvas!
      const twinData = await api.getDigitalTwin(route.warehouse_id, route.route_id);
      this.digitalTwin.setData(twinData);

    } catch (err) {
      console.error("Picking route generation error", err);
    }
  }

  async confirmPickStep(stepOrder, qty) {
    if (!this.activeRouteDeliveryId) return;
    try {
      const res = await api.confirmRoutePickStep(this.activeRouteDeliveryId, {
        step_order: stepOrder,
        picked_quantity: qty
      });
      await this.loadPickingRouteView(this.activeRouteDeliveryId);
      if (res.all_steps_completed) {
        alert("🎉 All picking steps confirmed! Delivery is now READY for Packing & Dispatch.");
      }
    } catch (err) {
      alert(`Pick confirmation error: ${err.message}`);
    }
  }

  // --- 6. AI Intelligence Views (Impact Score Integration) ---
  async loadForecastView() {
    try {
      const forecast = await api.getForecast(3, 30);
      document.getElementById('forecastMonthlyDemand').innerText = `${forecast.projected_monthly_demand} Units`;
      document.getElementById('forecastConfidence').innerText = `${forecast.confidence_score}%`;
      document.getElementById('forecastImpactScore').innerText = `${forecast.impact_score}/100`;
      document.getElementById('forecastImpactBadge').className = `impact-badge impact-${forecast.impact_level.toLowerCase()}`;
      document.getElementById('forecastImpactBadge').innerText = `${forecast.impact_level} Impact`;

      const explainContainer = document.getElementById('forecastExplainability');
      explainContainer.innerHTML = forecast.explainability.map(e => `<li>${e}</li>`).join('');

      const pointsTbody = document.getElementById('forecastPointsTbody');
      pointsTbody.innerHTML = forecast.daily_forecasts.slice(0, 15).map(p => `
        <tr>
          <td>${p.date}</td>
          <td><strong>${p.projected_demand}</strong></td>
          <td>${p.confidence_lower}</td>
          <td>${p.confidence_upper}</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error("Forecast load error", err);
    }
  }

  async loadReorderView() {
    try {
      const reorders = await api.getReorderRecommendations();
      const tbody = document.getElementById('reorderTableTbody');
      tbody.innerHTML = reorders.map(r => `
        <tr>
          <td>
            <strong>${r.product_name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted)">${r.sku}</div>
          </td>
          <td>${r.current_stock} / <small>Min: ${r.min_stock_level}</small></td>
          <td>${r.reorder_point}</td>
          <td><strong style="color: var(--primary); font-size: 1.05rem;">${r.recommended_order_qty}</strong></td>
          <td>₹${r.estimated_cost.toLocaleString('en-IN')}</td>
          <td>
            ${r.supplier_name}<br>
            <small style="color: var(--text-muted)">Lead: ${r.supplier_lead_time_days}d | Rel: ${r.supplier_reliability_pct}%</small>
          </td>
          <td><span class="badge ${r.urgency === 'CRITICAL' ? 'badge-danger' : (r.urgency === 'HIGH' ? 'badge-waiting' : 'badge-ready')}">${r.urgency}</span></td>
          <td>
            <span class="impact-badge impact-${r.impact_level.toLowerCase()}">
              ${r.impact_score}/100 (${r.impact_level})
            </span>
            <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 4px;">
              ${r.impact_reasons[0] || ''}
            </div>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      console.error("Reorder load error", err);
    }
  }

  async loadAnomaliesView() {
    try {
      const anomalies = await api.getAnomalies();
      const tbody = document.getElementById('anomaliesTableTbody');
      tbody.innerHTML = anomalies.map(a => `
        <tr>
          <td><span class="badge badge-danger">${a.anomaly_type}</span></td>
          <td><strong>${a.product_name}</strong> (${a.sku})</td>
          <td>${a.warehouse_name}</td>
          <td><strong>${a.detected_value}</strong> (Expected: ${a.expected_value})</td>
          <td>Z = ${a.z_score}</td>
          <td>
            <span class="impact-badge impact-${a.impact_level.toLowerCase()}">
              ${a.impact_score}/100 (${a.impact_level})
            </span>
          </td>
          <td>${a.explanation}</td>
          <td><em>${a.recommended_action}</em></td>
        </tr>
      `).join('');

      // Cause of Loss
      const colData = await api.getCauseOfLoss();
      const colTbody = document.getElementById('causeOfLossTbody');
      colTbody.innerHTML = colData.map(c => `
        <tr>
          <td><strong>${c.reason}</strong></td>
          <td>${c.total_quantity_lost}</td>
          <td>₹${c.total_value_lost.toLocaleString('en-IN')}</td>
          <td>${c.percentage_of_total_loss}%</td>
          <td>${c.top_affected_product}</td>
          <td>
            <span class="impact-badge impact-medium">${c.impact_score}/100</span>
          </td>
          <td>${c.mitigation_strategy}</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error("Anomalies load error", err);
    }
  }

  async loadWhatIfView() {
    // Initial calculation for product 3
    await this.triggerWhatIfSimulation();
  }

  async triggerWhatIfSimulation() {
    const demandChange = parseFloat(document.getElementById('simDemandSlider').value);
    const leadTimeChange = parseFloat(document.getElementById('simLeadTimeSlider').value);
    const suppReliability = parseFloat(document.getElementById('simReliabilitySlider').value);

    document.getElementById('simDemandVal').innerText = `${demandChange > 0 ? `+${demandChange}` : demandChange}%`;
    document.getElementById('simLeadTimeVal').innerText = `${leadTimeChange > 0 ? `+${leadTimeChange}` : leadTimeChange} days`;
    document.getElementById('simReliabilityVal').innerText = `${suppReliability}%`;

    try {
      const res = await api.runWhatIf({
        product_id: 3,
        demand_change_pct: demandChange,
        lead_time_change_days: leadTimeChange,
        supplier_reliability_pct: suppReliability
      });

      document.getElementById('simStockoutRisk').innerText = `${res.simulated_stockout_risk_pct}% (Base: ${res.baseline_stockout_risk_pct}%)`;
      document.getElementById('simSafetyStock').innerText = `${res.simulated_safety_stock} (Base: ${res.baseline_safety_stock})`;
      document.getElementById('simReorderQty').innerText = `${res.simulated_reorder_qty} (Base: ${res.baseline_reorder_qty})`;
      document.getElementById('simFinDiff').innerText = `₹${res.financial_impact_difference.toLocaleString('en-IN')}`;
      
      document.getElementById('simImpactScore').innerText = `${res.impact_score}/100`;
      document.getElementById('simImpactBadge').className = `impact-badge impact-${res.impact_level.toLowerCase()}`;
      document.getElementById('simImpactBadge').innerText = `${res.impact_level} Impact`;

      document.getElementById('simInsightsList').innerHTML = res.insights.map(i => `<li>${i}</li>`).join('');
    } catch (err) {
      console.error("What if simulation error", err);
    }
  }

  // --- 7. Digital Twin View ---
  async loadDigitalTwinView() {
    const whId = document.getElementById('twinWhSelect')?.value || 1;
    try {
      const twinData = await api.getDigitalTwin(whId);
      this.digitalTwin.setData(twinData);

      document.getElementById('twinTotalRacks').innerText = twinData.summary.total_locations;
      document.getElementById('twinDeadStockRacks').innerText = twinData.summary.dead_stock_locations_count;
      document.getElementById('twinExpiringRacks').innerText = twinData.summary.expiring_locations_count;
      document.getElementById('twinHighOccRacks').innerText = twinData.summary.high_occupancy_locations_count;
    } catch (err) {
      console.error("Digital twin load error", err);
    }
  }

  // --- 8. Cryptographic Trust Chain View ---
  async loadTrustChainView() {
    try {
      const res = await api.verifyTrustChain();
      document.getElementById('trustChainStatus').innerText = res.is_intact ? 'VERIFIED INTACT (100% Tamper-Proof)' : 'TAMPERING DETECTED';
      document.getElementById('trustChainStatus').style.color = res.is_intact ? '#10b981' : '#ef4444';
      document.getElementById('trustChainCheckedBlocks').innerText = res.total_blocks_checked;

      const blocks = await api.getTrustChainBlocks();
      const listEl = document.getElementById('trustChainBlocksList');
      listEl.innerHTML = blocks.map(b => `
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: var(--primary);">Block #${b.block_index}</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${b.timestamp}</span>
          </div>
          <div style="font-family: monospace; font-size: 0.78rem; word-break: break-all; margin-bottom: 4px;">
            <strong>Block Hash:</strong> <span style="color: #60a5fa">${b.block_hash}</span>
          </div>
          <div style="font-family: monospace; font-size: 0.78rem; word-break: break-all; margin-bottom: 4px; color: var(--text-muted)">
            <strong>Prev Hash:</strong> ${b.previous_hash}
          </div>
          <div style="font-family: monospace; font-size: 0.78rem; word-break: break-all; color: var(--text-muted)">
            <strong>Merkle Root:</strong> ${b.merkle_root}
          </div>
          <div style="margin-top: 8px; font-size: 0.82rem; background: rgba(0,0,0,0.2); padding: 6px 10px; border-radius: 4px;">
            ${b.payload_summary}
          </div>
        </div>
      `).join('');
    } catch (err) {
      console.error("Trust chain load error", err);
    }
  }

  // --- 9. Products & Operations Views ---
  async loadProducts() {
    try {
      const products = await api.getProducts();
      const tbody = document.getElementById('productsTableTbody');
      tbody.innerHTML = products.map(p => `
        <tr>
          <td><strong>${p.name}</strong></td>
          <td><code>${p.sku}</code></td>
          <td><code>${p.barcode || 'N/A'}</code></td>
          <td>${p.category_name || 'General'}</td>
          <td><strong>${p.total_stock}</strong> ${p.uom}</td>
          <td>₹${p.cost_price.toFixed(2)}</td>
          <td>₹${p.selling_price.toFixed(2)}</td>
          <td>₹${p.inventory_value.toLocaleString('en-IN')}</td>
          <td>${p.is_perishable ? '<span class="badge badge-waiting">Perishable</span>' : '<span class="badge badge-draft">Standard</span>'}</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error("Products load error", err);
    }
  }

  async loadOperations() {
    await this.filterOperations();
  }

  async filterOperations() {
    const docType = document.getElementById('docTypeFilter')?.value || 'receipts';
    const status = document.getElementById('docStatusFilter')?.value || '';

    const tbody = document.getElementById('operationsTableTbody');
    const headerEl = document.getElementById('operationsTableHeader');

    if (docType === 'receipts') {
      headerEl.innerText = "Receipts (Incoming Goods from Vendors)";
      const data = await api.getReceipts(status ? `?status=${status}` : '');
      tbody.innerHTML = data.map(r => `
        <tr>
          <td><strong>${r.receipt_number}</strong></td>
          <td>${r.supplier_name}</td>
          <td>${r.warehouse_name}</td>
          <td>${r.items.length} items</td>
          <td>${r.order_date.substring(0, 10)}</td>
          <td><span class="badge badge-${r.status.toLowerCase()}">${r.status}</span></td>
          <td>
            ${r.status !== 'DONE' ? `<button class="btn btn-sm btn-success" onclick="app.validateReceipt(${r.id})">Validate Receipt</button>` : 'Validated'}
          </td>
        </tr>
      `).join('');
    } else if (docType === 'deliveries') {
      headerEl.innerText = "Delivery Orders (Outgoing Goods to Customers)";
      const data = await api.getDeliveries(status ? `?status=${status}` : '');
      tbody.innerHTML = data.map(d => `
        <tr>
          <td><strong>${d.delivery_number}</strong></td>
          <td>${d.customer_name}</td>
          <td>${d.warehouse_name}</td>
          <td>${d.items.length} items</td>
          <td>${d.order_date.substring(0, 10)}</td>
          <td><span class="badge badge-${d.status.toLowerCase()}">${d.status}</span></td>
          <td>
            ${d.status !== 'DONE' ? `
              <button class="btn btn-sm btn-primary" onclick="app.openPickingRouteForDelivery(${d.id})">Pick Route</button>
              <button class="btn btn-sm btn-success" onclick="app.validateDelivery(${d.id})">Validate Delivery</button>
            ` : 'Validated'}
          </td>
        </tr>
      `).join('');
    }
  }

  async validateReceipt(id) {
    try {
      await api.validateReceipt(id);
      alert("Receipt validated! Stock automatically updated, ledger logged, and supplier metrics recalculated.");
      await this.filterOperations();
    } catch (err) {
      alert(`Receipt validation error: ${err.message}`);
    }
  }

  async validateDelivery(id) {
    try {
      await api.validateDelivery(id);
      alert("Delivery validated! Stock automatically decreased, batch quantities updated, and ledger logged.");
      await this.filterOperations();
    } catch (err) {
      alert(`Delivery validation error: ${err.message}`);
    }
  }

  openPickingRouteForDelivery(deliveryId) {
    this.switchView('smart-picking');
    document.getElementById('pickingDeliverySelect').value = deliveryId;
    this.loadPickingRouteView(deliveryId);
  }

  async loadLedger() {
    try {
      const entries = await api.getLedger();
      const tbody = document.getElementById('ledgerTableTbody');
      tbody.innerHTML = entries.map(e => `
        <tr>
          <td><span style="font-size: 0.75rem; color: var(--text-muted);">${e.timestamp.replace('T', ' ').substring(0, 19)}</span></td>
          <td><strong>${e.product_name}</strong> (${e.product_sku})</td>
          <td>${e.warehouse_name} / <code>${e.location_code}</code></td>
          <td><span class="badge ${e.change_qty > 0 ? 'badge-done' : 'badge-danger'}">${e.transaction_type}</span></td>
          <td style="font-weight: 700; color: ${e.change_qty > 0 ? '#10b981' : '#ef4444'}">${e.change_qty > 0 ? `+${e.change_qty}` : e.change_qty}</td>
          <td><strong>${e.balance_after}</strong></td>
          <td><code>${e.reference_type} #${e.reference_id}</code></td>
          <td style="font-size: 0.75rem; font-family: monospace; color: var(--text-muted);">${e.entry_uuid.substring(0, 8)}...</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error("Ledger load error", err);
    }
  }

  async performGlobalSearch(q) {
    try {
      const results = await api.search(q);
      if (results.length > 0) {
        alert(`Found ${results.length} products matching "${q}":\n` + results.map(r => `• ${r.name} (${r.sku}) - Price: ₹${r.selling_price}`).join('\n'));
      } else {
        alert(`No products found matching "${q}".`);
      }
    } catch (err) {
      alert(`Search error: ${err.message}`);
    }
  }
}

// Bootstrap application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  new StockSenseApp().init();
});
