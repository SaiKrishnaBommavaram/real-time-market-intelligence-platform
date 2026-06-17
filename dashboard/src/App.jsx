import "./App.css";

import { DashboardShell } from "./components/DashboardShell";
import { ObservabilityRoute } from "./components/routes/ObservabilityRoute";
import { OverviewRoute } from "./components/routes/OverviewRoute";
import { TickerRoute } from "./components/routes/TickerRoute";
import { WatchlistRoute } from "./components/routes/WatchlistRoute";
import { useDashboardData } from "./hooks/useDashboardData";
import { useDashboardRoute } from "./hooks/useDashboardRoute";

const VALID_CHART_WINDOWS = new Set(["1m", "3m", "6m", "max"]);
const VALID_CHART_VIEWS = new Set(["price", "indexed"]);
const VALID_COMPARE_MODES = new Set(["none", "benchmark"]);
const VALID_SORT_DIRECTIONS = new Set(["asc", "desc"]);

function normalizeTicker(value) {
  return value ? String(value).trim().toUpperCase() : "";
}

function readQueryValue(value, validValues, fallback) {
  return validValues.has(value) ? value : fallback;
}

function App() {
  const { navigate, query, route, setQueryParams } = useDashboardRoute();
  const selectedTicker = normalizeTicker(query.symbol) || "AAPL";
  const focusedWatchTicker = normalizeTicker(query.watch) || "";
  const anomalySearch = query.anomaly_q || "";
  const anomalySort = query.anomaly_sort || "trade_date";
  const anomalyDirection = readQueryValue(
    query.anomaly_dir,
    VALID_SORT_DIRECTIONS,
    "desc",
  );
  const chartWindow = readQueryValue(query.window, VALID_CHART_WINDOWS, "3m");
  const chartView = readQueryValue(query.view, VALID_CHART_VIEWS, "price");
  const chartCompare = readQueryValue(query.compare, VALID_COMPARE_MODES, "none");
  const {
    activeTicker,
    addTickerToWatchlist,
    anomalyFeed,
    anomalyHistory,
    error,
    health,
    intradayCandles,
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
    watchlistMutationState,
    liveStock,
    loadDashboard,
    removeTickerFromWatchlist,
    searchTicker,
    setTicker,
  } = useDashboardData(route, { initialTicker: selectedTicker });

  async function handleTickerSelect(nextTicker) {
    const normalizedTicker = normalizeTicker(nextTicker || ticker);
    if (!normalizedTicker) {
      return;
    }

    if (route !== "ticker") {
      navigate("ticker", {
        query: {
          ...query,
          symbol: normalizedTicker,
        },
      });
    } else {
      setQueryParams({ symbol: normalizedTicker }, { replace: false });
    }

    await searchTicker(nextTicker);
  }

  function handleShellNavigation(nextRoute) {
    const nextQuery = { ...query };
    if (nextRoute === "ticker") {
      nextQuery.symbol = activeTicker || selectedTicker;
    }

    navigate(nextRoute, { query: nextQuery });
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
        chartCompare={chartCompare}
        chartView={chartView}
        chartWindow={chartWindow}
        intradayCandles={intradayCandles}
        onChartCompareChange={(value) => setQueryParams({ compare: value })}
        onChartViewChange={(value) => setQueryParams({ view: value })}
        onChartWindowChange={(value) => setQueryParams({ window: value })}
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
        anomalySearch={anomalySearch}
        anomalySort={anomalySort}
        anomalySortDirection={anomalyDirection}
        panelStates={panelStates}
        focusedTicker={focusedWatchTicker}
        onAnomalySearchChange={(value) => setQueryParams({ anomaly_q: value })}
        onAnomalySortChange={(nextSort, nextDirection) =>
          setQueryParams({
            anomaly_sort: nextSort,
            anomaly_dir: nextDirection,
          })
        }
        onFocusTicker={(value) => setQueryParams({ watch: normalizeTicker(value) })}
        removeTickerFromWatchlist={removeTickerFromWatchlist}
        searchTicker={handleTickerSelect}
        triggeredAlerts={triggeredAlerts}
        updateWatchlistThreshold={updateWatchlistThreshold}
        watchlistMutationState={watchlistMutationState}
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
      onNavigate={handleShellNavigation}
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
