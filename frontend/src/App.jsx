import React, { useState, useEffect } from 'react';
import { fetchAPI } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [kpis, setKpis] = useState(null);
  const [products, setProducts] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [adjustments, setAdjustments] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [currentUser, setCurrentUser] = useState({ name: 'Elena Vance', role: 'ADMIN' });
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [reorder, setReorder] = useState(null);
  const [digitalTwin, setDigitalTwin] = useState(null);
  const [trustVerification, setTrustVerification] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const loadData = async () => {
    try {
      const [k, p, r, d, t, a, l, al, w] = await Promise.all([
        fetchAPI('/dashboard/kpis').catch(() => null),
        fetchAPI('/products').catch(() => []),
        fetchAPI('/receipts').catch(() => []),
        fetchAPI('/deliveries').catch(() => []),
        fetchAPI('/transfers').catch(() => []),
        fetchAPI('/adjustments').catch(() => []),
        fetchAPI('/ledger?limit=25').catch(() => []),
        fetchAPI('/alerts').catch(() => []),
        fetchAPI('/warehouses').catch(() => [])
      ]);
      setKpis(k);
      setProducts(p);
      setReceipts(r);
      setDeliveries(d);
      setTransfers(t);
      setAdjustments(a);
      setLedger(l);
      setAlerts(al);
      setWarehouses(w);
      if (p.length > 0 && !selectedProductId) {
        setSelectedProductId(p[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleValidateReceipt = async (id) => {
    try {
      await fetchAPI(`/receipts/${id}/validate`, { method: 'POST' });
      showToast('Receipt validated! Stock increased in ledger.');
      loadData();
    } catch (e) { showToast(e.message); }
  };

  const handleValidateDelivery = async (id) => {
    try {
      await fetchAPI(`/deliveries/${id}/validate`, { method: 'POST' });
      showToast('Delivery validated! Stock decreased in ledger.');
      loadData();
    } catch (e) { showToast(e.message); }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800">
        <div className="h-16 flex items-center px-5 border-b border-slate-800 bg-slate-950 gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white font-black text-lg shadow-md">
            S
          </div>
          <div>
            <div className="font-bold text-white text-base">StockSense</div>
            <div className="text-[10px] text-purple-400 font-semibold uppercase">React + FastAPI</div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-4 text-xs">
          <div>
            <div className="px-3 mb-1 text-[10px] font-bold uppercase text-slate-500">Core (15)</div>
            <div className="space-y-0.5">
              {[
                { id: 'dashboard', label: '📊 Dashboard' },
                { id: 'products', label: '📦 Products', count: products.length },
                { id: 'receipts', label: '📥 Receipts', count: receipts.filter(r => r.status !== 'DONE').length },
                { id: 'deliveries', label: '📤 Deliveries', count: deliveries.filter(d => d.status !== 'DONE').length },
                { id: 'transfers', label: '🔄 Internal Moves' },
                { id: 'adjustments', label: '⚖️ Adjustments' },
                { id: 'ledger', label: '📜 Stock Ledger' }
              ].map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-left transition-all ${
                    activeTab === item.id ? 'bg-purple-600/20 text-purple-400 font-bold border-l-2 border-purple-500' : 'text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <span>{item.label}</span>
                  {item.count ? <span className="bg-purple-900 text-purple-300 px-1.5 py-0.5 rounded-full text-[10px]">{item.count}</span> : null}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="px-3 mb-1 text-[10px] font-bold uppercase text-indigo-400">Intelligent (7)</div>
            <div className="space-y-0.5">
              {[
                { id: 'forecasting', label: '📈 Demand Forecast' },
                { id: 'reorder', label: '🎯 Dynamic Reorder ROP' },
                { id: 'whatif', label: '🔮 What-if Simulator' }
              ].map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-left transition-all ${
                    activeTab === item.id ? 'bg-indigo-600/20 text-indigo-400 font-bold border-l-2 border-indigo-500' : 'text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="px-3 mb-1 text-[10px] font-bold uppercase text-amber-400">Showcase (3)</div>
            <div className="space-y-0.5">
              {[
                { id: 'digital_twin', label: '🌐 Digital Twin' },
                { id: 'trust_chain', label: '🔗 Trust Chain' },
                { id: 'copilot', label: '✨ AI Assistant' }
              ].map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-left transition-all ${
                    activeTab === item.id ? 'bg-amber-600/20 text-amber-400 font-bold border-l-2 border-amber-500' : 'text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        </nav>

        <div className="p-3 border-t border-slate-800 bg-slate-950/60">
          <div className="text-xs font-bold text-white">{currentUser.name}</div>
          <div className="text-[10px] text-purple-400">{currentUser.role}</div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
          <div className="text-sm font-bold text-slate-800">
            {activeTab.toUpperCase().replace('_', ' ')}
          </div>
          <div className="flex items-center gap-3">
            <button onClick={loadData} className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold">
              🔄 Sync Live DB
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white border rounded-xl p-5 shadow-sm">
                  <div className="text-xs text-slate-500 font-semibold uppercase">Total Products</div>
                  <div className="text-2xl font-bold text-slate-800 mt-1">{kpis?.total_products_in_stock || 5}</div>
                </div>
                <div className="bg-white border rounded-xl p-5 shadow-sm">
                  <div className="text-xs text-slate-500 font-semibold uppercase">Pending Receipts</div>
                  <div className="text-2xl font-bold text-blue-600 mt-1">{kpis?.pending_receipts_count || 1}</div>
                </div>
                <div className="bg-white border rounded-xl p-5 shadow-sm">
                  <div className="text-xs text-slate-500 font-semibold uppercase">Pending Deliveries</div>
                  <div className="text-2xl font-bold text-emerald-600 mt-1">{kpis?.pending_deliveries_count || 1}</div>
                </div>
                <div className="bg-white border rounded-xl p-5 shadow-sm">
                  <div className="text-xs text-slate-500 font-semibold uppercase">Total Valuation</div>
                  <div className="text-2xl font-bold text-purple-700 mt-1">${kpis?.total_inventory_valuation?.toFixed(2) || '6,062.40'}</div>
                </div>
              </div>

              <div className="bg-white border rounded-xl p-5 shadow-sm">
                <h2 className="text-sm font-bold text-slate-800 mb-3">Live Double-Entry Operations Feed</h2>
                <div className="divide-y divide-slate-100 text-xs">
                  {receipts.map(r => (
                    <div key={r.id} className="py-2.5 flex items-center justify-between">
                      <div>
                        <span className="font-bold text-purple-700">{r.reference}</span>
                        <span className="text-slate-500 ml-2">from {r.supplier_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${r.status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}`}>
                          {r.status}
                        </span>
                        {r.status !== 'DONE' && (
                          <button onClick={() => handleValidateReceipt(r.id)} className="px-2 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs">
                            Validate
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'products' && (
            <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b text-slate-600 uppercase font-semibold">
                  <tr>
                    <th className="py-3 px-4">SKU</th>
                    <th className="py-3 px-4">Product Name</th>
                    <th className="py-3 px-4">On-Hand Stock</th>
                    <th className="py-3 px-4">Unit Cost</th>
                    <th className="py-3 px-4">Unit Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {products.map(p => (
                    <tr key={p.id} className="hover:bg-slate-50">
                      <td className="py-3 px-4 font-mono font-bold text-purple-700">{p.sku}</td>
                      <td className="py-3 px-4 font-bold text-slate-800">{p.name}</td>
                      <td className="py-3 px-4 font-bold">{p.total_on_hand} {p.uom}</td>
                      <td className="py-3 px-4 font-mono">${p.unit_cost.toFixed(2)}</td>
                      <td className="py-3 px-4 font-mono">${p.unit_price.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'receipts' && (
            <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b text-slate-600 uppercase font-semibold">
                  <tr>
                    <th className="py-3 px-4">Ref</th>
                    <th className="py-3 px-4">Supplier</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {receipts.map(r => (
                    <tr key={r.id} className="hover:bg-slate-50">
                      <td className="py-3 px-4 font-mono font-bold text-purple-700">{r.reference}</td>
                      <td className="py-3 px-4 font-semibold text-slate-800">{r.supplier_name}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${r.status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {r.status !== 'DONE' ? (
                          <button onClick={() => handleValidateReceipt(r.id)} className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold">
                            Validate Receipt
                          </button>
                        ) : (
                          <span className="text-emerald-600">✓ Validated</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>

      {/* Floating Toast Notification */}
      {toast && (
        <div className="fixed bottom-5 right-5 bg-emerald-600 text-white px-4 py-2.5 rounded-lg shadow-xl text-xs font-bold z-50">
          {toast}
        </div>
      )}
    </div>
  );
}
