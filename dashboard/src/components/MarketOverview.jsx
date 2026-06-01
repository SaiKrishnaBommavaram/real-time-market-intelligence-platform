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
} from "../utils/dashboard";

export function MarketOverview({
  activeTicker,
  marketLeaders,
  marketMetrics,
  marketTrend,
  onTickerSelect,
  summary,
}) {
  return (
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
              <div className="empty chart-empty">No warehouse summary rows are available yet.</div>
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
                  className={`leader-row ${row.ticker === activeTicker ? "active" : ""}`}
                  onClick={() => onTickerSelect(row.ticker)}
                >
                  <div>
                    <strong>{row.ticker}</strong>
                    <span>{formatDate(row.trade_date)}</span>
                  </div>
                  <div>
                    <strong>{formatCompactNumber(row.total_volume)}</strong>
                    <span>{formatCurrency(row.avg_price)}</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="empty">No leaders available.</div>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
