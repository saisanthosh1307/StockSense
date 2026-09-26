import { lazy, Suspense, useMemo, useState, type FormEvent } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowDownRight,
  ArrowLeftRight,
  ArrowUpRight,
  Bell,
  Boxes,
  Check,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Clock3,
  Download,
  FileClock,
  FilePlus2,
  Filter,
  LayoutDashboard,
  LogOut,
  MapPin,
  MoreHorizontal,
  Package,
  PackageCheck,
  PackagePlus,
  PackageSearch,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Truck,
  X,
  type LucideIcon,
} from "lucide-react";
import AuthPage, { type AuthenticatedUser } from "./AuthPage";
import "./StockSense.css";

const StockMovementChart = lazy(() => import("./StockMovementChart"));

type Product = {
  name: string;
  sku: string;
  category: string;
  warehouse: string;
  location: string;
  quantity: number;
  reorderPoint: number;
  unit: string;
  unitCost: number;
  color: string;
};

type Movement = {
  id: number;
  product: string;
  sku: string;
  type: "Receipt" | "Delivery" | "Transfer" | "Adjustment";
  quantity: number;
  warehouse: string;
  reference: string;
  date: string;
  user: string;
  reason?: string;
};

type View =
  | "Dashboard"
  | "Inventory"
  | "Movements"
  | "Receipts"
  | "Transfers"
  | "Reports";
type MovementKind = Movement["type"];

const warehouses = ["North warehouse", "Central depot", "Harbor storage"];

const initialProducts: Product[] = [
  {
    name: "Steel sheet · 304L",
    sku: "STL-304-01",
    category: "Raw materials",
    warehouse: "North warehouse",
    location: "Rack A-12",
    quantity: 142,
    reorderPoint: 80,
    unit: "sheets",
    unitCost: 32.5,
    color: "green",
  },
  {
    name: "Filter cartridge F-120",
    sku: "FLT-120-04",
    category: "Components",
    warehouse: "Central depot",
    location: "Bin C-08",
    quantity: 18,
    reorderPoint: 24,
    unit: "units",
    unitCost: 18.75,
    color: "blue",
  },
  {
    name: "Safety gloves · size 9",
    sku: "PPE-GLV-09",
    category: "Safety",
    warehouse: "North warehouse",
    location: "Rack D-03",
    quantity: 4,
    reorderPoint: 20,
    unit: "pairs",
    unitCost: 6.2,
    color: "orange",
  },
  {
    name: "Hydraulic oil · 20L",
    sku: "OIL-HYD-20",
    category: "Consumables",
    warehouse: "Harbor storage",
    location: "Pallet H-14",
    quantity: 0,
    reorderPoint: 12,
    unit: "drums",
    unitCost: 54,
    color: "red",
  },
  {
    name: "Hex bolt M12 × 40",
    sku: "BLT-M12-40",
    category: "Fasteners",
    warehouse: "Central depot",
    location: "Bin B-21",
    quantity: 980,
    reorderPoint: 250,
    unit: "units",
    unitCost: 0.18,
    color: "purple",
  },
  {
    name: "Copper wire · 2.5mm",
    sku: "WIR-CU-25",
    category: "Raw materials",
    warehouse: "Harbor storage",
    location: "Reel R-02",
    quantity: 67,
    reorderPoint: 30,
    unit: "reels",
    unitCost: 42,
    color: "amber",
  },
  {
    name: "Bearing 6204-ZZ",
    sku: "BRG-6204-ZZ",
    category: "Components",
    warehouse: "North warehouse",
    location: "Bin A-07",
    quantity: 31,
    reorderPoint: 18,
    unit: "units",
    unitCost: 12.4,
    color: "teal",
  },
  {
    name: "Packaging carton · L",
    sku: "PKG-CTN-L",
    category: "Packaging",
    warehouse: "Central depot",
    location: "Pallet P-04",
    quantity: 215,
    reorderPoint: 100,
    unit: "units",
    unitCost: 1.15,
    color: "slate",
  },
];

const initialMovements: Movement[] = [
  {
    id: 1,
    product: "Steel sheet · 304L",
    sku: "STL-304-01",
    type: "Receipt",
    quantity: 48,
    warehouse: "North warehouse",
    reference: "REC-2025-0842",
    date: "Today, 10:42 AM",
    user: "Olivia Chen",
  },
  {
    id: 2,
    product: "Filter cartridge F-120",
    sku: "FLT-120-04",
    type: "Delivery",
    quantity: -12,
    warehouse: "Central depot",
    reference: "DO-2025-0318",
    date: "Today, 9:18 AM",
    user: "Marcus Lee",
  },
  {
    id: 3,
    product: "Copper wire · 2.5mm",
    sku: "WIR-CU-25",
    type: "Transfer",
    quantity: 20,
    warehouse: "Harbor storage",
    reference: "TRF-2025-0119",
    date: "Yesterday, 4:36 PM",
    user: "Olivia Chen",
  },
  {
    id: 4,
    product: "Safety gloves · size 9",
    sku: "PPE-GLV-09",
    type: "Adjustment",
    quantity: -2,
    warehouse: "North warehouse",
    reference: "ADJ-2025-0056",
    date: "Yesterday, 2:05 PM",
    user: "Priya Shah",
  },
  {
    id: 5,
    product: "Hex bolt M12 × 40",
    sku: "BLT-M12-40",
    type: "Receipt",
    quantity: 400,
    warehouse: "Central depot",
    reference: "REC-2025-0841",
    date: "Sep 23, 11:22 AM",
    user: "Marcus Lee",
  },
];

