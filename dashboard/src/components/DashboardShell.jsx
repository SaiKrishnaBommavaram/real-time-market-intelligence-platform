import { PanelStatus } from "./PanelStatus";

const NAV_ITEMS = [
  { route: "overview", label: "Overview" },
  { route: "ticker", label: "Ticker" },
  { route: "watchlist", label: "Watchlist" },
  { route: "observability", label: "Observability" },
];

export function DashboardShell({
  children,
  health,
  loading,
  onRefresh,
  route,
  onNavigate,
  shellState,
}) {
  return (
    <main className="page">
      <section className="topbar">
        <div>
          <p className="eyebrow">Real-Time Market Intelligence</p>
          <h1>Operations Dashboard</h1>
        </div>

        <div className="topbar-actions">
          <div className={`status-pill ${health ? "healthy" : "unhealthy"}`}>
            <span className="status-dot" />
            {health ? "API online" : "API unavailable"}
          </div>
          <button className="secondary-button" onClick={onRefresh} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh all"}
          </button>
        </div>
      </section>

      <section className="dashboard-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.route}
            className={`nav-chip ${route === item.route ? "active" : ""}`}
            onClick={() => onNavigate(item.route)}
          >
            {item.label}
          </button>
        ))}
      </section>

      <PanelStatus state={shellState} />
      {children}
    </main>
  );
}
