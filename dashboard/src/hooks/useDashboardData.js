import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  deleteWatchlistItem,
  fetchIntradayCandles,
  fetchIntradayMovers,
  fetchHealth,
  fetchLiveStock,
  fetchMarketSummary,
  fetchStockNews,
  fetchStockNewsSummary,
  fetchStockSummary,
  fetchWatchlist,
  fetchWatchlistAlerts,
  upsertWatchlistItem,
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
  const [intradayMovers, setIntradayMovers] = useState([]);
  const [intradayCandles, setIntradayCandles] = useState([]);
  const [watchlistAlerts, setWatchlistAlerts] = useState([]);

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

    const [healthResult, marketResult, intradayMoversResult, watchlistResult, watchlistAlertsResult] =
      await Promise.allSettled([
      fetchHealth(),
      fetchMarketSummary(),
      fetchIntradayMovers(),
      fetchWatchlist(),
      fetchWatchlistAlerts(),
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

    if (intradayMoversResult.status === "fulfilled") {
      setIntradayMovers(intradayMoversResult.value.data || []);
    } else {
      setIntradayMovers([]);
    }

    if (watchlistResult.status === "fulfilled") {
      const persistedWatchlist = (watchlistResult.value.data || []).map((item) => ({
        ticker: item.ticker,
        priceAlertThreshold: Number(item.price_alert_threshold || item.priceAlertThreshold || 4),
        volumeAlertThreshold: Number(
          item.volume_alert_threshold || item.volumeAlertThreshold || 1.5,
        ),
      }));
      if (persistedWatchlist.length) {
        setWatchlist(persistedWatchlist);
      }
    }

    if (watchlistAlertsResult.status === "fulfilled") {
      setWatchlistAlerts(watchlistAlertsResult.value.data || []);
    } else {
      setWatchlistAlerts([]);
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
    const intradayResult = await Promise.allSettled([fetchIntradayCandles(cleanedTicker)]);

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

    if (intradayResult[0].status === "fulfilled") {
      setIntradayCandles(intradayResult[0].value.data || []);
    } else {
      setIntradayCandles([]);
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
    void upsertWatchlistItem({
      ticker: cleanedTicker,
      price_alert_threshold: createWatchlistEntry(cleanedTicker).priceAlertThreshold,
      volume_alert_threshold: createWatchlistEntry(cleanedTicker).volumeAlertThreshold,
    }).catch(() => undefined);
  }

  function removeTickerFromWatchlist(tickerToRemove) {
    setWatchlist((currentWatchlist) => {
      const nextWatchlist = currentWatchlist.filter((item) => item.ticker !== tickerToRemove);
      return nextWatchlist.length ? nextWatchlist : [createWatchlistEntry(DEFAULT_TICKER)];
    });
    void deleteWatchlistItem(tickerToRemove).catch(() => undefined);
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
    const nextWatchlistItem = {
      ticker: tickerToUpdate,
      price_alert_threshold:
        fieldName === "priceAlertThreshold" ? normalizedValue : watchlist.find((item) => item.ticker === tickerToUpdate)?.priceAlertThreshold || 4,
      volume_alert_threshold:
        fieldName === "volumeAlertThreshold" ? normalizedValue : watchlist.find((item) => item.ticker === tickerToUpdate)?.volumeAlertThreshold || 1.5,
    };
    void upsertWatchlistItem(nextWatchlistItem).catch(() => undefined);
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
    intradayCandles,
    intradayMovers,
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
    watchlistAlerts,
    watchlistEntries,
    loadDashboard,
    searchTicker,
    setTicker,
  };
}
