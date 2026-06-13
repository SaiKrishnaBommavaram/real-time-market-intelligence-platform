import { useEffect, useMemo, useState } from "react";
import {
  useMutation,
  useQueries,
  useQueryClient,
} from "@tanstack/react-query";

import {
  fetchAnomalyHistory,
  deleteWatchlistItem,
  fetchIntradayCandles,
  fetchIntradayMovers,
  fetchHealth,
  fetchLiveStock,
  fetchMarketSummary,
  fetchObservabilityMetrics,
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
const EMPTY_ARRAY = [];
const EMPTY_OBSERVABILITY_METRICS = {
  counters: {},
  gauges: {},
  timings: {},
};
const dashboardQueryKeys = {
  health: ["health"],
  marketSummary: ["market-summary"],
  intradayMovers: ["intraday-movers"],
  watchlist: ["watchlist"],
  watchlistAlerts: ["watchlist-alerts"],
  anomalyHistory: ["anomaly-history"],
  observabilityMetrics: ["observability-metrics"],
  liveStock: (ticker) => ["live-stock", ticker],
  stockSummary: (ticker) => ["stock-summary", ticker],
  stockNews: (ticker) => ["stock-news", ticker],
  stockNewsSummary: (ticker) => ["stock-news-summary", ticker],
  intradayCandles: (ticker) => ["intraday-candles", ticker],
};

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

export function useDashboardData(route = "overview") {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [activeTicker, setActiveTicker] = useState(DEFAULT_TICKER);
  const [validationError, setValidationError] = useState("");
  const queryClient = useQueryClient();
  const isTickerRoute = route === "ticker";
  const isWatchlistRoute = route === "watchlist";
  const isObservabilityRoute = route === "observability";

  const baseQueries = useQueries({
    queries: [
      {
        queryKey: dashboardQueryKeys.health,
        queryFn: fetchHealth,
        staleTime: 15_000,
        refetchInterval: 30_000,
      },
      {
        queryKey: dashboardQueryKeys.marketSummary,
        queryFn: fetchMarketSummary,
        staleTime: 30_000,
        refetchInterval: 60_000,
      },
      {
        queryKey: dashboardQueryKeys.intradayMovers,
        queryFn: fetchIntradayMovers,
        enabled: route === "overview",
        staleTime: 30_000,
        refetchInterval: 60_000,
      },
      {
        queryKey: dashboardQueryKeys.watchlist,
        queryFn: fetchWatchlist,
        enabled: isWatchlistRoute,
        initialData: {
          data: loadStoredWatchlist(),
        },
        staleTime: 30_000,
      },
      {
        queryKey: dashboardQueryKeys.watchlistAlerts,
        queryFn: fetchWatchlistAlerts,
        enabled: isWatchlistRoute,
        initialData: {
          data: [],
        },
        staleTime: 30_000,
        refetchInterval: 60_000,
      },
      {
        queryKey: dashboardQueryKeys.anomalyHistory,
        queryFn: () => fetchAnomalyHistory(120),
        enabled: isWatchlistRoute,
        staleTime: 30_000,
        refetchInterval: 60_000,
        initialData: {
          data: [],
        },
      },
      {
        queryKey: dashboardQueryKeys.observabilityMetrics,
        queryFn: fetchObservabilityMetrics,
        enabled: isObservabilityRoute,
        staleTime: 15_000,
        refetchInterval: 30_000,
        initialData: {
          counters: {},
          gauges: {},
          timings: {},
        },
      },
    ],
  });

  const [
    healthQuery,
    marketSummaryQuery,
    intradayMoversQuery,
    watchlistQuery,
    watchlistAlertsQuery,
    anomalyHistoryQuery,
    observabilityMetricsQuery,
  ] = baseQueries;

  const tickerQueries = useQueries({
    queries: [
      {
        queryKey: dashboardQueryKeys.liveStock(activeTicker),
        queryFn: () => fetchLiveStock(activeTicker),
        enabled: Boolean(activeTicker) && isTickerRoute,
        staleTime: 15_000,
        refetchInterval: 30_000,
      },
      {
        queryKey: dashboardQueryKeys.stockSummary(activeTicker),
        queryFn: () => fetchStockSummary(activeTicker),
        enabled: Boolean(activeTicker) && isTickerRoute,
        staleTime: 30_000,
      },
      {
        queryKey: dashboardQueryKeys.stockNews(activeTicker),
        queryFn: () => fetchStockNews(activeTicker),
        enabled: Boolean(activeTicker) && isTickerRoute,
        staleTime: 60_000,
      },
      {
        queryKey: dashboardQueryKeys.stockNewsSummary(activeTicker),
        queryFn: () => fetchStockNewsSummary(activeTicker),
        enabled: Boolean(activeTicker) && isTickerRoute,
        staleTime: 60_000,
      },
      {
        queryKey: dashboardQueryKeys.intradayCandles(activeTicker),
        queryFn: () => fetchIntradayCandles(activeTicker),
        enabled: Boolean(activeTicker) && isTickerRoute,
        staleTime: 30_000,
        refetchInterval: 60_000,
      },
    ],
  });

  const [
    liveStockQuery,
    stockSummaryQuery,
    newsQuery,
    newsSummaryQuery,
    intradayCandlesQuery,
  ] = tickerQueries;

  const health = healthQuery.data ?? null;
  const summary = marketSummaryQuery.data?.data ?? EMPTY_ARRAY;
  const intradayMovers = intradayMoversQuery.data?.data ?? EMPTY_ARRAY;
  const liveStock = liveStockQuery.data ?? null;
  const tickerSummary = stockSummaryQuery.data?.data ?? EMPTY_ARRAY;
  const news = newsQuery.data?.articles ?? EMPTY_ARRAY;
  const newsSummary = newsSummaryQuery.data ?? null;
  const newsSummaryError = newsSummaryQuery.isError
    ? "News summary is unavailable for this ticker right now."
    : "";
  const watchlist = useMemo(() => {
    const persistedItems = watchlistQuery.data?.data;
    if (!Array.isArray(persistedItems) || !persistedItems.length) {
      return [createWatchlistEntry(DEFAULT_TICKER)];
    }

    return persistedItems
      .filter((item) => item?.ticker)
      .map((item) => ({
        ticker: String(item.ticker).trim().toUpperCase(),
        priceAlertThreshold: Number(item.price_alert_threshold ?? item.priceAlertThreshold ?? 4),
        volumeAlertThreshold: Number(
          item.volume_alert_threshold ?? item.volumeAlertThreshold ?? 1.5,
        ),
      }));
  }, [watchlistQuery.data]);
  const intradayCandles = intradayCandlesQuery.data?.data ?? EMPTY_ARRAY;
  const watchlistAlerts = watchlistAlertsQuery.data?.data ?? EMPTY_ARRAY;
  const anomalyHistory = anomalyHistoryQuery.data?.data ?? EMPTY_ARRAY;
  const observabilityMetrics =
    observabilityMetricsQuery.data ?? EMPTY_OBSERVABILITY_METRICS;
  const loading =
    marketSummaryQuery.isLoading ||
    healthQuery.isLoading ||
    intradayMoversQuery.isLoading ||
    watchlistQuery.isLoading;
  const searchLoading =
    liveStockQuery.isLoading ||
    stockSummaryQuery.isLoading ||
    newsQuery.isLoading ||
    newsSummaryQuery.isLoading ||
    intradayCandlesQuery.isLoading;
  const newsSummaryLoading = newsSummaryQuery.isLoading;

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
  const watchlistEntries = useMemo(
    () => buildWatchlistEntries(summary, watchlist),
    [summary, watchlist],
  );
  const triggeredAlerts = useMemo(
    () => watchlistEntries.filter((entry) => entry.hasAlert),
    [watchlistEntries],
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlist));
  }, [watchlist]);

  const error =
    validationError ||
    (marketSummaryQuery.isError
      ? marketSummaryQuery.error instanceof Error
        ? marketSummaryQuery.error.message
        : "Could not load dashboard data. Make sure FastAPI is running."
      : "") ||
    (liveStockQuery.isError && activeTicker
      ? liveStockQuery.error?.response?.data?.detail ||
        `No live data found for ${activeTicker}`
      : "");

  async function loadDashboard() {
    setValidationError("");
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.health }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.marketSummary }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.intradayMovers }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.watchlist }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.watchlistAlerts }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.anomalyHistory }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.observabilityMetrics }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.liveStock(activeTicker) }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stockSummary(activeTicker) }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stockNews(activeTicker) }),
      queryClient.invalidateQueries({
        queryKey: dashboardQueryKeys.stockNewsSummary(activeTicker),
      }),
      queryClient.invalidateQueries({
        queryKey: dashboardQueryKeys.intradayCandles(activeTicker),
      }),
    ]);
  }

  async function searchTicker(nextTicker = ticker) {
    const cleanedTicker = nextTicker.trim().toUpperCase();

    if (!cleanedTicker) {
      setValidationError("Please enter a ticker symbol.");
      return;
    }

    setTicker(cleanedTicker);
    setActiveTicker(cleanedTicker);
    setValidationError("");
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.liveStock(cleanedTicker) }),
      queryClient.invalidateQueries({
        queryKey: dashboardQueryKeys.stockSummary(cleanedTicker),
      }),
      queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.stockNews(cleanedTicker) }),
      queryClient.invalidateQueries({
        queryKey: dashboardQueryKeys.stockNewsSummary(cleanedTicker),
      }),
      queryClient.invalidateQueries({
        queryKey: dashboardQueryKeys.intradayCandles(cleanedTicker),
      }),
    ]);
  }

  const watchlistMutation = useMutation({
    mutationFn: upsertWatchlistItem,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.watchlist }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.watchlistAlerts }),
      ]);
    },
  });

  const deleteWatchlistMutation = useMutation({
    mutationFn: deleteWatchlistItem,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.watchlist }),
        queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.watchlistAlerts }),
      ]);
    },
  });

  function addTickerToWatchlist(nextTicker = activeTicker) {
    const cleanedTicker = nextTicker.trim().toUpperCase();
    if (!cleanedTicker) {
      return;
    }

    const currentWatchlist = watchlistQuery.data?.data ?? [];
    if (currentWatchlist.some((item) => item.ticker === cleanedTicker)) {
      return;
    }

    const nextWatchlist = [...currentWatchlist, createWatchlistEntry(cleanedTicker)];
    queryClient.setQueryData(dashboardQueryKeys.watchlist, {
      ...(watchlistQuery.data || {}),
      data: nextWatchlist,
    });
    void watchlistMutation.mutateAsync({
      ticker: cleanedTicker,
      price_alert_threshold: createWatchlistEntry(cleanedTicker).priceAlertThreshold,
      volume_alert_threshold: createWatchlistEntry(cleanedTicker).volumeAlertThreshold,
    }).catch(() => {
      queryClient.setQueryData(dashboardQueryKeys.watchlist, watchlistQuery.data);
    });
  }

  function removeTickerFromWatchlist(tickerToRemove) {
    const currentWatchlist = watchlistQuery.data?.data ?? [];
    const nextWatchlist = currentWatchlist.filter((item) => item.ticker !== tickerToRemove);
    const fallbackWatchlist = nextWatchlist.length
      ? nextWatchlist
      : [createWatchlistEntry(DEFAULT_TICKER)];

    queryClient.setQueryData(dashboardQueryKeys.watchlist, {
      ...(watchlistQuery.data || {}),
      data: fallbackWatchlist,
    });
    void deleteWatchlistMutation.mutateAsync(tickerToRemove).catch(() => {
      queryClient.setQueryData(dashboardQueryKeys.watchlist, watchlistQuery.data);
    });
  }

  function updateWatchlistThreshold(tickerToUpdate, fieldName, nextValue) {
    const normalizedValue = Number(nextValue);
    if (!Number.isFinite(normalizedValue) || normalizedValue <= 0) {
      return;
    }

    const currentWatchlist = watchlistQuery.data?.data ?? [];
    const nextWatchlist = currentWatchlist.map((item) =>
      item.ticker === tickerToUpdate
        ? { ...item, [fieldName]: normalizedValue }
        : item,
    );
    queryClient.setQueryData(dashboardQueryKeys.watchlist, {
      ...(watchlistQuery.data || {}),
      data: nextWatchlist,
    });

    const currentTickerSettings =
      currentWatchlist.find((item) => item.ticker === tickerToUpdate) ||
      createWatchlistEntry(tickerToUpdate);
    const nextWatchlistItem = {
      ticker: tickerToUpdate,
      price_alert_threshold:
        fieldName === "priceAlertThreshold"
          ? normalizedValue
          : currentTickerSettings.priceAlertThreshold || 4,
      volume_alert_threshold:
        fieldName === "volumeAlertThreshold"
          ? normalizedValue
          : currentTickerSettings.volumeAlertThreshold || 1.5,
    };
    void watchlistMutation.mutateAsync(nextWatchlistItem).catch(() => {
      queryClient.setQueryData(dashboardQueryKeys.watchlist, watchlistQuery.data);
    });
  }

  const latestTickerSummary = tickerSummary[0] || null;

  function buildPanelState({ queries, refreshKeys, empty = false }) {
    const relevantQueries = queries.filter(Boolean);
    const firstError = relevantQueries.find((query) => query.isError)?.error;
    const updatedAt = Math.max(
      ...relevantQueries.map((query) => Number(query.dataUpdatedAt || 0)),
      0,
    );

    return {
      isLoading: relevantQueries.some((query) => query.isLoading),
      isFetching: relevantQueries.some((query) => query.isFetching),
      isError: Boolean(firstError),
      error:
        firstError?.response?.data?.detail ||
        firstError?.message ||
        "",
      isStale: relevantQueries.some((query) => query.isStale),
      isEmpty: empty,
      updatedAt: updatedAt || null,
      async refresh() {
        await Promise.all(
          refreshKeys.map((queryKey) =>
            queryClient.invalidateQueries({ queryKey }),
          ),
        );
      },
    };
  }

  const panelStates = {
    shell: buildPanelState({
      queries: [healthQuery, marketSummaryQuery],
      refreshKeys: [
        dashboardQueryKeys.health,
        dashboardQueryKeys.marketSummary,
      ],
      empty: !summary.length,
    }),
    overview: buildPanelState({
      queries: [marketSummaryQuery],
      refreshKeys: [dashboardQueryKeys.marketSummary],
      empty: !summary.length,
    }),
    signals: buildPanelState({
      queries: [marketSummaryQuery, intradayMoversQuery],
      refreshKeys: [
        dashboardQueryKeys.marketSummary,
        dashboardQueryKeys.intradayMovers,
      ],
      empty: !topMovers.length && !anomalyFeed.length,
    }),
    ticker: buildPanelState({
      queries: [liveStockQuery, stockSummaryQuery, intradayCandlesQuery],
      refreshKeys: [
        dashboardQueryKeys.liveStock(activeTicker),
        dashboardQueryKeys.stockSummary(activeTicker),
        dashboardQueryKeys.intradayCandles(activeTicker),
      ],
      empty: !liveStock && !tickerSummary.length,
    }),
    news: buildPanelState({
      queries: [newsQuery, newsSummaryQuery],
      refreshKeys: [
        dashboardQueryKeys.stockNews(activeTicker),
        dashboardQueryKeys.stockNewsSummary(activeTicker),
      ],
      empty: !news.length && !newsSummary,
    }),
    watchlist: buildPanelState({
      queries: [watchlistQuery, watchlistAlertsQuery],
      refreshKeys: [
        dashboardQueryKeys.watchlist,
        dashboardQueryKeys.watchlistAlerts,
      ],
      empty: !watchlistEntries.length,
    }),
    anomalies: buildPanelState({
      queries: [anomalyHistoryQuery],
      refreshKeys: [dashboardQueryKeys.anomalyHistory],
      empty: !anomalyHistory.length,
    }),
    observability: buildPanelState({
      queries: [healthQuery, observabilityMetricsQuery],
      refreshKeys: [
        dashboardQueryKeys.health,
        dashboardQueryKeys.observabilityMetrics,
      ],
      empty:
        !Object.keys(observabilityMetrics.counters || {}).length &&
        !Object.keys(observabilityMetrics.timings || {}).length,
    }),
  };

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
    loadDashboard,
    marketLeaders,
    marketMetrics,
    marketTrend,
    news,
    newsSummary,
    newsSummaryError,
    newsSummaryLoading,
    observabilityMetrics,
    anomalyHistory,
    panelStates,
    quickTickers,
    removeTickerFromWatchlist,
    searchLoading,
    searchTicker,
    setTicker,
    summary,
    ticker,
    tickerSummary,
    tickerTrend,
    topMovers,
    triggeredAlerts,
    updateWatchlistThreshold,
    watchlistAlerts,
    watchlistEntries,
  };
}
