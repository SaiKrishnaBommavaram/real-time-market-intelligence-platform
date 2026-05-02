import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import "./App.css";
import { fetchHealth, fetchMarketSummary, fetchStockSummary } from "./api";

function App() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState([]);
  const [ticker, setTicker] = useState("AAPL");
  const [stockData, setStockData] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError("");

      const healthData = await fetchHealth();
      const marketData = await fetchMarketSummary();

      setHealth(healthData);
      setSummary(marketData.data || []);
    } catch (err) {
      setHealth(null);
      setError("Could not load dashboard data. Make sure FastAPI is running.");
    } finally {
      setLoading(false);
    }
  }

  async function searchTicker() {
    try {
      setSearchLoading(true);
      setError("");

      const data = await fetchStockSummary(ticker);
      setStockData(data.data || []);
    } catch (err) {
      setStockData([]);
      setError(`No data found for ${ticker.toUpperCase()}`);
    } finally {
      setSearchLoading(false);
    }
  }

  const chartData = useMemo(() => {
    const latestByTicker = {};

    summary.forEach((row) => {
      if (!latestByTicker[row.ticker]) {
        latestByTicker[row.ticker] = {
          ticker: row.ticker,
          avg_price: Number(row.avg_price),
        };
      }
    });

    return Object.values(latestByTicker);
  }, [summary]);

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
            Kafka streaming, PostgreSQL warehouse, dbt transformations, FastAPI
            serving, and React visualization.
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
              <span>Total Market Rows</span>
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

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Average Price by Ticker</h2>
                <p className="panel-subtitle">
                  Latest dbt-transformed daily stock summaries.
                </p>
              </div>
            </div>

            <div className="chart">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="ticker" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="avg_price" name="Average Price" fill="#60a5fa" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <h2>Search Stock Summary</h2>
              <div className="search">
                <input
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  placeholder="AAPL"
                />
                <button onClick={searchTicker} disabled={searchLoading}>
                  {searchLoading ? "Searching..." : "Search"}
                </button>
              </div>
            </div>

            <DataTable rows={stockData.length ? stockData : summary.slice(0, 10)} />
          </section>
        </>
      )}
    </main>
  );
}

function DataTable({ rows }) {
  if (!rows.length) {
    return <div className="empty">No market summary rows available yet.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Date</th>
            <th>Events</th>
            <th>Avg Price</th>
            <th>Min</th>
            <th>Max</th>
            <th>Total Volume</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.ticker}-${row.trade_date}-${index}`}>
              <td>{row.ticker}</td>
              <td>{row.trade_date}</td>
              <td>{row.event_count}</td>
              <td>${row.avg_price}</td>
              <td>${row.min_price}</td>
              <td>${row.max_price}</td>
              <td>{Number(row.total_volume).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;