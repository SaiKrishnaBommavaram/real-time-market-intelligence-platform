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
  buildMarketLeaders,
  buildMarketMetrics,
  buildMarketTrend,
  buildTickerTrend,
} from "../utils/dashboard";

const DEFAULT_TICKER = "AAPL";

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

  const marketMetrics = useMemo(() => buildMarketMetrics(summary), [summary]);
  const marketTrend = useMemo(() => buildMarketTrend(summary), [summary]);
  const marketLeaders = useMemo(() => buildMarketLeaders(summary), [summary]);
  const quickTickers = useMemo(
    () => marketLeaders.map((row) => row.ticker).slice(0, 5),
    [marketLeaders],
  );
  const tickerTrend = useMemo(() => buildTickerTrend(tickerSummary), [tickerSummary]);
  const latestTickerSummary = tickerSummary[0] || null;

  const hasInitialized = useRef(false);

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

  return {
    activeTicker,
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
    searchLoading,
    summary,
    ticker,
    tickerSummary,
    tickerTrend,
    loadDashboard,
    searchTicker,
    setTicker,
  };
}
