const API_BASE = '/api/v1';

const api = {
  // Helper
  async request(endpoint, options = {}) {
    const defaultHeaders = {
      'Content-Type': 'application/json',
    };
    const token = localStorage.getItem('stocksense_token');
    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`;
    }
    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };
    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || 'API Request failed');
    }
    return response.json();
  },

  // Auth
  login: (data) => api.request('/auth/login', { method: 'POST', body: data }),
  getMe: () => api.request('/auth/me'),

  // Master Data
  getProducts: (params = '') => api.request(`/products${params}`),
  getCategories: () => api.request('/categories'),
  getWarehouses: () => api.request('/warehouses'),
  getLocations: (whId = '') => api.request(`/locations${whId ? `?warehouse_id=${whId}` : ''}`),
  search: (q) => api.request(`/search?q=${encodeURIComponent(q)}`),

  // Operations
  getReceipts: (params = '') => api.request(`/receipts${params}`),
  createReceipt: (data) => api.request('/receipts', { method: 'POST', body: data }),
  validateReceipt: (id) => api.request(`/receipts/${id}/validate`, { method: 'POST' }),

  getDeliveries: (params = '') => api.request(`/deliveries${params}`),
  createDelivery: (data) => api.request('/deliveries', { method: 'POST', body: data }),
  validateDelivery: (id) => api.request(`/deliveries/${id}/validate`, { method: 'POST' }),

  getTransfers: () => api.request('/transfers'),
  createTransfer: (data) => api.request('/transfers', { method: 'POST', body: data }),
  validateTransfer: (id) => api.request(`/transfers/${id}/validate`, { method: 'POST' }),

  getAdjustments: () => api.request('/adjustments'),
  createAdjustment: (data) => api.request('/adjustments', { method: 'POST', body: data }),
  validateAdjustment: (id) => api.request(`/adjustments/${id}/validate`, { method: 'POST' }),

  // Dashboard & Governance
  getDashboardSummary: (whId = '') => api.request(`/dashboard/summary${whId ? `?warehouse_id=${whId}` : ''}`),
  getLedger: (params = '') => api.request(`/ledger${params}`),
  getTrustChainBlocks: () => api.request('/trust-chain/blocks'),
  verifyTrustChain: () => api.request('/trust-chain/verify'),
  getAlerts: () => api.request('/alerts'),
  getValuationReport: () => api.request('/reports/valuation'),

  // AI Intelligence
  getForecast: (productId, daysAhead = 30) => api.request('/intelligence/forecast', {
    method: 'POST', body: { product_id: productId, days_ahead: daysAhead }
  }),
  getReorderRecommendations: () => api.request('/intelligence/reorder'),
  getAnomalies: () => api.request('/intelligence/anomalies'),
  getCauseOfLoss: () => api.request('/intelligence/cause-of-loss'),
  runWhatIf: (data) => api.request('/intelligence/what-if', { method: 'POST', body: data }),
  getImpactScore: (params) => api.request(`/intelligence/impact?${new URLSearchParams(params).toString()}`),

  // 5 New Advanced Features
  // 1. Dead Stock Rescue
  getDeadStock: (whId = '') => api.request(`/advanced/dead-stock${whId ? `?warehouse_id=${whId}` : ''}`),
  confirmDeadStockAction: (data) => api.request('/advanced/dead-stock/confirm-action', { method: 'POST', body: data }),

  // 2. Supplier Intelligence
  getSuppliersComparison: () => api.request('/advanced/suppliers'),
  getSupplierMetrics: (supplierId) => api.request(`/advanced/suppliers/${supplierId}`),

  // 3. Expiry / FEFO
  getBatches: (params = '') => api.request(`/advanced/expiry/batches${params}`),
  getExpiryAlerts: (days = 30) => api.request(`/advanced/expiry/alerts?days_threshold=${days}`),
  getFefoPlan: (productId, warehouseId, qty) => api.request(
    `/advanced/fefo/plan?product_id=${productId}&warehouse_id=${warehouseId}&requested_qty=${qty}`
  ),

  // 4. Smart Picking Route
  getPickingRoute: (deliveryId) => api.request(`/advanced/picking-route/${deliveryId}`),
  confirmRoutePickStep: (deliveryId, data) => api.request(
    `/advanced/picking-route/${deliveryId}/confirm-step`, { method: 'POST', body: data }
  ),

  // Showcase: Digital Twin & Assistant
  getDigitalTwin: (whId, routeId = null) => api.request(
    `/digital-twin/warehouse/${whId}${routeId ? `?route_id=${routeId}` : ''}`
  ),
  askAssistant: (message) => api.request('/assistant/chat', { method: 'POST', body: { message } })
};
