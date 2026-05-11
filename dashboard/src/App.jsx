import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import "./App.css";
import {
  fetchHealth,
  fetchLiveStock,
  fetchMarketSummary,
  fetchStockNews,
  fetchStockNewsSummary,
  fetchStockSummary,
} from "./api";

const DEFAULT_TICKER = "AAPL";

function App() {
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
    async function initialize() {
      await Promise.all([loadDashboard(), searchTicker(DEFAULT_TICKER)]);
    }

    void initialize();
  }, [loadDashboard, searchTicker]);

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
          <section className="metric-grid">
            <MetricCard
              label="Warehouse rows"
              value={formatInteger(summary.length)}
              detail={`${marketMetrics.dayCount} market days`}
            />
            <MetricCard
              label="Tracked tickers"
              value={formatInteger(marketMetrics.tickerCount)}
              detail={`Top: ${marketLeaders[0]?.ticker || "N/A"}`}
            />
            <MetricCard
              label="Aggregate volume"
              value={formatCompactNumber(marketMetrics.totalVolume)}
              detail="Across loaded summary rows"
            />
            <MetricCard
              label="Average close"
              value={formatCurrency(marketMetrics.avgPrice)}
              detail="Mean warehouse price"
            />
          </section>

          <section className="workspace-grid">
            <div className="panel chart-panel">
              <div className="panel-header">
                <div>
                  <h2>Market activity</h2>
                  <p className="panel-subtitle">
                    Daily warehouse volume and mean price across transformed rows.
                  </p>
                </div>
              </div>

              <div className="chart-wrap">
                {marketTrend.length ? (
                  <ResponsiveContainer width="100%" height={320}>
                    <AreaChart data={marketTrend}>
                      <defs>
                        <linearGradient id="marketVolume" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#223046" vertical={false} />
                      <XAxis dataKey="tradeDate" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                      <YAxis
                        yAxisId="left"
                        tick={{ fill: "#94a3b8", fontSize: 12 }}
                        tickFormatter={formatCompactNumber}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        tick={{ fill: "#94a3b8", fontSize: 12 }}
                        tickFormatter={(value) => `$${value}`}
                      />
                      <Tooltip content={<ChartTooltip />} />
                      <Area
                        yAxisId="left"
                        type="monotone"
                        dataKey="totalVolume"
                        stroke="#38bdf8"
                        fill="url(#marketVolume)"
                        strokeWidth={2}
                      />
                      <Area
                        yAxisId="right"
                        type="monotone"
                        dataKey="avgPrice"
                        stroke="#f59e0b"
                        fillOpacity={0}
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="empty chart-empty">
                    No warehouse summary rows are available yet.
                  </div>
                )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>Volume leaders</h2>
                  <p className="panel-subtitle">
                    Highest-volume tickers from the current warehouse snapshot.
                  </p>
                </div>
              </div>

              <div className="leaders-list">
                {marketLeaders.length ? (
                  marketLeaders.map((row) => (
                    <button
                      key={row.ticker}
                      className={`leader-row ${
                        row.ticker === activeTicker ? "active" : ""
                      }`}
                      onClick={() => searchTicker(row.ticker)}
                    >
                      <div>
                        <strong>{row.ticker}</strong>
                        <span>{formatDate(row.tradeDate)}</span>
                      </div>
                      <div>
                        <strong>{formatCompactNumber(row.totalVolume)}</strong>
                        <span>{formatCurrency(row.avgPrice)}</span>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="empty">No leaders available.</div>
                )}
              </div>
            </div>
          </section>

          <section className="panel search-panel">
            <div className="search-copy">
              <h2>Ticker workspace</h2>
              <p className="panel-subtitle">
                Live quote, warehouse history, and current news sentiment for one symbol.
              </p>
              <div className="quick-tickers">
                {quickTickers.map((symbol) => (
                  <button
                    key={symbol}
                    className={`ticker-chip ${symbol === activeTicker ? "active" : ""}`}
                    onClick={() => searchTicker(symbol)}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>

            <div className="search-box">
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="Example: TSLA, META, AMD"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    searchTicker();
                  }
                }}
              />
              <button onClick={() => searchTicker()} disabled={searchLoading}>
                {searchLoading ? "Searching..." : "Load ticker"}
              </button>
            </div>
          </section>

          <section className="workspace-grid">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>{activeTicker} snapshot</h2>
                  <p className="panel-subtitle">
                    Live quote from Yahoo Finance with warehouse context when available.
                  </p>
                </div>
              </div>

              <div className="metric-grid compact">
                <MetricCard
                  label="Live price"
                  value={liveStock ? formatCurrency(liveStock.price) : "N/A"}
                  detail={liveStock?.source || "Live feed unavailable"}
                  highlight
                />
                <MetricCard
                  label="Live volume"
                  value={
                    liveStock ? formatInteger(Number(liveStock.volume || 0)) : "N/A"
                  }
                  detail={
                    liveStock?.event_time
                      ? `Updated ${formatTimestamp(liveStock.event_time)}`
                      : "No update time"
                  }
                  highlight
                />
                <MetricCard
                  label="Warehouse events"
                  value={
                    latestTickerSummary
                      ? formatInteger(Number(latestTickerSummary.event_count || 0))
                      : "N/A"
                  }
                  detail={
                    latestTickerSummary
                      ? formatDate(latestTickerSummary.trade_date)
                      : "No dbt summary for this ticker"
                  }
                />
                <MetricCard
                  label="Warehouse range"
                  value={
                    latestTickerSummary
                      ? `${formatCurrency(latestTickerSummary.min_price)} - ${formatCurrency(
                          latestTickerSummary.max_price,
                        )}`
                      : "N/A"
                  }
                  detail={
                    latestTickerSummary
                      ? `Avg ${formatCurrency(latestTickerSummary.avg_price)}`
                      : "No price band available"
                  }
                />
              </div>

              <div className="chart-wrap ticker-chart">
                {tickerTrend.length ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={tickerTrend}>
                      <defs>
                        <linearGradient id="tickerPrice" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#223046" vertical={false} />
                      <XAxis dataKey="tradeDate" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                      <Tooltip content={<ChartTooltip currency />} />
                      <Area
                        type="monotone"
                        dataKey="avgPrice"
                        stroke="#22c55e"
                        fill="url(#tickerPrice)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="empty chart-empty">
                    No warehouse history is available for {activeTicker}.
                  </div>
                )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>{activeTicker} warehouse history</h2>
                  <p className="panel-subtitle">
                    Most recent transformed daily summaries for the selected ticker.
                  </p>
                </div>
              </div>

              <div className="history-table">
                <div className="table-head">
                  <span>Date</span>
                  <span>Avg</span>
                  <span>Range</span>
                  <span>Volume</span>
                </div>
                {tickerSummary.length ? (
                  tickerSummary.slice(0, 6).map((row) => (
                    <div className="table-row" key={`${row.ticker}-${row.trade_date}`}>
                      <span>{formatDate(row.trade_date)}</span>
                      <span>{formatCurrency(row.avg_price)}</span>
                      <span>
                        {formatCurrency(row.min_price)} - {formatCurrency(row.max_price)}
                      </span>
                      <span>{formatCompactNumber(row.total_volume)}</span>
                    </div>
                  ))
                ) : (
                  <div className="empty">No warehouse history is available.</div>
                )}
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Latest news and sentiment</h2>
                <p className="panel-subtitle">
                  Article sentiment with an aggregated summary for {activeTicker}.
                </p>
              </div>
            </div>

            {newsSummaryLoading && (
              <div className="summary-card">
                <div className="summary-header">
                  <h3>News summary</h3>
                  <span className="summary-source fallback">Generating</span>
                </div>
                <p>Building a summary from the latest articles.</p>
              </div>
            )}

            {newsSummary && (
              <div className="summary-card">
                <div className="summary-header">
                  <h3>News summary</h3>
                  <span
                    className={`summary-source ${
                      newsSummary.source === "local_model" ? "openai" : "fallback"
                    }`}
                  >
                    {newsSummary.source === "local_model"
                      ? `Local ${newsSummary.model}`
                      : "Fallback"}
                  </span>
                </div>
                <p>{newsSummary.summary}</p>
              </div>
            )}

            {!newsSummaryLoading && newsSummaryError && (
              <div className="summary-card">
                <div className="summary-header">
                  <h3>News summary</h3>
                  <span className="summary-source fallback">Unavailable</span>
                </div>
                <p>{newsSummaryError}</p>
              </div>
            )}

            <div className="news-list">
              {news.length ? (
                news.map((item, idx) => (
                  <article key={`${item.url}-${idx}`} className="news-card">
                    <div className="news-header">
                      <h3>{item.title}</h3>
                      <span className={`sentiment ${getSentimentClass(item.sentiment)}`}>
                        {getSentimentLabel(item.sentiment)}
                      </span>
                    </div>
                    <p>{item.description || "No article summary provided."}</p>
                    <div className="news-footer">
                      <span>Score {Number(item.sentiment || 0).toFixed(2)}</span>
                      <a href={item.url} target="_blank" rel="noreferrer">
                        Open article
                      </a>
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty">No news articles are available for this ticker.</div>
              )}
            </div>
          </section>
        </>
      )}
    </main>
  );
}

function MetricCard({ label, value, detail, highlight = false }) {
  return (
    <div className={`metric-card ${highlight ? "highlight" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </div>
  );
}

function ChartTooltip({ active, payload, label, currency = false }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="tooltip-row">
          <span>{entry.name || entry.dataKey}</span>
          <span>
            {currency ? formatCurrency(entry.value) : formatTooltipValue(entry.dataKey, entry.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

function buildMarketMetrics(rows) {
  if (!rows.length) {
    return {
      tickerCount: 0,
      dayCount: 0,
      totalVolume: 0,
      avgPrice: 0,
    };
  }

  const tickerCount = new Set(rows.map((row) => row.ticker)).size;
  const dayCount = new Set(rows.map((row) => row.trade_date)).size;
  const totalVolume = rows.reduce(
    (sum, row) => sum + Number(row.total_volume || 0),
    0,
  );
  const avgPrice =
    rows.reduce((sum, row) => sum + Number(row.avg_price || 0), 0) / rows.length;

  return { tickerCount, dayCount, totalVolume, avgPrice };
}

function buildMarketTrend(rows) {
  const grouped = rows.reduce((acc, row) => {
    const date = row.trade_date;
    if (!acc[date]) {
      acc[date] = {
        tradeDate: date,
        rawDate: new Date(date).getTime(),
        totalVolume: 0,
        avgPriceSum: 0,
        count: 0,
      };
    }

    acc[date].totalVolume += Number(row.total_volume || 0);
    acc[date].avgPriceSum += Number(row.avg_price || 0);
    acc[date].count += 1;
    return acc;
  }, {});

  return Object.values(grouped)
    .sort((a, b) => a.rawDate - b.rawDate)
    .map((row) => ({
      tradeDate: shortDate(row.tradeDate),
      totalVolume: row.totalVolume,
      avgPrice: Number((row.avgPriceSum / row.count).toFixed(2)),
    }));
}

function buildMarketLeaders(rows) {
  const latestByTicker = rows.reduce((acc, row) => {
    const current = acc[row.ticker];
    if (!current || new Date(row.trade_date) > new Date(current.trade_date)) {
      acc[row.ticker] = row;
    }
    return acc;
  }, {});

  return Object.values(latestByTicker)
    .sort((a, b) => Number(b.total_volume || 0) - Number(a.total_volume || 0))
    .slice(0, 6);
}

function buildTickerTrend(rows) {
  return [...rows]
    .map((row) => ({
      tradeDate: shortDate(row.trade_date),
      avgPrice: Number(row.avg_price || 0),
    }))
    .reverse();
}

function formatInteger(value) {
  return Number(value || 0).toLocaleString();
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value || 0));
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

function formatDate(value) {
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function shortDate(value) {
  const date = new Date(value);
  return `${date.toLocaleDateString("en-US", { month: "short" })} ${date.getDate()}`;
}

function formatTimestamp(value) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatTooltipValue(key, value) {
  if (key?.toLowerCase().includes("price")) {
    return formatCurrency(value);
  }

  return formatCompactNumber(value);
}

function getSentimentClass(score) {
  if (score > 0.2) return "positive";
  if (score < -0.2) return "negative";
  return "neutral";
}

function getSentimentLabel(score) {
  if (score > 0.2) return "Positive";
  if (score < -0.2) return "Negative";
  return "Neutral";
}

export default App;
