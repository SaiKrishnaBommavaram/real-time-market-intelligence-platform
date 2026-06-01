import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartTooltip } from "./ChartTooltip";
import { MetricCard } from "./MetricCard";
import {
  formatCompactNumber,
  formatCurrency,
  formatDate,
  formatInteger,
  formatTimestamp,
} from "../utils/dashboard";

export function TickerWorkspace({
  activeTicker,
  latestTickerSummary,
  liveStock,
  onSearch,
  quickTickers,
  searchLoading,
  setTicker,
  ticker,
  tickerSummary,
  tickerTrend,
}) {
  return (
    <>
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
                onClick={() => onSearch(symbol)}
              >
                {symbol}
              </button>
            ))}
          </div>
        </div>

        <div className="search-box">
          <input
            value={ticker}
            onChange={(event) => setTicker(event.target.value.toUpperCase())}
            placeholder="Example: TSLA, META, AMD"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                onSearch();
              }
            }}
          />
          <button onClick={() => onSearch()} disabled={searchLoading}>
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
              value={liveStock ? formatInteger(Number(liveStock.volume || 0)) : "N/A"}
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
    </>
  );
}
