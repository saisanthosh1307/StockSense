/**
 * StockSense Frontend Application
 * Fully connects to the FastAPI backend covering all 25 features.
 */

const API_BASE = window.location.origin.includes(":8000") 
  ? `${window.location.origin}/api/v1` 
  : "http://127.0.0.1:8000/api/v1";

// State
const state = {
  token: localStorage.getItem("token") || null,
  currentUser: JSON.parse(localStorage.getItem("user") || "null") || {
    name: "Elena Vance",
    email: "admin@stocksense.com",
    role: "ADMIN"
  },
  activeTab: "dashboard",
  kpis: null,
  products: [],
  warehouses: [],
  receipts: [],
  deliveries: [],
  transfers: [],
  adjustments: [],
  ledger: [],
  alerts: [],
  selectedProductId: null,
  forecastData: null,
  reorderData: null,
  explainData: null,
  confidenceData: null,
  anomalies: [],
  causeOfLoss: null,
  whatIfResult: null,
  digitalTwin: null,
  trustBlocks: [],
  trustVerification: null,
  chatMessages: [
    {
      role: "assistant",
      content: "Hello! I am your **StockSense AI Copilot**. How can I assist with your warehouse operations, demand forecasting, or ledger audit today?"
    }
  ],
  isChatOpen: false,
  modal: null
};

// API Helper
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "API Error");
    }
    return await res.json();
  } catch (err) {
    console.warn(`API call failed for ${path}:`, err.message);
    throw err;
  }
}

// Automatic Login / Token Refresh
async function loginAs(email, password = "password123") {
  const pword = email.includes("admin") ? "admin123" : email.includes("manager") ? "manager123" : "staff123";
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password: pword })
    });
    state.token = data.access_token;
    state.currentUser = data.user;
    localStorage.setItem("token", state.token);
    localStorage.setItem("user", JSON.stringify(state.currentUser));
    showToast(`Signed in as ${data.user.name} (${data.user.role})`);
    await loadInitialData();
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Initial Data Loader
async function loadInitialData() {
  try {
    // Try authenticating default user if no token
    if (!state.token) {
      await loginAs("admin@stocksense.com", "admin123");
      return;
    }

    const [kpis, prods, whs, recs, dels, trans, adjs, ledger, alerts] = await Promise.all([
      api("/dashboard/kpis").catch(() => null),
      api("/products").catch(() => []),
      api("/warehouses").catch(() => []),
      api("/receipts").catch(() => []),
      api("/deliveries").catch(() => []),
      api("/transfers").catch(() => []),
      api("/adjustments").catch(() => []),
      api("/ledger?limit=30").catch(() => []),
      api("/alerts").catch(() => [])
    ]);

    state.kpis = kpis;
    state.products = prods;
    state.warehouses = whs;
    state.receipts = recs;
    state.deliveries = dels;
    state.transfers = trans;
    state.adjustments = adjs;
    state.ledger = ledger;
    state.alerts = alerts;

    if (prods.length > 0 && !state.selectedProductId) {
      state.selectedProductId = prods[0].id;
    }
  } catch (e) {
    console.error("Initial load error:", e);
  }
}

// Toast Notifications
function showToast(msg, type = "success") {
  const existing = document.getElementById("toast-container");
  if (!existing) {
    const div = document.createElement("div");
    div.id = "toast-container";
    div.className = "fixed bottom-5 right-5 z-50 flex flex-col gap-2";
    document.body.appendChild(div);
  }
  const toast = document.createElement("div");
  const bg = type === "error" ? "bg-red-600 text-white" : "bg-emerald-600 text-white";
  toast.className = `${bg} px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 transform transition-all duration-300 translate-y-2 opacity-0`;
  toast.innerHTML = `<span>${msg}</span>`;
  document.getElementById("toast-container").appendChild(toast);
  setTimeout(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  }, 10);
  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// View Navigation
function setTab(tabName) {
  state.activeTab = tabName;
  if (tabName === "forecasting" || tabName === "reorder" || tabName === "explainability" || tabName === "confidence" || tabName === "whatif") {
    loadIntelligenceData(state.selectedProductId || (state.products[0] && state.products[0].id));
  } else if (tabName === "anomalies") {
    api("/intelligence/anomalies").then(data => { state.anomalies = data; render(); });
  } else if (tabName === "cause_of_loss") {
    api("/intelligence/cause-of-loss").then(data => { state.causeOfLoss = data; render(); });
  } else if (tabName === "digital_twin") {
    const whId = state.warehouses[0]?.id || 1;
    api(`/showcase/digital-twin/${whId}`).then(data => { state.digitalTwin = data; render(); });
  } else if (tabName === "trust_chain") {
    Promise.all([
      api("/showcase/trust-chain/blocks"),
      api("/showcase/trust-chain/verify")
    ]).then(([blocks, v]) => {
      state.trustBlocks = blocks;
      state.trustVerification = v;
      render();
    });
  }
  render();
}

async function loadIntelligenceData(productId) {
  if (!productId) return;
  state.selectedProductId = productId;
  try {
    const [fc, ro, exp, conf] = await Promise.all([
      api(`/intelligence/forecast/${productId}?horizon_days=14`).catch(() => null),
      api(`/intelligence/reorder/${productId}`).catch(() => null),
      api(`/intelligence/explainability/${productId}`).catch(() => null),
      api(`/intelligence/confidence/${productId}`).catch(() => null)
    ]);
    state.forecastData = fc;
    state.reorderData = ro;
    state.explainData = exp;
    state.confidenceData = conf;
    render();
  } catch (err) {
    console.error(err);
  }
}

