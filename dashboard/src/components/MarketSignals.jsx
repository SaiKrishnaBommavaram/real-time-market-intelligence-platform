import {
  formatCompactNumber,
  formatCurrency,
  formatDate,
  formatPercent,
  formatRatio,
  getAnomalyLabel,
  getPriceChangeClass,
} from "../utils/dashboard";

export function MarketSignals({
  activeTicker,
  anomalyFeed,
  onTickerSelect,
  topMovers,
}) {
  return (
    <section className="workspace-grid signal-grid">
      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Top movers</h2>
            <p className="panel-subtitle">
              Largest daily percentage swings from the latest warehouse snapshot.
            </p>
          </div>
        </div>

        <div className="leaders-list">
          {topMovers.length ? (
            topMovers.map((row) => (
              <button
                key={`${row.ticker}-${row.trade_date}`}
                className={`leader-row ${row.ticker === activeTicker ? "active" : ""}`}
                onClick={() => onTickerSelect(row.ticker)}
              >
                <div>
                  <strong>{row.ticker}</strong>
                  <span>{formatDate(row.trade_date)}</span>
                </div>
                <div>
                  <strong className={`metric-chip ${getPriceChangeClass(row.price_change_pct)}`}>
                    {formatPercent(row.price_change_pct)}
                  </strong>
                  <span>{formatCurrency(row.close_price || row.avg_price)}</span>
                </div>
              </button>
            ))
          ) : (
            <div className="empty">No mover data is available yet.</div>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h2>Anomaly feed</h2>
            <p className="panel-subtitle">
              Price and volume outliers surfaced from the latest daily aggregates.
            </p>
          </div>
        </div>

        <div className="leaders-list">
          {anomalyFeed.length ? (
            anomalyFeed.map((row) => (
              <button
                key={`${row.ticker}-${row.trade_date}-anomaly`}
                className={`leader-row ${row.ticker === activeTicker ? "active" : ""}`}
                onClick={() => onTickerSelect(row.ticker)}
              >
                <div>
                  <strong>{row.ticker}</strong>
                  <span>{getAnomalyLabel(row.anomaly_flag)}</span>
                </div>
                <div>
                  <strong>{formatRatio(row.volume_vs_avg_ratio)}</strong>
                  <span>{formatCompactNumber(row.total_volume)}</span>
                </div>
              </button>
            ))
          ) : (
            <div className="empty">No anomalies are flagged in the latest snapshot.</div>
          )}
        </div>
      </div>
    </section>
  );
}
