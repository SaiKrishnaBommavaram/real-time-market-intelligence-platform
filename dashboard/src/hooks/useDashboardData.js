import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchHealth,
  fetchLiveStock,
  fetchMarketSummary,
  fetchStockNews,
  fetchStockNewsSummary,
  fetchStockSummary,
} from "../api";
import {
  buildAnomalyFeed,
  buildMarketLeaders,
  buildMarketMetrics,
  buildMarketTrend,
  buildTickerTrend,
  buildTopMovers,
  buildWatchlistEntries,
  createWatchlistEntry,
} from "../utils/dashboard";

const DEFAULT_TICKER = "AAPL";
const WATCHLIST_STORAGE_KEY = "market-dashboard-watchlist-v1";

function loadStoredWatchlist() {
  if (typeof window === "undefined") {
    return [createWatchlistEntry(DEFAULT_TICKER)];
  }

  try {
    const rawValue = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (!rawValue) {
      return [createWatchlistEntry(DEFAULT_TICKER)];
    }

    const parsedValue = JSON.parse(rawValue);
    if (!Array.isArray(parsedValue) || !parsedValue.length) {
      return [createWatchlistEntry(DEFAULT_TICKER)];
    }

    return parsedValue
      .filter((item) => item?.ticker)
      .map((item) => ({
        ticker: String(item.ticker).trim().toUpperCase(),
        priceAlertThreshold: Number(item.priceAlertThreshold || 4),
        volumeAlertThreshold: Number(item.volumeAlertThreshold || 1.5),
      }));
  } catch {
    return [createWatchlistEntry(DEFAULT_TICKER)];
  }
}

export function useDashboardData() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState([]);
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [activeTicker, setActiveTicker] = useState(DEFAULT_TICKER);
  const [liveStock, setLiveStock] = useState(null);
  const [tickerSummary, setTickerSummary] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [news, setNews] = useState([]);
  const [newsSummary, setNewsSummary] = useState(null);
  const [newsSummaryLoading, setNewsSummaryLoading] = useState(false);
  const [newsSummaryError, setNewsSummaryError] = useState("");
  const [watchlist, setWatchlist] = useState(loadStoredWatchlist);

  const marketMetrics = useMemo(() => buildMarketMetrics(summary), [summary]);
  const marketTrend = useMemo(() => buildMarketTrend(summary), [summary]);
  const marketLeaders = useMemo(() => buildMarketLeaders(summary), [summary]);
  const topMovers = useMemo(() => buildTopMovers(summary), [summary]);
  const anomalyFeed = useMemo(() => buildAnomalyFeed(summary), [summary]);
  const quickTickers = useMemo(
    () => marketLeaders.map((row) => row.ticker).slice(0, 5),
    [marketLeaders],
  );
  const tickerTrend = useMemo(() => buildTickerTrend(tickerSummary), [tickerSummary]);
  const latestTickerSummary = tickerSummary[0] || null;
  const watchlistEntries = useMemo(
    () => buildWatchlistEntries(summary, watchlist),
    [summary, watchlist],
  );
  const triggeredAlerts = useMemo(
    () => watchlistEntries.filter((entry) => entry.hasAlert),
    [watchlistEntries],
  );

  const hasInitialized = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlist));
  }, [watchlist]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    const [healthResult, marketResult] = await Promise.allSettled([
      fetchHealth(),
      fetchMarketSummary(),
    ]);

    if (healthResult.status === "fulfilled") {
      setHealth(healthResult.value);
    } else {
      setHealth(null);
    }

    if (marketResult.status === "fulfilled") {
      setSummary(marketResult.value.data || []);
    } else {
      setSummary([]);
      setError(
        marketResult.reason instanceof Error
          ? marketResult.reason.message
          : "Could not load dashboard data. Make sure FastAPI is running.",
      );
    }

    setLoading(false);
  }, []);

  const searchTicker = useCallback(async (nextTicker = ticker) => {
    const cleanedTicker = nextTicker.trim().toUpperCase();

    if (!cleanedTicker) {
      setError("Please enter a ticker symbol.");
      return;
    }

    setTicker(cleanedTicker);
    setActiveTicker(cleanedTicker);
    setSearchLoading(true);
    setError("");
    setNews([]);
    setNewsSummary(null);
    setNewsSummaryError("");
    setNewsSummaryLoading(true);

    const [liveResult, newsResult, summaryResult, warehouseResult] =
      await Promise.allSettled([
        fetchLiveStock(cleanedTicker),
        fetchStockNews(cleanedTicker),
        fetchStockNewsSummary(cleanedTicker),
        fetchStockSummary(cleanedTicker),
      ]);

    if (liveResult.status === "fulfilled") {
      setLiveStock(liveResult.value);
    } else {
      setLiveStock(null);
      setError(
        liveResult.reason?.response?.data?.detail ||
          `No live data found for ${cleanedTicker}`,
      );
    }

    if (newsResult.status === "fulfilled") {
      setNews(newsResult.value.articles || []);
    } else {
      setNews([]);
    }

    if (summaryResult.status === "fulfilled") {
      setNewsSummary(summaryResult.value);
    } else {
      setNewsSummary(null);
      setNewsSummaryError("News summary is unavailable for this ticker right now.");
    }

    if (warehouseResult.status === "fulfilled") {
      setTickerSummary(warehouseResult.value.data || []);
    } else {
      setTickerSummary([]);
    }

    setNewsSummaryLoading(false);
    setSearchLoading(false);
  }, [ticker]);

  useEffect(() => {
    if (hasInitialized.current) {
      return;
    }

    hasInitialized.current = true;

    async function initialize() {
      await Promise.all([loadDashboard(), searchTicker(DEFAULT_TICKER)]);
    }

    void initialize();
  }, [loadDashboard, searchTicker]);

  function addTickerToWatchlist(nextTicker = activeTicker) {
    const cleanedTicker = nextTicker.trim().toUpperCase();
    if (!cleanedTicker) {
      return;
    }

    setWatchlist((currentWatchlist) => {
      if (currentWatchlist.some((item) => item.ticker === cleanedTicker)) {
        return currentWatchlist;
      }

      return [...currentWatchlist, createWatchlistEntry(cleanedTicker)];
    });
  }

  function removeTickerFromWatchlist(tickerToRemove) {
    setWatchlist((currentWatchlist) => {
      const nextWatchlist = currentWatchlist.filter((item) => item.ticker !== tickerToRemove);
      return nextWatchlist.length ? nextWatchlist : [createWatchlistEntry(DEFAULT_TICKER)];
    });
  }

  function updateWatchlistThreshold(tickerToUpdate, fieldName, nextValue) {
    const normalizedValue = Number(nextValue);
    if (!Number.isFinite(normalizedValue) || normalizedValue <= 0) {
      return;
    }

    setWatchlist((currentWatchlist) =>
      currentWatchlist.map((item) =>
        item.ticker === tickerToUpdate
          ? { ...item, [fieldName]: normalizedValue }
          : item,
      ),
    );
  }

  return {
    activeTicker,
    addTickerToWatchlist,
    anomalyFeed,
    error,
    health,
    latestTickerSummary,
    liveStock,
    loading,
    marketLeaders,
    marketMetrics,
    marketTrend,
    news,
    newsSummary,
    newsSummaryError,
    newsSummaryLoading,
    quickTickers,
    removeTickerFromWatchlist,
    searchLoading,
    summary,
    ticker,
    tickerSummary,
    tickerTrend,
    topMovers,
    triggeredAlerts,
    updateWatchlistThreshold,
    watchlistEntries,
    loadDashboard,
    searchTicker,
    setTicker,
  };
}