// --- RENDER MAIN LAYOUT ---
function render() {
  const app = document.getElementById("app");
  if (!app) return;

  app.innerHTML = `
    <!-- Left Sidebar -->
    <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 border-r border-slate-800">
      <!-- App Brand -->
      <div class="h-16 flex items-center justify-between px-5 border-b border-slate-800 bg-slate-950">
        <div class="flex items-center gap-2.5">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white font-black text-lg shadow-md shadow-purple-500/20">
            S
          </div>
          <div>
            <div class="font-bold text-white text-base tracking-tight leading-tight">StockSense</div>
            <div class="text-[10px] text-purple-400 font-semibold uppercase tracking-wider">Modular IMS</div>
          </div>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="flex-1 overflow-y-auto p-3 space-y-6 text-xs">
        <!-- Operations Section -->
        <div>
          <div class="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">Core Operations (15)</div>
          <div class="space-y-1">
            ${navItem("dashboard", "📊 Dashboard", state.activeTab === "dashboard")}
            ${navItem("products", "📦 Products", state.activeTab === "products", state.products.length)}
            ${navItem("warehouses", "🏢 Warehouses & Racks", state.activeTab === "warehouses")}
            ${navItem("receipts", "📥 Incoming Receipts", state.activeTab === "receipts", state.receipts.filter(r => r.status !== "DONE").length)}
            ${navItem("deliveries", "📤 Outgoing Deliveries", state.activeTab === "deliveries", state.deliveries.filter(d => d.status !== "DONE").length)}
            ${navItem("transfers", "🔄 Internal Transfers", state.activeTab === "transfers")}
            ${navItem("adjustments", "⚖️ Stock Adjustments", state.activeTab === "adjustments")}
            ${navItem("ledger", "📜 Move Ledger", state.activeTab === "ledger")}
          </div>
        </div>

        <!-- Intelligent Section -->
        <div>
          <div class="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-indigo-400">Intelligent (7)</div>
          <div class="space-y-1">
            ${navItem("forecasting", "📈 Demand Forecast", state.activeTab === "forecasting")}
            ${navItem("reorder", "🎯 Dynamic Reorder & EOQ", state.activeTab === "reorder")}
            ${navItem("explainability", "💡 Explainability (XAI)", state.activeTab === "explainability")}
            ${navItem("confidence", "🎚️ Confidence Scores", state.activeTab === "confidence")}
            ${navItem("anomalies", "🚨 Anomaly Detection", state.activeTab === "anomalies", state.anomalies.length || "")}
            ${navItem("cause_of_loss", "📉 Cause-of-Loss", state.activeTab === "cause_of_loss")}
            ${navItem("whatif", "🔮 What-If Simulator", state.activeTab === "whatif")}
          </div>
        </div>

        <!-- Showcase Section -->
        <div>
          <div class="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-amber-400">Showcase (3)</div>
          <div class="space-y-1">
            ${navItem("digital_twin", "🌐 Digital Twin", state.activeTab === "digital_twin")}
            ${navItem("trust_chain", "🔗 Trust Chain", state.activeTab === "trust_chain")}
            ${navItem("copilot", "🤖 AI Assistant Copilot", state.activeTab === "copilot")}
          </div>
        </div>

        <!-- Management Tools -->
        <div>
          <div class="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">Management & Audit</div>
          <div class="space-y-1">
            ${navItem("qr_scanner", "🏷️ QR Engine & Barcode", state.activeTab === "qr_scanner")}
            ${navItem("reports", "📑 Reports & Valuation", state.activeTab === "reports")}
            ${navItem("roles", "👥 Roles & Permissions", state.activeTab === "roles")}
            ${navItem("audit", "🕵️ Audit Trail", state.activeTab === "audit")}
          </div>
        </div>
      </nav>

      <!-- Active User Card & Role Switcher -->
      <div class="p-3 border-t border-slate-800 bg-slate-950/60">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-full bg-purple-700 flex items-center justify-center font-bold text-white text-xs">
              ${(state.currentUser?.name || "U")[0]}
            </div>
            <div class="truncate">
              <div class="text-xs font-semibold text-white truncate">${state.currentUser?.name || "User"}</div>
              <div class="text-[10px] text-purple-400">${state.currentUser?.role || "Staff"}</div>
            </div>
          </div>
        </div>
        <div class="text-[10px] text-slate-300 mb-1">Switch RBAC Role:</div>
        <select onchange="loginAs(this.value)" class="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1 focus:ring-1 focus:ring-purple-500">
          <option value="admin@stocksense.com" ${state.currentUser?.role === "ADMIN" ? "selected" : ""}>👑 Elena (Admin)</option>
          <option value="manager@stocksense.com" ${state.currentUser?.role === "INVENTORY_MANAGER" ? "selected" : ""}>📦 Marcus (Manager)</option>
          <option value="staff@stocksense.com" ${state.currentUser?.role === "WAREHOUSE_STAFF" ? "selected" : ""}>👷 Sam (Warehouse Staff)</option>
        </select>
      </div>
    </aside>

    <!-- Main Workspace -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-100">
      <!-- Top Header -->
      <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-10">
        <!-- Search Bar -->
        <div class="relative w-96">
          <input 
            type="text" 
            id="global-search-input"
            oninput="handleSearch(this.value)"
            placeholder="Search SKU, product name, barcode, rack..." 
            class="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500 focus:bg-white transition-all"
          />
          <span class="absolute left-3 top-2.5 text-slate-400 text-xs">🔍</span>
          <div id="search-dropdown" class="hidden absolute top-10 left-0 right-0 bg-white border border-slate-200 rounded-lg shadow-xl z-50 p-2 max-h-72 overflow-y-auto"></div>
        </div>

        <!-- Top Right Actions -->
        <div class="flex items-center gap-3">
          <!-- Anomaly Scan Button -->
          <button onclick="scanForLowStock()" class="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium border border-slate-300 transition-all flex items-center gap-1.5">
            <span>⚡</span>
            <span>Check Low Stock</span>
          </button>

          <!-- Notification Bell -->
          <div class="relative">
            <button onclick="toggleAlertsDropdown()" class="w-9 h-9 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center relative transition-all">
              <span>🔔</span>
              ${state.alerts.filter(a => !a.is_read).length > 0 ? `<span class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[9px] flex items-center justify-center font-bold">${state.alerts.filter(a => !a.is_read).length}</span>` : ""}
            </button>
            <div id="alerts-dropdown" class="hidden absolute right-0 top-11 w-80 bg-white border border-slate-200 rounded-xl shadow-2xl z-50 p-3">
              <div class="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
                <span class="text-xs font-bold text-slate-800">Alerts & Notifications</span>
                <span class="text-[10px] text-slate-500">${state.alerts.length} total</span>
              </div>
              <div class="space-y-2 max-h-64 overflow-y-auto text-xs">
                ${state.alerts.length === 0 ? '<div class="text-slate-400 text-center py-4">No active alerts</div>' : state.alerts.map(a => `
                  <div class="p-2 rounded-lg ${a.is_read ? 'bg-slate-50' : 'bg-amber-50 border border-amber-200'}">
                    <div class="font-semibold text-slate-800">${a.title}</div>
                    <div class="text-[11px] text-slate-600 mt-0.5">${a.message}</div>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>

          <!-- Open AI Copilot Button -->
          <button onclick="setTab('copilot')" class="px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white text-xs font-semibold shadow-sm flex items-center gap-1.5 transition-all">
            <span>✨</span>
            <span>AI Copilot</span>
          </button>
        </div>
      </header>

      <!-- View Area Container -->
      <main class="flex-1 overflow-y-auto p-6">
        ${renderActiveTab()}
      </main>
    </div>

    <!-- Modal Container -->
    <div id="modal-container">${renderModal()}</div>
  `;
}

function navItem(tabId, label, active, badge = null) {
  const activeClass = active 
    ? "bg-purple-600/20 text-purple-400 font-semibold border-l-2 border-purple-500" 
    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200";
  return `
    <button onclick="setTab('${tabId}')" class="w-full flex items-center justify-between px-3 py-2 rounded-md text-left transition-all ${activeClass}">
      <span class="truncate">${label}</span>
      ${badge !== null && badge !== "" ? `<span class="bg-purple-900/80 text-purple-300 text-[10px] px-1.5 py-0.5 rounded-full font-bold">${badge}</span>` : ""}
    </button>
  `;
}

// --- ACTIVE TAB ROUTER ---
function renderActiveTab() {
  switch (state.activeTab) {
    case "dashboard": return renderDashboard();
    case "products": return renderProducts();
    case "warehouses": return renderWarehouses();
    case "receipts": return renderReceipts();
    case "deliveries": return renderDeliveries();
    case "transfers": return renderTransfers();
    case "adjustments": return renderAdjustments();
    case "ledger": return renderLedger();
    case "forecasting": return renderForecasting();
    case "reorder": return renderReorder();
    case "explainability": return renderExplainability();
    case "confidence": return renderConfidence();
    case "anomalies": return renderAnomalies();
    case "cause_of_loss": return renderCauseOfLoss();
    case "whatif": return renderWhatIf();
    case "digital_twin": return renderDigitalTwin();
    case "trust_chain": return renderTrustChain();
    case "copilot": return renderCopilot();
    case "qr_scanner": return renderQREngine();
    case "reports": return renderReports();
    case "roles": return renderRoles();
    case "audit": return renderAudit();
    default: return renderDashboard();
  }
}

// --- 1. DASHBOARD VIEW (Feature 9) ---
function renderDashboard() {
  const k = state.kpis || {
    total_products_in_stock: 5,
    low_stock_items_count: 1,
    out_of_stock_items_count: 0,
    pending_receipts_count: 1,
    pending_deliveries_count: 1,
    scheduled_transfers_count: 0,
    total_inventory_valuation: 6062.40,
    recent_activity_count: 8
  };

  return `
    <div class="space-y-6">
      <!-- Title & Greeting -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Inventory Operations Dashboard</h1>
          <p class="text-xs text-slate-500 mt-1">Real-time status of multi-warehouse stock, incoming vendor shipments, and outbound orders.</p>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="openModal('new_receipt')" class="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow transition-all">+ New Receipt</button>
          <button onclick="openModal('new_transfer')" class="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow transition-all">+ Internal Move</button>
        </div>
      </div>

      <!-- 6 KPI Metric Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        ${kpiCard("Total Catalog Items", k.total_products_in_stock, "Active SKUs in warehouses", "📦", "border-purple-200 bg-purple-50/50 text-purple-700")}
        ${kpiCard("Low / Out of Stock", k.low_stock_items_count, "At or below safety threshold", "⚠️", "border-amber-200 bg-amber-50/50 text-amber-700")}
        ${kpiCard("Pending Receipts", k.pending_receipts_count, "Awaiting vendor arrival", "📥", "border-blue-200 bg-blue-50/50 text-blue-700")}
        ${kpiCard("Pending Deliveries", k.pending_deliveries_count, "Orders ready to ship", "📤", "border-emerald-200 bg-emerald-50/50 text-emerald-700")}
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Inventory Valuation</div>
          <div class="text-3xl font-extrabold text-slate-800 mt-2">$${Number(k.total_inventory_valuation).toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
          <div class="text-xs text-emerald-600 mt-2 flex items-center gap-1">
            <span>↑ Asset backed across 2 distribution warehouses</span>
          </div>
        </div>
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Scheduled Internal Transfers</div>
          <div class="text-3xl font-extrabold text-slate-800 mt-2">${k.scheduled_transfers_count} scheduled</div>
          <div class="text-xs text-slate-500 mt-2">Rack-to-rack & plant replenishment operations</div>
        </div>
      </div>

      <!-- Quick Operations Feed with Dynamic Filter -->
      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-bold text-slate-800">Dynamic Operations Feed</h2>
          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-500">Filter Type:</span>
            <select id="feed-filter" onchange="filterOperationsFeed(this.value)" class="text-xs bg-slate-50 border border-slate-300 rounded px-2.5 py-1 text-slate-700">
              <option value="">All Documents</option>
              <option value="receipts">Receipts Only</option>
              <option value="deliveries">Deliveries Only</option>
              <option value="transfers">Transfers Only</option>
              <option value="adjustments">Adjustments Only</option>
            </select>
          </div>
        </div>
        <div id="operations-feed-list" class="divide-y divide-slate-100 text-xs">
          ${renderRecentOperations()}
        </div>
      </div>
    </div>
  `;
}

function kpiCard(title, val, subtitle, icon, style) {
  return `
    <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex items-start justify-between">
      <div>
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider">${title}</div>
        <div class="text-2xl font-bold text-slate-800 mt-1">${val}</div>
        <div class="text-[11px] text-slate-500 mt-1">${subtitle}</div>
      </div>
      <div class="w-10 h-10 rounded-lg flex items-center justify-center text-lg border ${style}">
        ${icon}
      </div>
    </div>
  `;
}

function renderRecentOperations() {
  const items = [];
  state.receipts.slice(0, 3).forEach(r => items.push({ type: "Receipt", ref: r.reference, partner: r.supplier_name, status: r.status, date: r.created_at, id: r.id }));
  state.deliveries.slice(0, 3).forEach(d => items.push({ type: "Delivery", ref: d.reference, partner: d.customer_name, status: d.status, date: d.created_at, id: d.id }));
  state.transfers.slice(0, 3).forEach(t => items.push({ type: "Transfer", ref: t.reference, partner: "Internal Move", status: t.status, date: t.created_at, id: t.id }));
  state.adjustments.slice(0, 3).forEach(a => items.push({ type: "Adjustment", ref: a.reference, partner: "Cycle Count", status: a.status, date: a.created_at, id: a.id }));

  items.sort((a, b) => new Date(b.date) - new Date(a.date));

  return items.map(item => `
    <div class="py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="px-2 py-1 rounded text-[10px] font-bold ${item.type === 'Receipt' ? 'bg-blue-100 text-blue-700' : item.type === 'Delivery' ? 'bg-emerald-100 text-emerald-700' : item.type === 'Transfer' ? 'bg-purple-100 text-purple-700' : 'bg-amber-100 text-amber-700'}">
          ${item.type}
        </span>
        <div>
          <div class="font-bold text-slate-800">${item.ref}</div>
          <div class="text-slate-500 text-[11px]">${item.partner}</div>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${item.status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">
          ${item.status}
        </span>
        ${item.status !== 'DONE' ? `<button onclick="quickValidate('${item.type.toLowerCase()}', ${item.id})" class="px-2.5 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-[11px] font-medium">Validate</button>` : ''}
      </div>
    </div>
  `).join("");
}

// --- 2. PRODUCTS VIEW (Feature 2) ---
function renderProducts() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Product Catalog & Reordering Rules</h1>
          <p class="text-xs text-slate-500 mt-1">Manage SKU catalog, Units of Measure (UoM), safety stock thresholds, and location availability.</p>
        </div>
        <button onclick="openModal('new_product')" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow transition-all">+ Add Product</button>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-semibold">
            <tr>
              <th class="py-3 px-4">Product Name & SKU</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4">Unit Cost / Price</th>
              <th class="py-3 px-4">On-Hand Stock</th>
              <th class="py-3 px-4">Reorder Rules (Min/Max)</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${state.products.map(p => `
              <tr class="hover:bg-slate-50/80 transition-all">
                <td class="py-3 px-4">
                  <div class="font-bold text-slate-800">${p.name}</div>
                  <div class="text-[11px] text-slate-500 font-mono">${p.sku} | Barcode: ${p.barcode || p.sku}</div>
                </td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">${p.category?.name || "Uncategorized"}</span>
                </td>
                <td class="py-3 px-4 font-mono">
                  <div>$${p.unit_price?.toFixed(2)} <span class="text-slate-400 text-[10px]">(Sell)</span></div>
                  <div class="text-slate-500 text-[11px]">$${p.unit_cost?.toFixed(2)} <span class="text-slate-400 text-[10px]">(Cost)</span></div>
                </td>
                <td class="py-3 px-4">
                  <div class="font-bold ${p.total_on_hand <= p.min_reorder_qty ? 'text-red-600' : 'text-slate-800'} text-sm">
                    ${p.total_on_hand} ${p.uom}
                  </div>
                  ${p.total_on_hand <= p.min_reorder_qty ? '<span class="inline-block mt-0.5 px-1.5 py-0.5 rounded bg-red-100 text-red-700 text-[9px] font-bold">REORDER TRIGGERED</span>' : '<span class="inline-block mt-0.5 text-emerald-600 text-[10px]">● Healthy Stock</span>'}
                </td>
                <td class="py-3 px-4 text-slate-600">
                  <div>Min: <strong>${p.min_reorder_qty}</strong> | Max: <strong>${p.max_reorder_qty}</strong></div>
                  <div class="text-[10px] text-slate-400">Lead time: ${p.lead_time_days} days</div>
                </td>
                <td class="py-3 px-4 text-right space-x-1">
                  <button onclick="viewProductQR(${p.id})" class="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[11px]">QR</button>
                  <button onclick="loadIntelligenceData(${p.id}); setTab('forecasting');" class="px-2 py-1 bg-purple-100 hover:bg-purple-200 text-purple-700 font-semibold rounded text-[11px]">AI Forecast</button>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 3. RECEIPTS VIEW (Feature 4) ---
function renderReceipts() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Incoming Vendor Receipts</h1>
          <p class="text-xs text-slate-500 mt-1">Receive stock from suppliers. Validating a receipt automatically updates the Stock Ledger and increases on-hand quantities.</p>
        </div>
        <button onclick="openModal('new_receipt')" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow transition-all">+ New Receipt</button>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-semibold">
            <tr>
              <th class="py-3 px-4">Receipt Ref</th>
              <th class="py-3 px-4">Supplier / Vendor</th>
              <th class="py-3 px-4">Items Expected</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4">Date Created</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${state.receipts.map(r => `
              <tr class="hover:bg-slate-50/80">
                <td class="py-3 px-4 font-mono font-bold text-purple-700">${r.reference}</td>
                <td class="py-3 px-4 font-medium text-slate-800">${r.supplier_name}</td>
                <td class="py-3 px-4">
                  ${r.lines.map(l => `<span class="inline-block bg-slate-100 text-slate-700 rounded px-1.5 py-0.5 mr-1 text-[11px]">${l.quantity_expected} units</span>`).join("")}
                </td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${r.status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}">
                    ${r.status}
                  </span>
                </td>
                <td class="py-3 px-4 text-slate-500">${new Date(r.created_at).toLocaleDateString()}</td>
                <td class="py-3 px-4 text-right">
                  ${r.status !== 'DONE' 
                    ? `<button onclick="validateReceipt(${r.id})" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold shadow-sm transition-all">Validate & Add Stock</button>`
                    : `<span class="text-emerald-600 text-xs font-medium">✓ Validated</span>`
                  }
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 4. DELIVERIES VIEW (Feature 5) ---
function renderDeliveries() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Outgoing Deliveries (Sales Orders)</h1>
          <p class="text-xs text-slate-500 mt-1">Pick, pack, and validate customer shipments. Validation automatically executes double-entry stock reduction.</p>
        </div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-semibold">
            <tr>
              <th class="py-3 px-4">Delivery Ref</th>
              <th class="py-3 px-4">Customer</th>
              <th class="py-3 px-4">Items Demanded</th>
              <th class="py-3 px-4">Pick / Pack Status</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${state.deliveries.map(d => `
              <tr class="hover:bg-slate-50/80">
                <td class="py-3 px-4 font-mono font-bold text-indigo-700">${d.reference}</td>
                <td class="py-3 px-4 font-medium text-slate-800">${d.customer_name}</td>
                <td class="py-3 px-4">
                  ${d.lines.map(l => `<span class="bg-slate-100 text-slate-700 rounded px-1.5 py-0.5 text-[11px]">${l.quantity_demanded} units</span>`).join("")}
                </td>
                <td class="py-3 px-4">
                  <div class="flex items-center gap-1.5 text-[10px]">
                    <span class="px-1.5 py-0.5 rounded ${d.is_picked ? 'bg-emerald-100 text-emerald-700 font-bold' : 'bg-slate-200 text-slate-600'}">Picked</span>
                    <span>→</span>
                    <span class="px-1.5 py-0.5 rounded ${d.is_packed ? 'bg-emerald-100 text-emerald-700 font-bold' : 'bg-slate-200 text-slate-600'}">Packed</span>
                  </div>
                </td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${d.status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">
                    ${d.status}
                  </span>
                </td>
                <td class="py-3 px-4 text-right space-x-1">
                  ${d.status !== 'DONE' ? `
                    ${!d.is_picked ? `<button onclick="pickDelivery(${d.id})" class="px-2.5 py-1 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded text-xs">Pick</button>` : ''}
                    ${d.is_picked && !d.is_packed ? `<button onclick="packDelivery(${d.id})" class="px-2.5 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded text-xs">Pack</button>` : ''}
                    <button onclick="validateDelivery(${d.id})" class="px-2.5 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-semibold">Validate</button>
                  ` : `<span class="text-emerald-600 text-xs font-medium">✓ Shipped</span>`}
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 5. INTERNAL TRANSFERS VIEW (Feature 6) ---
function renderTransfers() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Internal Stock Transfers</h1>
          <p class="text-xs text-slate-500 mt-1">Move inventory between warehouses and racks (e.g. Main Store → Production Floor). Company total remains constant.</p>
        </div>
        <button onclick="openModal('new_transfer')" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow transition-all">+ New Transfer</button>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-semibold">
            <tr>
              <th class="py-3 px-4">Transfer Ref</th>
              <th class="py-3 px-4">Source Location</th>
              <th class="py-3 px-4">Destination Location</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${state.transfers.map(t => `
              <tr class="hover:bg-slate-50/80">
                <td class="py-3 px-4 font-mono font-bold text-purple-700">${t.reference}</td>
                <td class="py-3 px-4 font-medium text-slate-700">${t.source_location_id} (Internal)</td>
                <td class="py-3 px-4 font-medium text-slate-700">${t.destination_location_id} (Internal)</td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${t.status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}">
                    ${t.status}
                  </span>
                </td>
                <td class="py-3 px-4 text-right">
                  ${t.status !== 'DONE' 
                    ? `<button onclick="validateTransfer(${t.id})" class="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-semibold">Execute Transfer</button>`
                    : `<span class="text-emerald-600 text-xs font-medium">✓ Completed</span>`
                  }
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 6. ADJUSTMENTS VIEW (Feature 7) ---
function renderAdjustments() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Physical Stock Count Adjustments</h1>
          <p class="text-xs text-slate-500 mt-1">Reconcile discrepancies between recorded balances and physical shelf counts (e.g. 3 kg steel damaged -> Stock: -3).</p>
        </div>
        <button onclick="openModal('new_adjustment')" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow transition-all">+ New Adjustment</button>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-semibold">
            <tr>
              <th class="py-3 px-4">Adjustment Ref</th>
              <th class="py-3 px-4">Discrepancy Details</th>
              <th class="py-3 px-4">Attributed Cause</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${state.adjustments.map(a => `
              <tr class="hover:bg-slate-50/80">
                <td class="py-3 px-4 font-mono font-bold text-slate-800">${a.reference}</td>
                <td class="py-3 px-4">
                  ${a.lines.map(l => `
                    <div>Recorded: <strong>${l.recorded_qty}</strong> | Counted: <strong>${l.counted_qty}</strong> 
                    (<span class="${l.difference_qty < 0 ? 'text-red-600 font-bold' : 'text-emerald-600 font-bold'}">${l.difference_qty > 0 ? '+' : ''}${l.difference_qty}</span>)</div>
                  `).join("")}
                </td>
                <td class="py-3 px-4 font-medium text-slate-600">
                  ${a.lines[0]?.loss_cause || "Count Mismatch"}
                </td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${a.status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">
                    ${a.status}
                  </span>
                </td>
                <td class="py-3 px-4 text-right">
                  ${a.status !== 'DONE'
                    ? `<button onclick="validateAdjustment(${a.id})" class="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-semibold">Confirm Adjustment</button>`
                    : `<span class="text-emerald-600 text-xs font-medium">✓ Logged to Scrap</span>`
                  }
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 7. STOCK LEDGER VIEW (Feature 8) ---
function renderLedger() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Double-Entry Stock Ledger</h1>
          <p class="text-xs text-slate-500 mt-1">Immutable move history where every transaction is recorded with source location, destination location, and SHA-256 integrity signature.</p>
        </div>
        <button onclick="exportCSV()" class="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow transition-all">Export CSV</button>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase font-semibold">
            <tr>
              <th class="py-3 px-4">Timestamp</th>
              <th class="py-3 px-4">Move Ref & Type</th>
              <th class="py-3 px-4">Product SKU</th>
              <th class="py-3 px-4">From Location → To Location</th>
              <th class="py-3 px-4">Quantity</th>
              <th class="py-3 px-4">Total Value</th>
              <th class="py-3 px-4">Cryptographic Hash</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 font-mono">
            ${state.ledger.map(m => `
              <tr class="hover:bg-slate-50/80">
                <td class="py-3 px-4 text-slate-500 font-sans">${new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                <td class="py-3 px-4">
                  <span class="font-bold text-slate-800">${m.reference}</span>
                  <span class="ml-1 text-[9px] px-1.5 py-0.5 rounded font-sans font-bold ${m.move_type === 'RECEIPT' ? 'bg-blue-100 text-blue-700' : m.move_type === 'DELIVERY' ? 'bg-emerald-100 text-emerald-700' : 'bg-purple-100 text-purple-700'}">
                    ${m.move_type}
                  </span>
                </td>
                <td class="py-3 px-4 font-bold text-slate-700">${m.product_sku || m.product_name}</td>
                <td class="py-3 px-4 text-slate-600 font-sans">
                  ${m.from_location_name || 'Vendor/Origin'} → ${m.to_location_name || 'Customer/Dest'}
                </td>
                <td class="py-3 px-4 font-bold text-slate-800">${m.quantity}</td>
                <td class="py-3 px-4 font-sans">$${m.total_value?.toFixed(2)}</td>
                <td class="py-3 px-4 text-[10px] text-slate-400 truncate max-w-xs" title="${m.record_hash}">
                  ${m.record_hash?.slice(0, 16)}...
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 8. DEMAND FORECASTING (Feature 16) ---
function renderForecasting() {
  const fc = state.forecastData;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Demand Forecasting (Holt's Double Smoothing)</h1>
          <p class="text-xs text-slate-500 mt-1">Statistical forward demand projections featuring 95% Confidence Intervals.</p>
        </div>
        <select onchange="loadIntelligenceData(this.value)" class="text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-semibold shadow-sm">
          ${state.products.map(p => `<option value="${p.id}" ${p.id === state.selectedProductId ? 'selected' : ''}>${p.name} (${p.sku})</option>`).join("")}
        </select>
      </div>

      ${!fc ? '<div class="text-slate-500 py-10 text-center">Loading forecast model...</div>' : `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Daily Average Demand</div>
            <div class="text-2xl font-bold text-purple-700 mt-1">${fc.daily_average_demand} units / day</div>
            <div class="text-[11px] text-slate-500 mt-1">Computed from past warehouse movements</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">14-Day Projected Demand</div>
            <div class="text-2xl font-bold text-indigo-700 mt-1">${fc.total_forecasted_demand} units</div>
            <div class="text-[11px] text-slate-500 mt-1">Expected outbound consumption</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Algorithm Engine</div>
            <div class="text-sm font-bold text-slate-800 mt-2 truncate">${fc.algorithm_used}</div>
            <div class="text-[11px] text-emerald-600 mt-1">✓ 95% Confidence Interval band active</div>
          </div>
        </div>

        <!-- Visual Trend Graph Representation -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h2 class="text-sm font-bold text-slate-800 mb-4">Historical vs Forecasted Demand Trajectory (14 Days)</h2>
          <div class="h-64 flex items-end gap-2 border-b border-l border-slate-200 p-4">
            ${fc.data.map(d => {
              const val = d.forecasted_demand !== null ? d.forecasted_demand : d.historical_demand;
              const heightPct = Math.min(100, Math.max(15, (val / (fc.daily_average_demand * 2 || 10)) * 100));
              const isFuture = d.forecasted_demand !== null;
              return `
                <div class="flex-1 flex flex-col items-center gap-1 group relative">
                  <div class="w-full rounded-t transition-all ${isFuture ? 'bg-purple-500 hover:bg-purple-600' : 'bg-slate-300 hover:bg-slate-400'}" style="height: ${heightPct}%;"></div>
                  <span class="text-[9px] text-slate-400 truncate w-full text-center">${d.date.slice(5)}</span>
                  <!-- Tooltip -->
                  <div class="hidden group-hover:block absolute -top-12 bg-slate-900 text-white text-[10px] px-2 py-1 rounded shadow-lg whitespace-nowrap z-20">
                    ${isFuture ? `Forecast: ${d.forecasted_demand} (95% CI: [${d.lower_bound_95} - ${d.upper_bound_95}])` : `Actual: ${d.historical_demand}`}
                  </div>
                </div>
              `;
            }).join("")}
          </div>
          <div class="flex items-center gap-4 mt-4 text-xs">
            <div class="flex items-center gap-1.5"><span class="w-3 h-3 bg-slate-300 rounded"></span> Historical Outbound</div>
            <div class="flex items-center gap-1.5"><span class="w-3 h-3 bg-purple-500 rounded"></span> Projected Forward Demand (95% CI)</div>
          </div>
        </div>
      `}
    </div>
  `;
}

// --- 9. DYNAMIC REORDER ENGINE (Feature 17 & 18) ---
function renderReorder() {
  const ro = state.reorderData;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Dynamic Reorder Engine & EOQ Optimization</h1>
          <p class="text-xs text-slate-500 mt-1">Calculates real-time Reorder Points (ROP = (d × L) + SS) and Economic Order Quantity (EOQ).</p>
        </div>
        <select onchange="loadIntelligenceData(this.value)" class="text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-semibold shadow-sm">
          ${state.products.map(p => `<option value="${p.id}" ${p.id === state.selectedProductId ? 'selected' : ''}>${p.name}</option>`).join("")}
        </select>
      </div>

      ${!ro ? '<div class="text-slate-500 py-10 text-center">Loading reorder calculations...</div>' : `
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Current Stock</div>
            <div class="text-3xl font-extrabold text-slate-800 mt-1">${ro.current_on_hand}</div>
            <div class="text-[11px] mt-1 font-semibold ${ro.reorder_triggered ? 'text-red-600' : 'text-emerald-600'}">
              ${ro.reorder_triggered ? '⚠️ Below Reorder Point' : '● Sufficient Buffer'}
            </div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Reorder Point (ROP)</div>
            <div class="text-3xl font-extrabold text-purple-700 mt-1">${ro.reorder_point}</div>
            <div class="text-[11px] text-slate-500 mt-1">${ro.lead_time_demand} LTD + ${ro.safety_stock} Safety Stock</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Optimal EOQ</div>
            <div class="text-3xl font-extrabold text-indigo-700 mt-1">${ro.economic_order_qty_eoq}</div>
            <div class="text-[11px] text-slate-500 mt-1">Minimizes holding vs setup cost</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Recommended Order</div>
            <div class="text-3xl font-extrabold text-amber-600 mt-1">${ro.recommended_order_qty}</div>
            <div class="text-[11px] text-slate-500 mt-1">Units to purchase now</div>
          </div>
        </div>

        <div class="bg-gradient-to-r from-purple-900 to-indigo-900 text-white rounded-xl p-6 shadow-lg flex items-center justify-between">
          <div>
            <div class="text-xs uppercase tracking-wider text-purple-300 font-bold">Algorithmic Replenishment Order</div>
            <div class="text-lg font-bold mt-1">${ro.reorder_triggered ? `Purchase order recommended for ${ro.recommended_order_qty} units of ${ro.product_name}` : `Inventory healthy: No purchase order required currently`}</div>
            <div class="text-xs text-purple-200 mt-1">Supplier lead time: ${ro.lead_time_days} days | Urgency Level: ${ro.urgency_level}</div>
          </div>
          ${ro.reorder_triggered ? `<button onclick="openModal('new_receipt'); document.getElementById('receipt-supplier').value='Auto Vendor'; " class="px-4 py-2 bg-white text-purple-900 hover:bg-purple-50 rounded-lg text-xs font-bold shadow transition-all">Draft Purchase Order</button>` : ''}
        </div>
      `}
    </div>
  `;
}

// --- 10. EXPLAINABILITY VIEW (Feature 18) ---
function renderExplainability() {
  const exp = state.explainData;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Explainable AI (XAI) Factor Decomposition</h1>
          <p class="text-xs text-slate-500 mt-1">Inspect the mathematical and empirical rationale behind algorithmic replenishment orders.</p>
        </div>
        <select onchange="loadIntelligenceData(this.value)" class="text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-semibold shadow-sm">
          ${state.products.map(p => `<option value="${p.id}" ${p.id === state.selectedProductId ? 'selected' : ''}>${p.name}</option>`).join("")}
        </select>
      </div>

      ${!exp ? '<div class="text-slate-500 py-10 text-center">Loading explainability decomposition...</div>' : `
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div class="text-sm font-bold text-slate-800 uppercase tracking-wide text-purple-700">Executive Summary</div>
          <p class="text-sm text-slate-700 mt-2 leading-relaxed">${exp.executive_summary}</p>
          <div class="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg font-mono text-xs text-slate-600">
            <strong>Formula Derivation:</strong> ${exp.formula_derivation}
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          ${exp.factors_breakdown.map(f => `
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-800">${f.factor}</span>
                <span class="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700 font-bold">${f.contribution_pct}%</span>
              </div>
              <div class="text-lg font-bold text-slate-800 mt-2">${f.value}</div>
              <p class="text-[11px] text-slate-500 mt-2 leading-normal">${f.description}</p>
            </div>
          `).join("")}
        </div>
      `}
    </div>
  `;
}

// --- 11. CONFIDENCE SCORE VIEW (Feature 19) ---
function renderConfidence() {
  const conf = state.confidenceData;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Confidence Scoring & Error Metrics</h1>
          <p class="text-xs text-slate-500 mt-1">Measures the statistical accuracy of forecasts and reorder recommendations based on demand volatility.</p>
        </div>
        <select onchange="loadIntelligenceData(this.value)" class="text-xs bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-semibold shadow-sm">
          ${state.products.map(p => `<option value="${p.id}" ${p.id === state.selectedProductId ? 'selected' : ''}>${p.name}</option>`).join("")}
        </select>
      </div>

      ${!conf ? '<div class="text-slate-500 py-10 text-center">Loading model confidence...</div>' : `
        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
          <div>
            <div class="text-xs font-semibold text-slate-500 uppercase">Overall Reliability Rating</div>
            <div class="text-4xl font-extrabold text-purple-700 mt-1">${conf.confidence_score}%</div>
            <div class="text-xs font-bold mt-1 text-emerald-600">● Tier: ${conf.confidence_tier}</div>
          </div>
          <div class="text-right">
            <div class="text-xs text-slate-500">Margin of Error</div>
            <div class="text-2xl font-bold text-slate-800">±${conf.margin_of_error_pct}%</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Sample observations: ${conf.sample_size_days} days</div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          ${conf.metrics.map(m => `
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div class="text-xs font-semibold text-slate-500 uppercase">${m.metric_name}</div>
              <div class="text-2xl font-bold text-slate-800 mt-1">${m.value}</div>
              <div class="text-xs text-slate-600 mt-2">${m.interpretation}</div>
            </div>
          `).join("")}
        </div>
      `}
    </div>
  `;
}

// --- 12. ANOMALIES VIEW (Feature 20) ---
function renderAnomalies() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Anomaly Detection & Irregular Movements</h1>
          <p class="text-xs text-slate-500 mt-1">Statistical Z-Score outlier detection flagging suspicious consumption spikes and abnormal count write-offs.</p>
        </div>
        <button onclick="api('/intelligence/anomalies').then(d => { state.anomalies = d; render(); }); showToast('Scan refreshed');" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow">Re-Scan Movements</button>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div class="p-4 border-b border-slate-200 bg-slate-50 text-xs font-bold text-slate-700">Flagged Anomalies (${state.anomalies.length})</div>
        <div class="divide-y divide-slate-100 text-xs">
          ${state.anomalies.length === 0 ? '<div class="p-8 text-center text-slate-400">Zero anomalous movements detected. Outbound operations match historical standard deviations.</div>' : state.anomalies.map(a => `
            <div class="p-4 flex items-start justify-between hover:bg-slate-50">
              <div class="flex items-start gap-3">
                <span class="px-2 py-1 rounded text-[10px] font-bold ${a.severity === 'HIGH' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}">
                  ${a.severity}
                </span>
                <div>
                  <div class="font-bold text-slate-800">${a.product_name} (${a.anomaly_type})</div>
                  <div class="text-slate-600 mt-1">${a.explanation}</div>
                  <div class="text-[10px] text-slate-400 mt-1">Z-Score: ${a.z_score} | Observed: ${a.observed_value} vs Expected: ${a.expected_value}</div>
                </div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    </div>
  `;
}

// --- 13. CAUSE OF LOSS VIEW (Feature 21) ---
function renderCauseOfLoss() {
  const cl = state.causeOfLoss;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Cause-of-Loss & Shrinkage Attribution</h1>
          <p class="text-xs text-slate-500 mt-1">Categorization of inventory write-offs across Handling Damage, Spoilage, Shrinkage/Theft, and Transit Loss.</p>
        </div>
      </div>

      ${!cl ? '<div class="text-slate-500 py-10 text-center">Loading loss attribution metrics...</div>' : `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Total Financial Loss</div>
            <div class="text-3xl font-extrabold text-red-600 mt-1">$${cl.total_financial_loss?.toFixed(2)}</div>
            <div class="text-xs text-slate-500 mt-1">${cl.total_units_lost} total units written off</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Primary Loss Driver</div>
            <div class="text-2xl font-bold text-slate-800 mt-1">${cl.categories[0]?.cause || "None"}</div>
            <div class="text-xs text-red-600 mt-1">${cl.categories[0]?.percentage_of_total_loss}% of total financial damage</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Top Affected Product</div>
            <div class="text-2xl font-bold text-slate-800 mt-1">${cl.top_affected_product}</div>
            <div class="text-xs text-slate-500 mt-1">Requires targeted quality inspections</div>
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h2 class="text-sm font-bold text-slate-800 mb-4">Loss Cause Distribution</h2>
          <div class="space-y-3">
            ${cl.categories.map(c => `
              <div>
                <div class="flex justify-between text-xs font-semibold mb-1">
                  <span>${c.cause} (${c.incident_count} incidents)</span>
                  <span>$${c.financial_impact?.toFixed(2)} (${c.percentage_of_total_loss}%)</span>
                </div>
                <div class="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div class="bg-red-500 h-2.5 rounded-full" style="width: ${c.percentage_of_total_loss}%"></div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `}
    </div>
  `;
}

// --- 14. WHAT-IF SIMULATOR (Feature 22) ---
function renderWhatIf() {
  const w = state.whatIfResult;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">What-if Scenario Simulator</h1>
          <p class="text-xs text-slate-500 mt-1">Interactive stress-test engine simulating supply chain shocks (demand surges, lead time delays) to project stockout dates.</p>
        </div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Product to Stress-Test:</label>
            <select id="whatif-prod" class="w-full bg-slate-50 border border-slate-300 rounded px-3 py-2 text-xs">
              ${state.products.map(p => `<option value="${p.id}">${p.name} (${p.sku})</option>`).join("")}
            </select>
          </div>
          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Simulated Demand Surge (%): <span id="surge-val" class="text-purple-600 font-bold">+35%</span></label>
            <input type="range" id="whatif-surge" min="0" max="100" value="35" oninput="document.getElementById('surge-val').innerText = '+' + this.value + '%'" class="w-full" />
          </div>
          <div>
            <label class="block text-xs font-bold text-slate-700 mb-1">Supplier Lead Time Delay: <span id="delay-val" class="text-purple-600 font-bold">+7 days</span></label>
            <input type="range" id="whatif-delay" min="0" max="30" value="7" oninput="document.getElementById('delay-val').innerText = '+' + this.value + ' days'" class="w-full" />
          </div>
        </div>
        <button onclick="runWhatIfSim()" class="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-lg text-xs font-bold shadow">
          ⚡ Execute Simulation
        </button>
      </div>

      <div id="whatif-output">
        ${!w ? '<div class="text-slate-400 py-6 text-center text-xs">Run a simulation above to preview stockout timelines and emergency buffer requirements.</div>' : `
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div class="text-xs font-semibold text-slate-500 uppercase">Days to Stockout</div>
              <div class="text-3xl font-extrabold ${w.days_to_stockout ? 'text-red-600' : 'text-emerald-600'} mt-1">
                ${w.days_to_stockout ? `Day ${w.days_to_stockout}` : 'No Stockout'}
              </div>
              <div class="text-xs text-slate-500 mt-1">Under simulated +${document.getElementById('whatif-surge')?.value || 35}% shock</div>
            </div>
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div class="text-xs font-semibold text-slate-500 uppercase">Projected Revenue Loss</div>
              <div class="text-3xl font-extrabold text-red-600 mt-1">$${w.projected_revenue_loss?.toFixed(2)}</div>
              <div class="text-xs text-slate-500 mt-1">Unmet customer orders</div>
            </div>
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div class="text-xs font-semibold text-slate-500 uppercase">Required Emergency Buffer</div>
              <div class="text-3xl font-extrabold text-purple-700 mt-1">${w.recommended_emergency_buffer} units</div>
              <div class="text-xs text-slate-500 mt-1">Buffer needed to prevent stockout</div>
            </div>
          </div>
        `}
      </div>
    </div>
  `;
}

// --- 15. DIGITAL TWIN VIEW (Feature 23) ---
function renderDigitalTwin() {
  const dt = state.digitalTwin;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Warehouse Digital Twin & Slotting Heatmaps</h1>
          <p class="text-xs text-slate-500 mt-1">Real-time 2D/3D layout mapping rack occupancy, capacity utilization %, and pick velocity heat intensity.</p>
        </div>
        <select onchange="api('/showcase/digital-twin/' + this.value).then(d => { state.digitalTwin = d; render(); });" class="text-xs bg-white border border-slate-300 rounded px-3 py-2 font-semibold">
          ${state.warehouses.map(w => `<option value="${w.id}">${w.name} (${w.code})</option>`).join("")}
        </select>
      </div>

      ${!dt ? '<div class="text-slate-500 py-10 text-center">Loading virtual warehouse twin...</div>' : `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Overall Capacity Utilization</div>
            <div class="text-3xl font-extrabold text-purple-700 mt-1">${dt.overall_capacity_utilization_pct}%</div>
            <div class="text-xs text-slate-500 mt-1">${dt.total_items_stored} units currently racked</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Total Rack Locations</div>
            <div class="text-3xl font-extrabold text-slate-800 mt-1">${dt.total_locations}</div>
            <div class="text-xs text-slate-500 mt-1">Across ${dt.zones.join(", ")}</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div class="text-xs font-semibold text-slate-500 uppercase">Heatmap Mode</div>
            <div class="text-sm font-bold text-slate-800 mt-2">Dual Mode Active</div>
            <div class="text-xs text-emerald-600 mt-1">● Density & Pick Intensity Combined</div>
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 class="text-sm font-bold text-slate-800 mb-4">Virtual Floorplan & Rack Matrix</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            ${dt.slots.map(s => `
              <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 hover:bg-purple-50/50 hover:border-purple-300 transition-all cursor-pointer">
                <div class="flex items-center justify-between text-xs mb-2">
                  <span class="font-bold text-slate-800">${s.name}</span>
                  <span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${s.status === 'OPTIMAL' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">${s.status}</span>
                </div>
                <div class="text-[11px] text-slate-500 font-mono">${s.code}</div>
                <div class="text-[10px] text-slate-400 mt-0.5">${s.zone} | ${s.aisle} | ${s.rack}</div>
                <div class="mt-3">
                  <div class="flex justify-between text-[10px] text-slate-500 mb-1">
                    <span>Capacity: ${s.capacity_used} / ${s.capacity_total}</span>
                    <span>${s.utilization_pct}%</span>
                  </div>
                  <div class="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-purple-600 h-1.5 rounded-full" style="width: ${s.utilization_pct}%"></div>
                  </div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `}
    </div>
  `;
}

// --- 16. TRUST CHAIN VIEW (Feature 24) ---
function renderTrustChain() {
  const v = state.trustVerification;
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Trust Chain - Cryptographic Ledger Verification</h1>
          <p class="text-xs text-slate-500 mt-1">Immutable SHA-256 Merkle blockchain sealing stock move batches to guarantee tamper resistance.</p>
        </div>
        <button onclick="api('/showcase/trust-chain/verify').then(res => { state.trustVerification = res; render(); showToast('Chain re-verified!'); });" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow">
          🛡️ Run Full Cryptographic Audit
        </button>
      </div>

      ${v ? `
        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-5 flex items-center justify-between">
          <div>
            <div class="text-sm font-bold text-emerald-800 flex items-center gap-2">
              <span>✓</span> <span>${v.verification_status}: Cryptographic Hash Integrity Intact</span>
            </div>
            <div class="text-xs text-emerald-700 mt-1">${v.audit_notes}</div>
          </div>
          <div class="text-right text-xs text-emerald-800 font-mono">
            <div>Blocks: <strong>${v.total_blocks_checked}</strong></div>
            <div>Moves Sealed: <strong>${v.total_moves_secured}</strong></div>
          </div>
        </div>
      ` : ""}

      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div class="p-4 border-b border-slate-200 bg-slate-50 font-bold text-xs text-slate-700">Blockchain Block History</div>
        <table class="w-full text-left text-xs font-mono">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-sans text-[11px]">
            <tr>
              <th class="py-2.5 px-4">Index</th>
              <th class="py-2.5 px-4">Block Hash (SHA-256)</th>
              <th class="py-2.5 px-4">Previous Hash</th>
              <th class="py-2.5 px-4">Merkle Root</th>
              <th class="py-2.5 px-4">Nonce</th>
              <th class="py-2.5 px-4 font-sans">Timestamp</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${state.trustBlocks.map(b => `
              <tr class="hover:bg-slate-50">
                <td class="py-2.5 px-4 font-bold text-purple-700">#${b.block_index}</td>
                <td class="py-2.5 px-4 text-slate-800 truncate max-w-xs" title="${b.block_hash}">${b.block_hash.slice(0, 18)}...</td>
                <td class="py-2.5 px-4 text-slate-400 truncate max-w-xs">${b.previous_hash.slice(0, 16)}...</td>
                <td class="py-2.5 px-4 text-slate-500 truncate max-w-xs">${b.merkle_root.slice(0, 16)}...</td>
                <td class="py-2.5 px-4 font-sans text-slate-600">${b.nonce}</td>
                <td class="py-2.5 px-4 font-sans text-slate-500">${new Date(b.timestamp).toLocaleTimeString()}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 17. AI COPILOT VIEW (Feature 25) ---
function renderCopilot() {
  return `
    <div class="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">StockSense AI Assistant Copilot</h1>
        <p class="text-xs text-slate-500 mt-1">Natural language conversational agent for stock inquiries, anomaly diagnosis, and operations tracking.</p>
      </div>

      <!-- Prompt Chips -->
      <div class="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <button onclick="askCopilot('Which products are low on stock?')" class="px-3 py-1.5 bg-white border border-purple-200 text-purple-700 hover:bg-purple-50 rounded-full font-medium shadow-sm transition-all whitespace-nowrap">
          ⚠️ Check low stock
        </button>
        <button onclick="askCopilot('Forecast demand for steel rods')" class="px-3 py-1.5 bg-white border border-purple-200 text-purple-700 hover:bg-purple-50 rounded-full font-medium shadow-sm transition-all whitespace-nowrap">
          📈 Forecast demand
        </button>
        <button onclick="askCopilot('Show pending warehouse receipts')" class="px-3 py-1.5 bg-white border border-purple-200 text-purple-700 hover:bg-purple-50 rounded-full font-medium shadow-sm transition-all whitespace-nowrap">
          📋 Pending operations
        </button>
        <button onclick="askCopilot('What is the primary cause of stock loss?')" class="px-3 py-1.5 bg-white border border-purple-200 text-purple-700 hover:bg-purple-50 rounded-full font-medium shadow-sm transition-all whitespace-nowrap">
          📉 Shrinkage analysis
        </button>
      </div>

      <!-- Chat Thread -->
      <div class="bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col h-[520px]">
        <div id="chat-messages" class="flex-1 p-5 overflow-y-auto space-y-4 text-xs">
          ${state.chatMessages.map(m => `
            <div class="flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}">
              <div class="max-w-[80%] rounded-xl p-3.5 ${m.role === 'user' ? 'bg-purple-600 text-white rounded-br-none' : 'bg-slate-100 text-slate-800 rounded-bl-none'}">
                <div class="prose prose-xs whitespace-pre-wrap">${m.content}</div>
              </div>
            </div>
          `).join("")}
        </div>

        <!-- Chat Input -->
        <div class="p-3 border-t border-slate-200 bg-slate-50 flex items-center gap-2">
          <input 
            type="text" 
            id="copilot-input" 
            placeholder="Ask about inventory, forecasts, receipts, or anomalies..."
            class="flex-1 bg-white border border-slate-300 rounded-lg px-4 py-2.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
            onkeydown="if (event.key === 'Enter') sendCopilotMessage()"
          />
          <button onclick="sendCopilotMessage()" class="px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold shadow">
            Send
          </button>
        </div>
      </div>
    </div>
  `;
}

// --- 18. QR ENGINE (Feature 14) ---
function renderQREngine() {
  return `
    <div class="space-y-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">QR Code Generation & Mobile Scanner</h1>
        <p class="text-xs text-slate-500 mt-1">Generate 2D QR labels for products and racks, or simulate barcode scans for instant lookup.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Generate QR Card -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h2 class="text-sm font-bold text-slate-800">Generate Product QR Code</h2>
          <select id="qr-prod-select" onchange="viewProductQR(this.value)" class="w-full bg-slate-50 border border-slate-300 rounded px-3 py-2 text-xs">
            ${state.products.map(p => `<option value="${p.id}">${p.name} (${p.sku})</option>`).join("")}
          </select>
          <div id="qr-preview-area" class="flex flex-col items-center justify-center p-6 border border-dashed border-slate-200 rounded-xl min-h-[220px]">
            <span class="text-slate-400 text-xs">Select a product to render its QR label</span>
          </div>
        </div>

        <!-- Scanner Simulator -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h2 class="text-sm font-bold text-slate-800">Simulate Barcode / QR Scanner</h2>
          <p class="text-xs text-slate-500">Scan hardware or enter raw barcode string below to resolve real-time entity.</p>
          <div class="flex gap-2">
            <input type="text" id="scanner-input" placeholder="e.g. STEEL-ROD-12, BAR-STL-001..." class="flex-1 bg-slate-50 border border-slate-300 rounded px-3 py-2 text-xs" />
            <button onclick="simulateScan(document.getElementById('scanner-input').value)" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs font-bold">
              Scan
            </button>
          </div>
          <div id="scan-result-area" class="p-4 bg-slate-50 rounded-lg text-xs min-h-[140px] text-slate-500">
            Awaiting barcode input...
          </div>
        </div>
      </div>
    </div>
  `;
}

// --- 19. REPORTS VIEW (Feature 12) ---
function renderReports() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Valuation & Velocity Reports</h1>
          <p class="text-xs text-slate-500 mt-1">Export valuation ledgers and review ABC inventory turnover classifications.</p>
        </div>
        <button onclick="exportCSV()" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow">Download CSV</button>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 class="text-sm font-bold text-slate-800 mb-4">Inventory Valuation by SKU</h2>
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
            <tr>
              <th class="py-2.5 px-3">SKU</th>
              <th class="py-2.5 px-3">Product</th>
              <th class="py-2.5 px-3">On-Hand</th>
              <th class="py-2.5 px-3">Unit Cost</th>
              <th class="py-2.5 px-3">Total Value</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${state.products.map(p => `
              <tr>
                <td class="py-2.5 px-3 font-mono font-bold text-slate-800">${p.sku}</td>
                <td class="py-2.5 px-3">${p.name}</td>
                <td class="py-2.5 px-3 font-bold">${p.total_on_hand} ${p.uom}</td>
                <td class="py-2.5 px-3 font-mono">$${p.unit_cost.toFixed(2)}</td>
                <td class="py-2.5 px-3 font-mono font-bold text-purple-700">$${(p.total_on_hand * p.unit_cost).toFixed(2)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// --- 20. ROLES & AUDIT (Features 13 & 15) ---
function renderRoles() {
  return `
    <div class="space-y-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">Role-Based Access Control (RBAC)</h1>
        <p class="text-xs text-slate-500 mt-1">Define permissions across Administrators, Inventory Managers, and Warehouse Staff.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div class="font-bold text-purple-700 text-sm">👑 Administrator</div>
          <div class="text-[11px] text-slate-500 mt-1">Full control over catalogs, users, settings, and blockchain integrity audit.</div>
        </div>
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div class="font-bold text-indigo-700 text-sm">📦 Inventory Manager</div>
          <div class="text-[11px] text-slate-500 mt-1">Manages PO receipts, sales orders, replenishment rules, and AI forecasts.</div>
        </div>
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div class="font-bold text-slate-700 text-sm">👷 Warehouse Staff</div>
          <div class="text-[11px] text-slate-500 mt-1">Executes internal moves, picking, packing, shelving, and cycle counts.</div>
        </div>
      </div>
    </div>
  `;
}

function renderAudit() {
  return `
    <div class="space-y-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">Activity Audit Trail</h1>
        <p class="text-xs text-slate-500 mt-1">Timestamped log of administrative actions, receipts, shipments, and adjustments.</p>
      </div>
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm p-4 text-xs text-slate-600">
        All activity logs are cryptographically sealed into the StockMove ledger and Trust Chain blocks.
      </div>
    </div>
  `;
}

function renderWarehouses() {
  return `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Warehouses & Locations</h1>
          <p class="text-xs text-slate-500 mt-1">Multi-warehouse configuration and physical storage hierarchy (Zones, Aisles, Racks, Shelves).</p>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        ${state.warehouses.map(w => `
          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <div class="flex justify-between items-center">
              <span class="font-bold text-slate-800 text-base">${w.name}</span>
              <span class="px-2 py-0.5 rounded bg-purple-100 text-purple-700 font-mono text-xs font-bold">${w.code}</span>
            </div>
            <div class="text-xs text-slate-500">${w.address}</div>
            <div class="border-t border-slate-100 pt-3">
              <div class="text-xs font-semibold text-slate-700 mb-2">Locations / Racks:</div>
              <div class="space-y-1.5">
                ${(w.locations || []).map(loc => `
                  <div class="flex items-center justify-between p-2 rounded bg-slate-50 text-xs">
                    <div>
                      <div class="font-medium text-slate-800">${loc.name}</div>
                      <div class="text-[10px] text-slate-400 font-mono">${loc.code} (${loc.zone || 'Zone A'})</div>
                    </div>
                    <button onclick="viewLocationQR(${loc.id})" class="px-2 py-1 bg-white border border-slate-200 rounded text-[10px] text-slate-600 hover:bg-slate-100">QR</button>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

// --- MODALS & ACTIONS ---
function openModal(name) {
  state.modal = name;
  render();
}

function closeModal() {
  state.modal = null;
  render();
}

function renderModal() {
  if (!state.modal) return "";
  if (state.modal === "new_receipt") {
    return `
      <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
          <div class="flex items-center justify-between border-b pb-3">
            <h3 class="text-base font-bold text-slate-800">Create Incoming Receipt</h3>
            <button onclick="closeModal()" class="text-slate-400 hover:text-slate-600">✕</button>
          </div>
          <div class="space-y-3 text-xs">
            <div>
              <label class="block font-semibold mb-1 text-slate-700">Supplier Name</label>
              <input type="text" id="receipt-supplier" value="Apex Foundry Ltd" class="w-full border rounded px-3 py-2" />
            </div>
            <div>
              <label class="block font-semibold mb-1 text-slate-700">Product</label>
              <select id="receipt-prod" class="w-full border rounded px-3 py-2">
                ${state.products.map(p => `<option value="${p.id}">${p.name} (${p.sku})</option>`).join("")}
              </select>
            </div>
            <div>
              <label class="block font-semibold mb-1 text-slate-700">Quantity to Receive</label>
              <input type="number" id="receipt-qty" value="50" class="w-full border rounded px-3 py-2" />
            </div>
          </div>
          <div class="flex justify-end gap-2 pt-2 border-t">
            <button onclick="closeModal()" class="px-4 py-2 border rounded text-xs">Cancel</button>
            <button onclick="submitReceipt()" class="px-4 py-2 bg-purple-600 text-white rounded text-xs font-bold">Create Receipt</button>
          </div>
        </div>
      </div>
    `;
  }
  if (state.modal === "new_transfer") {
    return `
      <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
          <div class="flex items-center justify-between border-b pb-3">
            <h3 class="text-base font-bold text-slate-800">Create Internal Transfer</h3>
            <button onclick="closeModal()" class="text-slate-400 hover:text-slate-600">✕</button>
          </div>
          <div class="space-y-3 text-xs">
            <div>
              <label class="block font-semibold mb-1 text-slate-700">Product</label>
              <select id="trans-prod" class="w-full border rounded px-3 py-2">
                ${state.products.map(p => `<option value="${p.id}">${p.name} (${p.sku})</option>`).join("")}
              </select>
            </div>
            <div>
              <label class="block font-semibold mb-1 text-slate-700">Quantity</label>
              <input type="number" id="trans-qty" value="10" class="w-full border rounded px-3 py-2" />
            </div>
          </div>
          <div class="flex justify-end gap-2 pt-2 border-t">
            <button onclick="closeModal()" class="px-4 py-2 border rounded text-xs">Cancel</button>
            <button onclick="submitTransfer()" class="px-4 py-2 bg-purple-600 text-white rounded text-xs font-bold">Create Transfer</button>
          </div>
        </div>
      </div>
    `;
  }
  return "";
}

// Action Dispatchers
async function validateReceipt(id) {
  try {
    await api(`/receipts/${id}/validate`, { method: "POST" });
    showToast("Receipt validated! Stock increased in ledger.");
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function validateDelivery(id) {
  try {
    await api(`/deliveries/${id}/validate`, { method: "POST" });
    showToast("Delivery validated! Stock decreased in ledger.");
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function pickDelivery(id) {
  try {
    await api(`/deliveries/${id}/pick`, { method: "POST" });
    showToast("Items marked as picked");
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function packDelivery(id) {
  try {
    await api(`/deliveries/${id}/pack`, { method: "POST" });
    showToast("Items marked as packed");
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function validateTransfer(id) {
  try {
    await api(`/transfers/${id}/validate`, { method: "POST" });
    showToast("Internal transfer validated! Stock location updated.");
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function validateAdjustment(id) {
  try {
    await api(`/adjustments/${id}/validate`, { method: "POST" });
    showToast("Stock adjustment confirmed and logged to scrap.");
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function submitReceipt() {
  const supplier = document.getElementById("receipt-supplier").value;
  const prodId = parseInt(document.getElementById("receipt-prod").value);
  const qty = parseFloat(document.getElementById("receipt-qty").value);
  const destLocId = state.warehouses[0]?.locations[0]?.id || 1;

  try {
    await api("/receipts", {
      method: "POST",
      body: JSON.stringify({
        supplier_name: supplier,
        destination_location_id: destLocId,
        lines: [{ product_id: prodId, quantity_expected: qty, unit_cost: 15.0 }]
      })
    });
    showToast("Receipt created!");
    closeModal();
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function submitTransfer() {
  const prodId = parseInt(document.getElementById("trans-prod").value);
  const qty = parseFloat(document.getElementById("trans-qty").value);
  const locs = state.warehouses[0]?.locations || [];
  if (locs.length < 2) { showToast("Need at least 2 locations for transfer", "error"); return; }

  try {
    await api("/transfers", {
      method: "POST",
      body: JSON.stringify({
        source_location_id: locs[0].id,
        destination_location_id: locs[1].id,
        lines: [{ product_id: prodId, quantity: qty }]
      })
    });
    showToast("Transfer created!");
    closeModal();
    await loadInitialData();
    render();
  } catch (err) { showToast(err.message, "error"); }
}

async function viewProductQR(prodId) {
  try {
    const data = await api(`/qr/product/${prodId}`);
    const area = document.getElementById("qr-preview-area");
    if (area) {
      area.innerHTML = `
        <img src="${data.qr_code_data_uri}" class="w-36 h-36 border p-1 rounded-lg bg-white shadow-sm mb-3" />
        <div class="font-bold text-slate-800 text-xs">${data.sku}</div>
        <div class="text-[10px] text-slate-500">Scan to view live stock & initiate moves</div>
      `;
    }
  } catch (err) { showToast(err.message, "error"); }
}

async function simulateScan(code) {
  if (!code) return;
  try {
    const data = await api("/qr/scan", {
      method: "POST",
      body: JSON.stringify({ raw_payload: code })
    });
    const area = document.getElementById("scan-result-area");
    if (area) {
      if (data.status === "RESOLVED") {
        area.innerHTML = `
          <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800">
            <div class="font-bold">✓ Match Found: ${data.data.name || data.data.code}</div>
            <div class="text-[11px] mt-1">Type: ${data.entity_type} | On Hand: ${data.data.current_stock || 'N/A'}</div>
            <div class="text-[10px] text-emerald-600 mt-2">Actions: ${data.available_actions?.join(", ")}</div>
          </div>
        `;
      } else {
        area.innerHTML = `<div class="p-3 bg-red-50 text-red-600 rounded">No entity matched barcode '${code}'</div>`;
      }
    }
  } catch (err) { showToast(err.message, "error"); }
}

async function runWhatIfSim() {
  const prodId = parseInt(document.getElementById("whatif-prod")?.value || state.selectedProductId);
  const surge = parseFloat(document.getElementById("whatif-surge")?.value || 35);
  const delay = parseInt(document.getElementById("whatif-delay")?.value || 7);
  try {
    const data = await api("/intelligence/what-if", {
      method: "POST",
      body: JSON.stringify({
        product_id: prodId,
        demand_surge_pct: surge,
        supplier_delay_days: delay
      })
    });
    state.whatIfResult = data;
    render();
    showToast("What-if simulation executed!");
  } catch (err) { showToast(err.message, "error"); }
}

async function scanForLowStock() {
  try {
    const res = await api("/alerts/scan", { method: "POST" });
    showToast(res.message);
    const alerts = await api("/alerts");
    state.alerts = alerts;
    render();
  } catch (err) { showToast(err.message, "error"); }
}

function exportCSV() {
  window.open(`${API_BASE}/reports/export/csv`, "_blank");
}

function handleSearch(q) {
  const dd = document.getElementById("search-dropdown");
  if (!q.trim()) { dd.classList.add("hidden"); return; }
  api(`/search?q=${encodeURIComponent(q)}`).then(res => {
    dd.classList.remove("hidden");
    if (res.total_matches === 0) {
      dd.innerHTML = `<div class="p-2 text-slate-400 text-xs">No matching items</div>`;
      return;
    }
    dd.innerHTML = `
      <div class="space-y-1">
        ${(res.products || []).map(p => `
          <div onclick="state.selectedProductId = ${p.id}; setTab('products');" class="p-2 hover:bg-purple-50 rounded cursor-pointer text-xs flex justify-between items-center">
            <div>
              <div class="font-bold text-slate-800">${p.name}</div>
              <div class="text-[10px] text-slate-400">${p.sku}</div>
            </div>
            <span class="font-mono text-xs font-bold text-purple-700">${p.on_hand} ${p.uom}</span>
          </div>
        `).join("")}
      </div>
    `;
  }).catch(() => {});
}

async function askCopilot(msg) {
  state.chatMessages.push({ role: "user", content: msg });
  render();
  try {
    const res = await api("/showcase/ai-assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message: msg })
    });
    state.chatMessages.push({ role: "assistant", content: res.response_text });
    render();
    const chatContainer = document.getElementById("chat-messages");
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
  } catch (err) {
    state.chatMessages.push({ role: "assistant", content: "Error contacting AI Copilot engine: " + err.message });
    render();
  }
}

function sendCopilotMessage() {
  const input = document.getElementById("copilot-input");
  if (!input || !input.value.trim()) return;
  const msg = input.value.trim();
  input.value = "";
  askCopilot(msg);
}

// Initial Boot
document.addEventListener("DOMContentLoaded", () => {
  loadInitialData().then(() => render());
});
