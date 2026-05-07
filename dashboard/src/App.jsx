import { useEffect, useState } from "react";

import "./App.css";
import {
  fetchHealth,
  fetchStockNews,
  fetchStockNewsSummary,
  fetchMarketSummary,
  fetchLiveStock,
} from "./api";

function App() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState([]);
  const [ticker, setTicker] = useState("AAPL");
  const [liveStock, setLiveStock] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [news, setNews] = useState([]);
  const [newsSummary, setNewsSummary] = useState(null);
  const [newsSummaryLoading, setNewsSummaryLoading] = useState(false);
  const [newsSummaryError, setNewsSummaryError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const healthData = await fetchHealth();
      setHealth(healthData);
    } catch {
      setHealth(null);
    }

    try {
      const marketData = await fetchMarketSummary();
      setSummary(marketData.data || []);
    } catch (err) {
      setSummary([]);
      setError(
        err instanceof Error
          ? err.message
          : "Could not load dashboard data. Make sure FastAPI is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function searchTicker() {
    const cleanedTicker = ticker.trim().toUpperCase();

    if (!cleanedTicker) {
      setError("Please enter a ticker symbol.");
      return;
    }

    setSearchLoading(true);
    setError("");
    setNews([]);
    setNewsSummary(null);
    setNewsSummaryError("");
    setNewsSummaryLoading(true);

    try {
      const liveData = await fetchLiveStock(cleanedTicker);
      setLiveStock(liveData);
    } catch (err) {
      setLiveStock(null);
      setError(
        err?.response?.data?.detail || `No live data found for ${cleanedTicker}`,
      );
    }

    try {
      const newsData = await fetchStockNews(cleanedTicker);
      setNews(newsData.articles || []);
    } catch {
      setNews([]);
    }

    try {
      const summaryData = await fetchStockNewsSummary(cleanedTicker);
      setNewsSummary(summaryData);
    } catch {
      setNewsSummary(null);
      setNewsSummaryError("News summary is unavailable for this ticker right now.");
    } finally {
      setNewsSummaryLoading(false);
    }

    setSearchLoading(false);
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Real-Time Market Intelligence</p>
          <h1>Modern Data Platform Dashboard</h1>
          <p className="subtitle">
            Stream real market data through Kafka, transform it with dbt, serve
            it through FastAPI, and explore stock analytics in React.
          </p>
        </div>

        <div className={`status-card ${health ? "healthy" : "unhealthy"}`}>
          <span className="status-label">API Health</span>
          <strong>{health ? "Healthy" : "Unavailable"}</strong>
          <p>{health?.database || "FastAPI not connected"}</p>
          <button onClick={loadDashboard} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="loading">Loading dashboard data...</div>
      ) : (
        <>
          <section className="cards">
            <div className="card">
              <span>Warehouse Rows</span>
              <strong>{summary.length}</strong>
            </div>

            <div className="card">
              <span>Tracked Tickers</span>
              <strong>{new Set(summary.map((row) => row.ticker)).size}</strong>
            </div>

            <div className="card">
              <span>API Layer</span>
              <strong>{health ? "Online" : "Offline"}</strong>
            </div>
          </section>

          <section className="panel search-panel">
            <div>
              <h2>Search Any Stock</h2>
              <p className="panel-subtitle">
                Enter any valid ticker symbol to fetch live market data from
                yfinance. Historical summaries appear if that ticker also exists
                in the Kafka/dbt pipeline.
              </p>
            </div>

            <div className="search">
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="Example: TSLA, META, AMD"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    searchTicker();
                  }
                }}
              />
              <button onClick={searchTicker} disabled={searchLoading}>
                {searchLoading ? "Searching..." : "Search"}
              </button>
            </div>
          </section>

          {liveStock && (
            <section className="cards">
              <div className="card highlight">
                <span>Selected Ticker</span>
                <strong>{liveStock.ticker}</strong>
              </div>

              <div className="card highlight">
                <span>Live Price</span>
                <strong>${liveStock.price}</strong>
              </div>

              <div className="card highlight">
                <span>Live Volume</span>
                <strong>{Number(liveStock.volume).toLocaleString()}</strong>
              </div>
            </section>
          )}

          {(news.length > 0 || newsSummary || newsSummaryLoading || newsSummaryError) && (
            <section className="panel">
              <div className="panel-header">
                <h2>Latest News & Sentiment</h2>
              </div>

              {newsSummaryLoading && (
                <div className="summary-card">
                  <div className="summary-header">
                    <h3>News Summary</h3>
                    <span className="summary-source fallback">Generating...</span>
                  </div>

                  <p>Generating a market summary from the latest articles.</p>
                </div>
              )}

              {newsSummary && (
                <div className="summary-card">
                  <div className="summary-header">
                    <h3>News Summary</h3>
                    <span
                      className={`summary-source ${
                        newsSummary.source === "local_model" ? "openai" : "fallback"
                      }`}
                    >
                      {newsSummary.source === "local_model"
                        ? `Local ${newsSummary.model}`
                        : "Fallback summary"}
                    </span>
                  </div>

                  <p>{newsSummary.summary}</p>
                </div>
              )}

              {!newsSummaryLoading && newsSummaryError && (
                <div className="summary-card">
                  <div className="summary-header">
                    <h3>News Summary</h3>
                    <span className="summary-source fallback">Unavailable</span>
                  </div>

                  <p>{newsSummaryError}</p>
                </div>
              )}

              <div className="news-list">
                {news.map((item, idx) => (
                  <div key={idx} className="news-card">
                    <h3>{item.title}</h3>
                    <p>{item.description}</p>

                    <div className="news-footer">
                      <span className={`sentiment ${getSentimentClass(item.sentiment)}`}>
                        {item.sentiment > 0 ? "Positive" : item.sentiment < 0 ? "Negative" : "Neutral"}
                      </span>

                      <a href={item.url} target="_blank" rel="noreferrer">
                        Read →
                      </a>
                    </div>
                  </div>
                ))}
              </div>

              {!news.length && (
                <div className="empty">No news articles are available for this ticker.</div>
              )}
            </section>
          )}

        </>
      )}
    </main>
  );
}

function getSentimentClass(score) {
  if (score > 0.2) return "positive";
  if (score < -0.2) return "negative";
  return "neutral";
}

export default App;
