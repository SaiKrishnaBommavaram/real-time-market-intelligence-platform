import "./App.css";

import { DashboardShell } from "./components/DashboardShell";
import { ObservabilityRoute } from "./components/routes/ObservabilityRoute";
import { OverviewRoute } from "./components/routes/OverviewRoute";
import { TickerRoute } from "./components/routes/TickerRoute";
import { WatchlistRoute } from "./components/routes/WatchlistRoute";
import { useDashboardData } from "./hooks/useDashboardData";
import { useDashboardRoute } from "./hooks/useDashboardRoute";

function App() {
  const { navigate, route } = useDashboardRoute();
  const {
    activeTicker,
    addTickerToWatchlist,
    anomalyFeed,
    anomalyHistory,
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
    observabilityMetrics,
    panelStates,
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
  } = useDashboardData(route);

  async function handleTickerSelect(nextTicker) {
    await searchTicker(nextTicker);
    if (route !== "ticker") {
      navigate("ticker");
    }
  }

  let content;

  if (route === "ticker") {
    content = (
      <TickerRoute
        activeTicker={activeTicker}
        latestTickerSummary={latestTickerSummary}
        liveStock={liveStock}
        news={news}
        newsSummary={newsSummary}
        newsSummaryError={newsSummaryError}
        newsSummaryLoading={newsSummaryLoading}
        onSearch={handleTickerSelect}
        panelStates={panelStates}
        quickTickers={quickTickers}
        searchLoading={searchLoading}
        setTicker={setTicker}
        ticker={ticker}
        tickerSummary={tickerSummary}
        tickerTrend={tickerTrend}
      />
    );
  } else if (route === "watchlist") {
    content = (
      <WatchlistRoute
        activeTicker={activeTicker}
        addTickerToWatchlist={addTickerToWatchlist}
        anomalyHistory={anomalyHistory}
        panelStates={panelStates}
        removeTickerFromWatchlist={removeTickerFromWatchlist}
        searchTicker={handleTickerSelect}
        triggeredAlerts={triggeredAlerts}
        updateWatchlistThreshold={updateWatchlistThreshold}
        watchlistEntries={watchlistEntries}
      />
    );
  } else if (route === "observability") {
    content = (
      <ObservabilityRoute
        observabilityMetrics={observabilityMetrics}
        panelStates={panelStates}
      />
    );
  } else {
    content = (
      <OverviewRoute
        activeTicker={activeTicker}
        anomalyFeed={anomalyFeed}
        marketLeaders={marketLeaders}
        marketMetrics={marketMetrics}
        marketTrend={marketTrend}
        onTickerSelect={handleTickerSelect}
        panelStates={panelStates}
        summary={summary}
        topMovers={topMovers}
      />
    );
  }

  return (
    <DashboardShell
      health={health}
      loading={loading}
      onNavigate={navigate}
      onRefresh={loadDashboard}
      route={route}
      shellState={panelStates.shell}
    >
      {error ? <div className="error">{error}</div> : null}
      {content}
    </DashboardShell>
  );
}

export default App;
