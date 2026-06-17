import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Brush,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartTooltip } from "./ChartTooltip";
import { MetricCard } from "./MetricCard";
import { PanelStatus } from "./PanelStatus";
import {
  formatCompactNumber,
  formatCurrency,
  formatDate,
  formatInteger,
  formatTimestamp,
} from "../utils/dashboard";

const CHART_WINDOWS = {
  "1m": 22,
  "3m": 66,
  "6m": 132,
  max: Infinity,
};

export function TickerWorkspace({
  activeTicker,
  chartCompare,
  chartView,
  chartWindow,
  intradayCandles,
  latestTickerSummary,
  liveStock,
  onChartCompareChange,
  onChartViewChange,
  onChartWindowChange,
  onSearch,
  panelState,
  quickTickers,
  searchLoading,
  setTicker,
  ticker,
  tickerSummary,
  tickerTrend,
}) {
  const visibleTrend = useMemo(() => {
    const visibleCount = CHART_WINDOWS[chartWindow] || CHART_WINDOWS["3m"];
    if (!tickerTrend.length || visibleCount === Infinity) {
      return tickerTrend;
    }

    return tickerTrend.slice(-visibleCount);
  }, [chartWindow, tickerTrend]);
  const benchmarkLabel = tickerTrend.find((row) => row.benchmarkTicker)?.benchmarkTicker || "benchmark";
  const chartValueKey =
    chartView === "indexed" ? "indexedClosePrice" : "closePrice";
  const benchmarkValueKey =
    chartView === "indexed"
      ? "indexedBenchmarkClosePrice"
      : "benchmarkClosePrice";

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
        <div className="search-status">
          <PanelStatus state={panelState} compact />
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
          <PanelStatus state={panelState} compact />

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

          <div className="chart-controls">
            <div className="chart-control-group">
              <span>Window</span>
              {Object.keys(CHART_WINDOWS).map((windowKey) => (
                <button
                  key={windowKey}
                  className={`ticker-chip ${chartWindow === windowKey ? "active" : ""}`}
                  onClick={() => onChartWindowChange(windowKey)}
                >
                  {windowKey.toUpperCase()}
                </button>
              ))}
            </div>
            <div className="chart-control-group">
              <span>View</span>
              <button
                className={`ticker-chip ${chartView === "price" ? "active" : ""}`}
                onClick={() => onChartViewChange("price")}
              >
                Price
              </button>
              <button
                className={`ticker-chip ${chartView === "indexed" ? "active" : ""}`}
                onClick={() => onChartViewChange("indexed")}
              >
                Indexed
              </button>
            </div>
            <div className="chart-control-group">
              <span>Compare</span>
              <button
                className={`ticker-chip ${chartCompare === "none" ? "active" : ""}`}
                onClick={() => onChartCompareChange("none")}
              >
                Solo
              </button>
              <button
                className={`ticker-chip ${chartCompare === "benchmark" ? "active" : ""}`}
                onClick={() => onChartCompareChange("benchmark")}
                disabled={!tickerTrend.some((row) => row.benchmarkClosePrice > 0)}
              >
                {benchmarkLabel}
              </button>
            </div>
          </div>

          <div className="chart-wrap ticker-chart">
            {visibleTrend.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={visibleTrend}>
                  <defs>
                    <linearGradient id="tickerPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#223046" vertical={false} />
                  <XAxis dataKey="tradeDate" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                  <YAxis
                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                    tickFormatter={(value) =>
                      chartView === "indexed" ? `${Number(value || 0).toFixed(0)}` : formatCurrency(value)
                    }
                  />
                  <Tooltip
                    content={<ChartTooltip currency={chartView !== "indexed"} />}
                    cursor={{ stroke: "#38bdf8", strokeDasharray: "4 4" }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey={chartValueKey}
                    name={chartView === "indexed" ? `${activeTicker} indexed` : activeTicker}
                    stroke="#22c55e"
                    fill="url(#tickerPrice)"
                    strokeWidth={2}
                  />
                  {chartCompare === "benchmark" ? (
                    <Line
                      type="monotone"
                      dataKey={benchmarkValueKey}
                      name={
                        chartView === "indexed"
                          ? `${benchmarkLabel} indexed`
                          : benchmarkLabel
                      }
                      stroke="#38bdf8"
                      strokeWidth={2}
                      dot={false}
                    />
                  ) : null}
                  <Brush
                    dataKey="tradeDate"
                    height={24}
                    stroke="#2563eb"
                    travellerWidth={8}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty chart-empty">
                No warehouse history is available for {activeTicker}.
              </div>
            )}
          </div>

          <div className="ticker-context-grid">
            <div className="context-card">
              <span>Benchmark</span>
              <strong>{latestTickerSummary?.benchmark_ticker || "Unavailable"}</strong>
              <p>{latestTickerSummary?.benchmark_name || "No benchmark mapping returned yet."}</p>
            </div>
            <div className="context-card">
              <span>Chart source</span>
              <strong>{intradayCandles.length ? "Daily + intraday context" : "Daily summaries"}</strong>
              <p>
                {intradayCandles[0]?.last_updated_at
                  ? `Latest intraday candle ${formatTimestamp(intradayCandles[0].last_updated_at)}`
                  : "Intraday candles are unavailable for this symbol right now."}
              </p>
            </div>
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
          <PanelStatus state={panelState} compact />

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
