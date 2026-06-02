import "./App.css";

import { MarketOverview } from "./components/MarketOverview";
import { MarketSignals } from "./components/MarketSignals";
import { NewsPanel } from "./components/NewsPanel";
import { TickerWorkspace } from "./components/TickerWorkspace";
import { WatchlistPanel } from "./components/WatchlistPanel";
import { useDashboardData } from "./hooks/useDashboardData";

function App() {
  const {
    activeTicker,
    addTickerToWatchlist,
    anomalyFeed,
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
    topMovers,
    triggeredAlerts,
    updateWatchlistThreshold,
    watchlistEntries,
    liveStock,
    loadDashboard,
    removeTickerFromWatchlist,
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

          <MarketSignals
            activeTicker={activeTicker}
            anomalyFeed={anomalyFeed}
            onTickerSelect={searchTicker}
            topMovers={topMovers}
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

          <WatchlistPanel
            activeTicker={activeTicker}
            onAddActiveTicker={() => addTickerToWatchlist(activeTicker)}
            onRemoveTicker={removeTickerFromWatchlist}
            onSelectTicker={searchTicker}
            onUpdateThreshold={updateWatchlistThreshold}
            triggeredAlerts={triggeredAlerts}
            watchlistEntries={watchlistEntries}
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