const movementChart = [
  { date: "Mon", received: 72, shipped: 48 },
  { date: "Tue", received: 95, shipped: 66 },
  { date: "Wed", received: 61, shipped: 88 },
  { date: "Thu", received: 126, shipped: 72 },
  { date: "Fri", received: 84, shipped: 104 },
  { date: "Sat", received: 54, shipped: 42 },
  { date: "Sun", received: 106, shipped: 64 },
];

const monthChart = [
  { date: "Week 1", received: 420, shipped: 368 },
  { date: "Week 2", received: 516, shipped: 442 },
  { date: "Week 3", received: 388, shipped: 501 },
  { date: "Week 4", received: 624, shipped: 477 },
];

const navigation: { label: View; icon: LucideIcon; badge?: string }[] = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Inventory", icon: Boxes, badge: "8" },
  { label: "Movements", icon: ArrowLeftRight },
  { label: "Receipts", icon: PackagePlus, badge: "8" },
  { label: "Transfers", icon: Truck },
  { label: "Reports", icon: Activity },
];

const getStatus = (product: Product) => {
  if (product.quantity === 0) return "Out of stock";
  if (product.quantity <= product.reorderPoint) return "Low stock";
  return "In stock";
};

const money = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);

function StockSense() {
  const [authenticatedUser, setAuthenticatedUser] =
    useState<AuthenticatedUser | null>(null);
  const [activeView, setActiveView] = useState<View>("Dashboard");
  const [products, setProducts] = useState(initialProducts);
  const [movements, setMovements] = useState(initialMovements);
  const [warehouse, setWarehouse] = useState("All warehouses");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All categories");
  const [statusFilter, setStatusFilter] = useState("All items");
  const [chartPeriod, setChartPeriod] = useState("7 days");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [movementKind, setMovementKind] = useState<MovementKind>("Receipt");
  const [selectedProduct, setSelectedProduct] = useState("");
  const [quantity, setQuantity] = useState("");
  const [movementWarehouse, setMovementWarehouse] = useState(warehouses[0]);
  const [destination, setDestination] = useState(warehouses[1]);
  const [reason, setReason] = useState("");
  const [adjustmentDirection, setAdjustmentDirection] = useState<
    "Increase" | "Decrease"
  >("Decrease");
  const [formError, setFormError] = useState("");
  const [toast, setToast] = useState("");
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Product | null>(null);

  const visibleProducts = useMemo(
    () =>
      products.filter((product) => {
        const matchesWarehouse =
          warehouse === "All warehouses" || product.warehouse === warehouse;
        const matchesSearch = `${product.name} ${product.sku}`
          .toLowerCase()
          .includes(search.toLowerCase());
        const matchesCategory =
          category === "All categories" || product.category === category;
        const status = getStatus(product);
        const matchesStatus =
          statusFilter === "All items" ||
          (statusFilter === "Low stock" && status !== "In stock") ||
          status === statusFilter;
        return (
          matchesWarehouse && matchesSearch && matchesCategory && matchesStatus
        );
      }),
    [products, warehouse, search, category, statusFilter],
  );

  const scopedProducts = products.filter(
    (product) =>
      warehouse === "All warehouses" || product.warehouse === warehouse,
  );
  const totalUnits = scopedProducts.reduce(
    (sum, product) => sum + product.quantity,
    0,
  );
  const stockValue = scopedProducts.reduce(
    (sum, product) => sum + product.quantity * product.unitCost,
    0,
  );
  const lowStockCount = scopedProducts.filter(
    (product) => getStatus(product) !== "In stock",
  ).length;
  const lowStockProducts = scopedProducts
    .filter((product) => getStatus(product) !== "In stock")
    .slice(0, 4);
  const selectedTitle =
    activeView === "Dashboard"
      ? `Good morning, ${authenticatedUser?.name.split(" ")[0] ?? "Olivia"}`
      : activeView;
  const chartData = chartPeriod === "7 days" ? movementChart : monthChart;
  const transferDestination =
    destination !== movementWarehouse
      ? destination
      : (warehouses.find((item) => item !== movementWarehouse) ??
        movementWarehouse);

  const openMovement = (
    kind: MovementKind = "Receipt",
    productSku?: string,
  ) => {
    const firstProduct =
      products.find((product) => product.sku === productSku) ?? products[0];
    setMovementKind(kind);
    setSelectedProduct(firstProduct?.sku ?? "");
    setQuantity("");
    const sourceWarehouse =
      kind === "Receipt"
        ? warehouse === "All warehouses"
          ? (firstProduct?.warehouse ?? warehouses[0])
          : warehouse
        : (firstProduct?.warehouse ?? warehouses[0]);
    setMovementWarehouse(sourceWarehouse);
    setDestination(
      warehouses.find((item) => item !== sourceWarehouse) ?? warehouses[1],
    );
    setReason("");
    setFormError("");
    setDialogOpen(true);
  };

  const chooseMovementKind = (kind: MovementKind) => {
    setMovementKind(kind);
    setFormError("");
    const product = products.find((item) => item.sku === selectedProduct);
    if (kind !== "Receipt" && product) {
      setMovementWarehouse(product.warehouse);
    }
  };

  const chooseMovementProduct = (sku: string) => {
    setSelectedProduct(sku);
    const product = products.find((item) => item.sku === sku);
    if (product) {
      setMovementWarehouse(product.warehouse);
    }
  };

  const submitMovement = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const product = products.find((item) => item.sku === selectedProduct);
    const amount = Number(quantity);
    if (!product || !Number.isFinite(amount) || amount <= 0) {
      setFormError("Choose a product and enter a quantity greater than zero.");
      return;
    }
    if (movementKind === "Adjustment" && !reason.trim()) {
      setFormError("Add a reason for this stock adjustment.");
      return;
    }
    if (movementKind === "Delivery" && product.quantity < amount) {
      setFormError(
        `Only ${product.quantity} ${product.unit} are available for this delivery.`,
      );
      return;
    }
    if (movementKind === "Transfer" && product.quantity < amount) {
      setFormError(
        `Only ${product.quantity} ${product.unit} are available to transfer.`,
      );
      return;
    }
    if (
      movementKind === "Adjustment" &&
      adjustmentDirection === "Decrease" &&
      product.quantity < amount
    ) {
      setFormError(
        `The count cannot reduce stock below zero. Current stock is ${product.quantity} ${product.unit}.`,
      );
      return;
    }
    if (movementKind !== "Receipt" && product.warehouse !== movementWarehouse) {
      setFormError(
        `${product.name} is currently stored at ${product.warehouse}.`,
      );
      return;
    }

    const reference = `${movementKind === "Receipt" ? "REC" : movementKind === "Delivery" ? "DO" : movementKind === "Transfer" ? "TRF" : "ADJ"}-${new Date().getFullYear()}-${String(Date.now()).slice(-4)}`;
    const signedQuantity =
      movementKind === "Delivery"
        ? -amount
        : movementKind === "Adjustment" && adjustmentDirection === "Decrease"
          ? -amount
          : amount;
    setProducts((current) =>
      current.map((item) =>
        item.sku !== product.sku
          ? item
          : {
              ...item,
              quantity:
                movementKind === "Transfer"
                  ? item.quantity
                  : Math.max(0, item.quantity + signedQuantity),
              warehouse:
                movementKind === "Transfer"
                  ? transferDestination
                  : movementWarehouse,
            },
      ),
    );

    const movement: Movement = {
      id: Date.now(),
      product: product.name,
      sku: product.sku,
      type: movementKind,
      quantity: signedQuantity,
      warehouse:
        movementKind === "Transfer" ? transferDestination : movementWarehouse,
      reference,
      date: "Just now",
      user: authenticatedUser?.name ?? "Olivia Chen",
      reason: movementKind === "Adjustment" ? reason.trim() : undefined,
    };
    setMovements((current) => [
      movement,
      ...(movementKind === "Transfer"
        ? [
            {
              ...movement,
              id: Date.now() + 1,
              quantity: -amount,
              warehouse: product.warehouse,
            },
          ]
        : []),
      ...current,
    ]);
    setDialogOpen(false);
    setToast(`${movementKind} recorded successfully`);
    window.setTimeout(() => setToast(""), 3000);
  };

  const exportMovements = () => {
    const rows = [
      [
        "Date",
        "Product",
        "SKU",
        "Type",
        "Quantity",
        "Warehouse",
        "Reference",
        "User",
        "Reason",
      ],
      ...movements.map((item) => [
        item.date,
        item.product,
        item.sku,
        item.type,
        String(item.quantity),
        item.warehouse,
        item.reference,
        item.user,
        item.reason ?? "",
      ]),
    ];
    const csv = rows
      .map((row) =>
        row.map((value) => `"${value.replaceAll('"', '""')}"`).join(","),
      )
      .join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    link.download = "stocksense-movements.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const productToShow = selectedItem
    ? (products.find((item) => item.sku === selectedItem.sku) ?? selectedItem)
    : null;

  if (!authenticatedUser) {
    return <AuthPage onAuthenticated={setAuthenticatedUser} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#dashboard"
          onClick={(event) => {
            event.preventDefault();
            setActiveView("Dashboard");
          }}
        >
          <span className="brand-mark">
            <PackageCheck size={21} strokeWidth={2.1} />
          </span>
          <span className="brand-name">
            stock<span>sense</span>
          </span>
          <span className="brand-version">OPS</span>
        </a>

        <button
          className="workspace-switcher"
          type="button"
          onClick={() =>
            setWarehouse(
              warehouse === "All warehouses" ? warehouses[0] : "All warehouses",
            )
          }
        >
          <span className="workspace-avatar">
            <Boxes size={16} />
          </span>
          <span className="workspace-copy">
            <strong>Acme Industries</strong>
            <small>
              {warehouse === "All warehouses" ? "All locations" : warehouse}
            </small>
          </span>
          <ChevronDown size={15} />
        </button>

        <div className="nav-caption">WORKSPACE</div>
        <nav className="primary-nav" aria-label="Main navigation">
          {navigation.map(({ label, icon: Icon, badge }) => (
            <button
              key={label}
              className={`nav-item ${activeView === label ? "active" : ""}`}
              type="button"
              onClick={() => setActiveView(label)}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
              {badge && (
                <span
                  className={`nav-badge ${label === "Receipts" ? "nav-badge-warm" : ""}`}
                >
                  {badge}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-spacer" />
        <div className="sidebar-help">
          <span className="help-icon">
            <ShieldCheck size={17} />
          </span>
          <div>
            <strong>Ledger is healthy</strong>
            <small>All systems operational</small>
          </div>
          <span className="pulse-dot" />
        </div>
        <button
          className="nav-item settings-link"
          type="button"
          onClick={() => setToast("Settings are available to workspace admins")}
        >
          <Settings2 size={18} />
          <span>Settings</span>
        </button>
        <button
          className="profile-switcher"
          type="button"
          onClick={() =>
            setToast("Signed in as Olivia Chen · Inventory Manager")
          }
        >
          <span className="profile-avatar">OC</span>
          <span className="profile-copy">
            <strong>{authenticatedUser.name}</strong>
            <small>{authenticatedUser.role}</small>
          </span>
          <MoreHorizontal size={19} />
        </button>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="mobile-brand">
            <PackageCheck size={20} />
            <strong>stocksense</strong>
          </div>
          <div className="breadcrumbs">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{activeView}</strong>
          </div>
          <div className="topbar-actions">
            <label className="global-search">
              <Search size={16} />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search products, SKU..."
                aria-label="Search products and SKU"
              />
              <kbd>⌘ K</kbd>
            </label>
            <div className="notification-wrap">
              <button
                className={`icon-button notification-button ${notificationOpen ? "selected" : ""}`}
                type="button"
                aria-label="Notifications"
                onClick={() => setNotificationOpen((open) => !open)}
              >
                <Bell size={18} />
                <i />
              </button>
              {notificationOpen && (
                <div className="notification-popover">
                  <div className="popover-heading">
                    <strong>Notifications</strong>
                    <span>2 new</span>
                  </div>
                  <p>
                    <CircleAlert size={16} /> 2 products have reached their
                    reorder point.
                  </p>
                  <p>
                    <PackagePlus size={16} /> Receipt REC-2025-0842 was
                    completed.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setNotificationOpen(false);
                      setStatusFilter("Low stock");
                      setActiveView("Inventory");
                    }}
                  >
                    Review low stock <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </div>
            <button
              className="icon-button signout-button"
              type="button"
              aria-label="Sign out"
              title="Sign out"
              onClick={() => setAuthenticatedUser(null)}
            >
              <LogOut size={17} />
            </button>
            <span className="topbar-divider" />
            <span className="topbar-date">
              <span className="date-dot" /> Live data
            </span>
          </div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" /> STOCK CONTROL, AT A GLANCE
              </div>
              <h1>
                {selectedTitle}
                <span className="heading-period">
                  {activeView === "Dashboard" ? "." : ""}
                </span>
              </h1>
              <p>
                {activeView === "Dashboard"
                  ? "Here’s what’s happening across your warehouses today."
                  : viewDescription(activeView)}
              </p>
            </div>
            <div className="heading-actions">
              <label className="warehouse-filter">
                <MapPin size={15} />
                <select
                  aria-label="Filter by warehouse"
                  value={warehouse}
                  onChange={(event) => setWarehouse(event.target.value)}
                >
                  <option>All warehouses</option>
                  {warehouses.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
                <ChevronDown size={14} />
              </label>
              <button
                className="button button-primary"
                type="button"
                onClick={() => openMovement("Receipt")}
              >
                <Plus size={17} /> Receive stock
              </button>
              <button
                className="button button-icon-only"
                type="button"
                aria-label="New transfer"
                title="New transfer"
                onClick={() => openMovement("Transfer")}
              >
                <ArrowLeftRight size={17} />
              </button>
            </div>
          </section>

          <section
            className="metric-grid"
            aria-label="Inventory key performance indicators"
          >
            <MetricCard
              label="Stock value"
              value={money(stockValue)}
              change="4.8%"
              note="vs. last month"
              icon={Package}
              tone="sage"
              trend="up"
            />
            <MetricCard
              label="Units on hand"
              value={totalUnits.toLocaleString()}
              change={`${scopedProducts.length}`}
              note="active SKUs"
              icon={Boxes}
              tone="blue"
            />
            <MetricCard
              label="Needs attention"
              value={String(lowStockCount).padStart(2, "0")}
              change={lowStockCount ? "Action" : "Clear"}
              note="low or out of stock"
              icon={CircleAlert}
              tone="coral"
              warning={lowStockCount > 0}
            />
            <MetricCard
              label="Inbound today"
              value="08"
              change="3 arriving"
              note="across 2 warehouses"
              icon={ArrowDownLeft}
              tone="yellow"
            />
          </section>

          {(activeView === "Dashboard" || activeView === "Reports") && (
            <section className="insights-grid">
              <article className="panel movement-panel">
                <div className="panel-heading">
                  <div>
                    <div className="panel-kicker">
                      <span className="live-pulse" /> INVENTORY FLOW
                    </div>
                    <h2>Stock movement</h2>
                    <p>Items received and shipped over time</p>
                  </div>
                  <div className="chart-heading-actions">
                    <div className="chart-legend">
                      <span>
                        <i className="legend-received" /> Received
                      </span>
                      <span>
                        <i className="legend-shipped" /> Shipped
                      </span>
                    </div>
                    <div
                      className="segmented-control"
                      role="group"
                      aria-label="Chart date range"
                    >
                      {["7 days", "30 days"].map((period) => (
                        <button
                          type="button"
                          key={period}
                          className={chartPeriod === period ? "active" : ""}
                          onClick={() => setChartPeriod(period)}
                        >
                          {period}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <Suspense
                  fallback={
                    <div
                      className="chart-wrap chart-loading"
                      aria-label="Loading stock movement chart"
                    />
                  }
                >
                  <StockMovementChart data={chartData} />
                </Suspense>
                <div className="chart-footnote">
                  <span>
                    <ArrowUpRight size={14} /> 12.6%
                  </span>{" "}
                  more stock received this period
                </div>
              </article>

              <article className="panel attention-panel">
                <div className="panel-heading attention-heading">
                  <div>
                    <div className="panel-kicker">REORDER WATCH</div>
                    <h2>
                      Needs attention{" "}
                      <span className="attention-count">{lowStockCount}</span>
                    </h2>
                    <p>Stock is at or below its reorder point</p>
                  </div>
                  <button
                    className="text-button"
                    type="button"
                    onClick={() => {
                      setActiveView("Inventory");
                      setStatusFilter("Low stock");
                    }}
                  >
                    View all <ChevronRight size={14} />
                  </button>
                </div>
                <div className="attention-list">
                  {lowStockProducts.length ? (
                    lowStockProducts.map((product) => (
                      <button
                        className="attention-item"
                        type="button"
                        key={product.sku}
                        onClick={() => setSelectedItem(product)}
                      >
                        <span className={`product-icon ${product.color}`}>
                          <Package size={17} />
                        </span>
                        <span className="attention-copy">
                          <strong>{product.name}</strong>
                          <small>{product.sku}</small>
                        </span>
                        <span className="attention-quantity">
                          <strong
                            className={
                              product.quantity === 0 ? "quantity-zero" : ""
                            }
                          >
                            {product.quantity} <small>{product.unit}</small>
                          </strong>
                          <small>reorder at {product.reorderPoint}</small>
                        </span>
                      </button>
                    ))
                  ) : (
                    <div className="empty-attention">
                      <span>
                        <Check size={18} />
                      </span>
                      <strong>Everything is in good shape</strong>
                      <small>No products need reordering.</small>
                    </div>
                  )}
                </div>
                <div className="attention-footer">
                  <span className="footer-spark">
                    <Sparkles size={14} />
                  </span>
                  <span>Reorder points checked just now</span>
                  <span className="fresh-dot" />
                </div>
              </article>
            </section>
          )}

          {(activeView === "Dashboard" || activeView === "Inventory") && (
            <section className="panel inventory-panel">
              <div className="table-heading">
                <div>
                  <div className="panel-kicker">CATALOG</div>
                  <h2>
                    {activeView === "Dashboard"
                      ? "Inventory overview"
                      : "All products"}{" "}
                    <span className="table-count">
                      {visibleProducts.length}
                    </span>
                  </h2>
                </div>
                <div className="table-tools">
                  <label className="table-search">
                    <Search size={15} />
                    <input
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Search inventory"
                      aria-label="Search inventory"
                    />
                  </label>
                  <label className="select-filter">
                    <Filter size={14} />
                    <select
                      aria-label="Filter by category"
                      value={category}
                      onChange={(event) => setCategory(event.target.value)}
                    >
                      <option>All categories</option>
                      {Array.from(
                        new Set(products.map((product) => product.category)),
                      ).map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                    <ChevronDown size={13} />
                  </label>
                  <button
                    className="filter-button"
                    type="button"
                    title="Show low-stock items"
                    aria-label="Toggle low stock filter"
                    onClick={() =>
                      setStatusFilter(
                        statusFilter === "All items"
                          ? "Low stock"
                          : "All items",
                      )
                    }
                  >
                    <SlidersHorizontal size={16} />
                    <span
                      className={
                        statusFilter !== "All items" ? "filter-active-dot" : ""
                      }
                    />
                  </button>
                  <button
                    className="filter-button export-button"
                    type="button"
                    title="Export stock ledger as CSV"
                    aria-label="Export CSV"
                    onClick={exportMovements}
                  >
                    <Download size={16} />
                  </button>
                </div>
              </div>
              <div className="table-scroll">
                <table className="inventory-table">
                  <thead>
                    <tr>
                      <th>PRODUCT</th>
                      <th>LOCATION</th>
                      <th>ON HAND</th>
                      <th>UNIT COST</th>
                      <th>STATUS</th>
                      <th>
                        <span className="sr-only">Open product</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleProducts.length ? (
                      visibleProducts
                        .slice(0, activeView === "Dashboard" ? 5 : undefined)
                        .map((product) => (
                          <tr
                            key={product.sku}
                            onClick={() => setSelectedItem(product)}
                            tabIndex={0}
                            onKeyDown={(event) => {
                              if (event.key === "Enter")
                                setSelectedItem(product);
                            }}
                          >
                            <td>
                              <div className="product-cell">
                                <span
                                  className={`product-icon ${product.color}`}
                                >
                                  <Package size={17} />
                                </span>
                                <span>
                                  <strong>{product.name}</strong>
                                  <small>
                                    {product.sku} <i /> {product.category}
                                  </small>
                                </span>
                              </div>
                            </td>
                            <td>
                              <span className="location-cell">
                                <MapPin size={13} />
                                {product.warehouse}
                                <small>{product.location}</small>
                              </span>
                            </td>
                            <td>
                              <span className="on-hand">
                                <strong>
                                  {product.quantity.toLocaleString()}
                                </strong>
                                <small>{product.unit}</small>
                              </span>
                            </td>
                            <td className="cost-cell">
                              {money(product.unitCost)}
                            </td>
                            <td>
                              <StatusBadge status={getStatus(product)} />
                            </td>
                            <td>
                              <button
                                className="row-more"
                                type="button"
                                aria-label={`View ${product.name}`}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setSelectedItem(product);
                                }}
                              >
                                <ChevronRight size={17} />
                              </button>
                            </td>
                          </tr>
                        ))
                    ) : (
                      <tr>
                        <td className="empty-table" colSpan={6}>
                          <PackageSearch size={21} />
                          <strong>No products found</strong>
                          <span>Try a different search or filter.</span>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="table-footer">
                <span>
                  Showing{" "}
                  <strong>
                    {Math.min(
                      visibleProducts.length,
                      activeView === "Dashboard" ? 5 : visibleProducts.length,
                    )}
                  </strong>{" "}
                  of <strong>{visibleProducts.length}</strong> products
                </span>
                <button
                  className="text-button"
                  type="button"
                  onClick={() => setActiveView("Inventory")}
                >
                  View inventory <ChevronRight size={14} />
                </button>
              </div>
            </section>
          )}

          {activeView === "Movements" && (
            <MovementsPanel
              movements={movements
                .filter(
                  (item) =>
                    warehouse === "All warehouses" ||
                    item.warehouse === warehouse,
                )
                .filter((item) =>
                  `${item.product} ${item.sku} ${item.reference}`
                    .toLowerCase()
                    .includes(search.toLowerCase()),
                )}
              onExport={exportMovements}
            />
          )}
          {activeView === "Receipts" && (
            <DocumentsPanel
              kind="Receipts"
              onCreate={() => openMovement("Receipt")}
            />
          )}
          {activeView === "Transfers" && (
            <DocumentsPanel
              kind="Transfers"
              onCreate={() => openMovement("Transfer")}
            />
          )}

          <footer className="page-footer">
            <span>
              <ShieldCheck size={14} /> Stock ledger is append-only
            </span>
            <span>
              LAST SYNCED <strong>Just now</strong>
            </span>
            <span>
              StockSense <i>·</i> Inventory operations
            </span>
          </footer>
        </div>
      </main>

      {dialogOpen && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setDialogOpen(false);
          }}
        >
          <section
            className="movement-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="movement-title"
          >
            <div className="modal-header">
              <div>
                <span className="modal-icon">
                  <FilePlus2 size={18} />
                </span>
                <div>
                  <div className="panel-kicker">INVENTORY OPERATIONS</div>
                  <h2 id="movement-title">New stock movement</h2>
                </div>
              </div>
              <button
                className="icon-button modal-close"
                type="button"
                aria-label="Close dialog"
                onClick={() => setDialogOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <form onSubmit={submitMovement}>
              <label className="form-label">MOVEMENT TYPE</label>
              <div className="movement-types">
                {(
                  [
                    "Receipt",
                    "Delivery",
                    "Transfer",
                    "Adjustment",
                  ] as MovementKind[]
                ).map((kind) => (
                  <button
                    type="button"
                    className={movementKind === kind ? "selected" : ""}
                    key={kind}
                    onClick={() => chooseMovementKind(kind)}
                  >
                    {kind}
                  </button>
                ))}
              </div>
              <label className="form-field">
                <span>Product</span>
                <span className="input-with-icon">
                  <Package size={15} />
                  <select
                    value={selectedProduct}
                    onChange={(event) => chooseMovementProduct(event.target.value)}
                    required
                  >
                    {products.map((product) => (
                      <option key={product.sku} value={product.sku}>
                        {product.name} · {product.sku}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={14} />
                </span>
              </label>
              <div className="form-row">
                <label className="form-field">
                  <span>
                    {movementKind === "Adjustment"
                      ? "Quantity to adjust"
                      : "Quantity"}
                  </span>
                  <span className="number-field">
                    <input
                      type="number"
                      min="0.01"
                      step="any"
                      value={quantity}
                      onChange={(event) => setQuantity(event.target.value)}
                      placeholder="e.g. 24"
                      required
                    />
                    <span>
                      {products.find(
                        (product) => product.sku === selectedProduct,
                      )?.unit ?? "units"}
                    </span>
                  </span>
                </label>
                <label className="form-field">
                  <span>
                    {movementKind === "Delivery"
                      ? "Ship from"
                      : movementKind === "Transfer"
                        ? "Move from"
                        : "Warehouse"}
                  </span>
                  <span className="input-with-icon">
                    <MapPin size={15} />
                    <select
                      value={movementWarehouse}
                      onChange={(event) =>
                        setMovementWarehouse(event.target.value)
                      }
                    >
                      {warehouses.map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                    <ChevronDown size={14} />
                  </span>
                </label>
              </div>
              {movementKind === "Adjustment" && (
                <>
                  <label className="form-label">COUNT VARIANCE</label>
                  <div className="direction-toggle">
                    <button
                      className={
                        adjustmentDirection === "Increase"
                          ? "selected increase"
                          : ""
                      }
                      type="button"
                      onClick={() => setAdjustmentDirection("Increase")}
                    >
                      <Plus size={14} /> Increase stock
                    </button>
                    <button
                      className={
                        adjustmentDirection === "Decrease"
                          ? "selected decrease"
                          : ""
                      }
                      type="button"
                      onClick={() => setAdjustmentDirection("Decrease")}
                    >
                      <ArrowDownRight size={14} /> Decrease stock
                    </button>
                  </div>
                  <label className="form-field reason-field">
                    <span>
                      Reason <b>Required</b>
                    </span>
                    <input
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      placeholder="e.g. Damaged during inspection"
                    />
                  </label>
                </>
              )}
              {movementKind === "Transfer" && (
                <label className="form-field">
                  <span>Move to</span>
                  <span className="input-with-icon">
                    <MapPin size={15} />
                    <select
                      value={destination}
                      onChange={(event) => setDestination(event.target.value)}
                    >
                      {warehouses
                        .filter((item) => item !== movementWarehouse)
                        .map((item) => (
                          <option key={item}>{item}</option>
                        ))}
                    </select>
                    <ChevronDown size={14} />
                  </span>
                </label>
              )}
              {movementKind === "Receipt" && (
                <label className="form-field">
                  <span>
                    Supplier / reference <small>OPTIONAL</small>
                  </span>
                  <input placeholder="e.g. Northstar Metals · PO-1088" />
                </label>
              )}
              {formError && (
                <div className="form-error">
                  <CircleAlert size={15} />
                  {formError}
                </div>
              )}
              <div className="modal-note">
                <ShieldCheck size={15} />
                <span>
                  This movement will be written to the append-only stock ledger.
                </span>
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setDialogOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="button button-primary">
                  <Check size={16} /> Validate {movementKind.toLowerCase()}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {productToShow && (
        <div
          className="drawer-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSelectedItem(null);
          }}
        >
          <aside className="product-drawer" aria-label="Product details">
            <div className="drawer-top">
              <span className="panel-kicker">PRODUCT DETAILS</span>
              <button
                className="icon-button"
                type="button"
                aria-label="Close product details"
                onClick={() => setSelectedItem(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="drawer-product-heading">
              <span className={`product-icon large ${productToShow.color}`}>
                <Package size={22} />
              </span>
              <div>
                <h2>{productToShow.name}</h2>
                <span>{productToShow.sku}</span>
              </div>
              <StatusBadge status={getStatus(productToShow)} />
            </div>
            <div className="drawer-stock">
              <div>
                <span>On hand</span>
                <strong>
                  {productToShow.quantity.toLocaleString()}{" "}
                  <small>{productToShow.unit}</small>
                </strong>
              </div>
              <div>
                <span>Reorder point</span>
                <strong>
                  {productToShow.reorderPoint}{" "}
                  <small>{productToShow.unit}</small>
                </strong>
              </div>
            </div>
            <div className="drawer-section">
              <span className="panel-kicker">STORAGE LOCATION</span>
              <div className="drawer-location">
                <MapPin size={16} />
                <div>
                  <strong>{productToShow.warehouse}</strong>
                  <span>{productToShow.location}</span>
                </div>
              </div>
            </div>
            <div className="drawer-section">
              <span className="panel-kicker">VALUATION</span>
              <div className="drawer-detail-row">
                <span>Unit cost</span>
                <strong>{money(productToShow.unitCost)}</strong>
              </div>
              <div className="drawer-detail-row">
                <span>Stock value</span>
                <strong>
                  {money(productToShow.quantity * productToShow.unitCost)}
                </strong>
              </div>
              <div className="drawer-detail-row">
                <span>Category</span>
                <strong>{productToShow.category}</strong>
              </div>
            </div>
            <div className="drawer-section recent-moves">
              <div className="drawer-section-heading">
                <span className="panel-kicker">RECENT MOVEMENTS</span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    setActiveView("Movements");
                    setSelectedItem(null);
                  }}
                >
                  Ledger <ChevronRight size={13} />
                </button>
              </div>
              {movements
                .filter((movement) => movement.sku === productToShow.sku)
                .slice(0, 3)
                .map((movement) => (
                  <div className="drawer-movement" key={movement.id}>
                    <span
                      className={`movement-symbol ${movement.quantity < 0 ? "negative" : ""}`}
                    >
                      {movement.quantity < 0 ? (
                        <ArrowDownRight size={15} />
                      ) : (
                        <ArrowUpRight size={15} />
                      )}
                    </span>
                    <div>
                      <strong>
                        {movement.type} <small>{movement.reference}</small>
                      </strong>
                      <span>{movement.date}</span>
                    </div>
                    <b className={movement.quantity < 0 ? "negative-text" : ""}>
                      {movement.quantity > 0 ? "+" : ""}
                      {movement.quantity}
                    </b>
                  </div>
                ))}
            </div>
            <button
              className="button button-primary drawer-action"
              type="button"
              onClick={() => {
                setSelectedItem(null);
                openMovement("Receipt", productToShow.sku);
              }}
            >
              <Plus size={16} /> Record movement
            </button>
          </aside>
        </div>
      )}

      {toast && (
        <div className="toast">
          <span>
            <Check size={15} />
          </span>
          {toast}
          <button
            type="button"
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  change,
  note,
  icon: Icon,
  tone,
  trend,
  warning,
}: {
  label: string;
  value: string;
  change: string;
  note: string;
  icon: LucideIcon;
  tone: string;
  trend?: "up";
  warning?: boolean;
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <span className={`metric-icon ${tone}`}>
          <Icon size={17} strokeWidth={1.9} />
        </span>
      </div>
      <div className="metric-value-row">
        <strong>{value}</strong>
        <span
          className={`metric-change ${warning ? "change-warning" : ""} ${trend ? "change-trend" : ""}`}
        >
          {trend && <ArrowUpRight size={13} />}
          {change}
        </span>
      </div>
      <div className="metric-note">{note}</div>
      <span className={`metric-accent ${tone}`} />
    </article>
  );
}

function StatusBadge({ status }: { status: string }) {
  const className =
    status === "In stock"
      ? "status-good"
      : status === "Low stock"
        ? "status-low"
        : "status-out";
  return (
    <span className={`status-badge ${className}`}>
      <i />
      {status}
    </span>
  );
}

function MovementsPanel({
  movements,
  onExport,
}: {
  movements: Movement[];
  onExport: () => void;
}) {
  return (
    <section className="panel ledger-panel">
      <div className="table-heading">
        <div>
          <div className="panel-kicker">IMMUTABLE STOCK LEDGER</div>
          <h2>
            Movement history{" "}
            <span className="table-count">{movements.length}</span>
          </h2>
          <p>Every stock change, traced from source to shelf.</p>
        </div>
        <button
          className="button button-secondary export-action"
          type="button"
          onClick={onExport}
        >
          <Download size={16} /> Export CSV
        </button>
      </div>
      <div className="table-scroll">
        <table className="inventory-table ledger-table">
          <thead>
            <tr>
              <th>MOVEMENT</th>
              <th>REFERENCE</th>
              <th>WAREHOUSE</th>
              <th>DATE / USER</th>
              <th>QUANTITY</th>
            </tr>
          </thead>
          <tbody>
            {movements.map((item) => (
              <tr key={item.id}>
                <td>
                  <div className="product-cell">
                    <span
                      className={`ledger-type-icon ${item.type.toLowerCase()}`}
                    >
                      {item.type === "Receipt" ? (
                        <ArrowDownLeft size={16} />
                      ) : item.type === "Delivery" ? (
                        <ArrowUpRight size={16} />
                      ) : item.type === "Transfer" ? (
                        <ArrowLeftRight size={16} />
                      ) : (
                        <Settings2 size={16} />
                      )}
                    </span>
                    <span>
                      <strong>{item.product}</strong>
                      <small>
                        {item.sku} <i /> {item.type}
                        {item.reason && (
                          <>
                            <i /> {item.reason}
                          </>
                        )}
                      </small>
                    </span>
                  </div>
                </td>
                <td className="reference-cell">{item.reference}</td>
                <td>
                  <span className="location-cell">
                    <MapPin size={13} />
                    {item.warehouse}
                  </span>
                </td>
                <td>
                  <span className="on-hand date-user">
                    <strong>{item.date}</strong>
                    <small>by {item.user}</small>
                  </span>
                </td>
                <td
                  className={`ledger-quantity ${item.quantity < 0 ? "negative-text" : ""}`}
                >
                  {item.quantity > 0 ? "+" : ""}
                  {item.quantity}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ledger-footnote">
        <FileClock size={15} /> Ledger entries are permanent and cannot be
        edited or deleted.
      </div>
    </section>
  );
}

function DocumentsPanel({
  kind,
  onCreate,
}: {
  kind: "Receipts" | "Transfers";
  onCreate: () => void;
}) {
  const isReceipt = kind === "Receipts";
  const rows = isReceipt
    ? [
        [
          "REC-2025-0842",
          "Northstar Metals",
          "Steel sheet · 304L",
          "48 sheets",
          "Today, 10:42 AM",
          "Done",
        ],
        [
          "REC-2025-0843",
          "Apex Industrial Supply",
          "Filter cartridge F-120",
          "36 units",
          "Today, 9:15 AM",
          "Ready",
        ],
        [
          "REC-2025-0844",
          "Pacific Safety Co.",
          "Safety gloves · size 9",
          "120 pairs",
          "Today, 8:30 AM",
          "Waiting",
        ],
        [
          "REC-2025-0845",
          "Northstar Metals",
          "Copper wire · 2.5mm",
          "20 reels",
          "Sep 25, 3:10 PM",
          "Draft",
        ],
      ]
    : [
        [
          "TRF-2025-0119",
          "Central depot → Harbor storage",
          "Copper wire · 2.5mm",
          "20 reels",
          "Yesterday, 4:36 PM",
          "Done",
        ],
        [
          "TRF-2025-0120",
          "North warehouse → Central depot",
          "Bearing 6204-ZZ",
          "12 units",
          "Today, 11:06 AM",
          "Ready",
        ],
        [
          "TRF-2025-0121",
          "Harbor storage → North warehouse",
          "Steel sheet · 304L",
          "16 sheets",
          "Today, 9:52 AM",
          "Waiting",
        ],
      ];
  return (
    <section className="panel docs-panel">
      <div className="table-heading">
        <div>
          <div className="panel-kicker">DOCUMENT WORKFLOW</div>
          <h2>
            {isReceipt ? "Incoming receipts" : "Internal transfers"}{" "}
            <span className="table-count">{rows.length}</span>
          </h2>
          <p>
            {isReceipt
              ? "Track deliveries from suppliers through validation."
              : "Move stock between warehouse locations."}
          </p>
        </div>
        <button
          className="button button-primary"
          type="button"
          onClick={onCreate}
        >
          <Plus size={16} /> {isReceipt ? "New receipt" : "New transfer"}
        </button>
      </div>
      <div className="document-list">
        {rows.map(([ref, source, product, qty, date, status]) => (
          <article className="document-row" key={ref}>
            <span
              className={`document-icon ${isReceipt ? "receipt-icon" : "transfer-icon"}`}
            >
              {isReceipt ? <PackagePlus size={18} /> : <Truck size={18} />}
            </span>
            <div className="document-main">
              <strong>{ref}</strong>
              <span>{source}</span>
              <small>
                {product} <i /> {qty}
              </small>
            </div>
            <div className="document-date">
              <span>{date}</span>
              <strong>{qty}</strong>
            </div>
            <DocumentStatus status={status} />
            <button
              className="row-more"
              type="button"
              aria-label={`Open ${ref}`}
            >
              <ChevronRight size={17} />
            </button>
          </article>
        ))}
      </div>
      <div className="workflow-note">
        <Clock3 size={15} />
        <span>
          Only documents validated as <strong>Done</strong> update the stock
          ledger.
        </span>
      </div>
    </section>
  );
}

function DocumentStatus({ status }: { status: string }) {
  const className =
    status === "Done"
      ? "status-good"
      : status === "Ready"
        ? "status-ready"
        : status === "Waiting"
          ? "status-low"
          : "status-draft";
  return (
    <span className={`status-badge ${className}`}>
      <i />
      {status}
    </span>
  );
}

function viewDescription(view: View) {
  const copy: Record<View, string> = {
    Dashboard: "Here’s what’s happening across your warehouses today.",
    Inventory: "A live view of every product, count, and storage location.",
    Movements: "A complete, traceable history of stock changes.",
    Receipts: "Track incoming deliveries from suppliers through validation.",
    Transfers: "Move stock across warehouses without losing the audit trail.",
    Reports: "Monitor stock valuation and movement trends across locations.",
  };
  return copy[view];
}

export default StockSense;
