import "./App.css";

import { MarketOverview } from "./components/MarketOverview";
import { NewsPanel } from "./components/NewsPanel";
import { TickerWorkspace } from "./components/TickerWorkspace";
import { useDashboardData } from "./hooks/useDashboardData";

function App() {
  const {
    activeTicker,
    error,
    health,
    latestTickerSummary,
    loading,
    marketLeaders,
    marketMetrics,
    marketTrend,
    news,
    newsSummary,
    newsSummaryError,
    newsSummaryLoading,
    quickTickers,
    searchLoading,
    summary,
    ticker,
    tickerSummary,
    tickerTrend,
    liveStock,
    loadDashboard,
    searchTicker,
    setTicker,
  } = useDashboardData();

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
          <button className="secondary-button" onClick={loadDashboard} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh data"}
          </button>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="loading">Loading dashboard data...</div>
      ) : (
        <>
          <MarketOverview
            activeTicker={activeTicker}
            marketLeaders={marketLeaders}
            marketMetrics={marketMetrics}
            marketTrend={marketTrend}
            onTickerSelect={searchTicker}
            summary={summary}
          />

          <TickerWorkspace
            activeTicker={activeTicker}
            latestTickerSummary={latestTickerSummary}
            liveStock={liveStock}
            onSearch={searchTicker}
            quickTickers={quickTickers}
            searchLoading={searchLoading}
            setTicker={setTicker}
            ticker={ticker}
            tickerSummary={tickerSummary}
            tickerTrend={tickerTrend}
          />

          <NewsPanel
            activeTicker={activeTicker}
            news={news}
            newsSummary={newsSummary}
            newsSummaryError={newsSummaryError}
            newsSummaryLoading={newsSummaryLoading}
          />
        </>
      )}
    </main>
  );
}

export default App;
