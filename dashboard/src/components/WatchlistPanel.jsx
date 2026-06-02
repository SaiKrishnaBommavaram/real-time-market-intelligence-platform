import {
  formatCompactNumber,
  formatCurrency,
  formatPercent,
  formatRatio,
  getAnomalyLabel,
  getPriceChangeClass,
} from "../utils/dashboard";

export function WatchlistPanel({
  activeTicker,
  onAddActiveTicker,
  onRemoveTicker,
  onSelectTicker,
  onUpdateThreshold,
  triggeredAlerts,
  watchlistEntries,
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Watchlist and alerts</h2>
          <p className="panel-subtitle">
            Track symbols with price-change and volume-spike thresholds.
          </p>
        </div>
        <button className="secondary-button" onClick={onAddActiveTicker}>
          Add {activeTicker}
        </button>
      </div>

      <div className="watchlist-alert-banner">
        <strong>{triggeredAlerts.length}</strong>
        <span>
          active alerts across {watchlistEntries.length} watched ticker
          {watchlistEntries.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="watchlist-list">
        {watchlistEntries.length ? (
          watchlistEntries.map((entry) => (
            <div className="watchlist-row" key={entry.ticker}>
              <button
                className={`watchlist-symbol ${entry.ticker === activeTicker ? "active" : ""}`}
                onClick={() => onSelectTicker(entry.ticker)}
              >
                <div>
                  <strong>{entry.ticker}</strong>
                  <span>
                    {entry.summary ? getAnomalyLabel(entry.summary.anomaly_flag) : "No summary yet"}
                  </span>
                </div>
                <span>{entry.hasAlert ? "Alerting" : "Watching"}</span>
              </button>

              <div className="watchlist-metrics">
                <div>
                  <span>Close</span>
                  <strong>{entry.summary ? formatCurrency(entry.summary.close_price) : "N/A"}</strong>
                </div>
                <div>
                  <span>Move</span>
                  <strong className={`metric-chip ${getPriceChangeClass(entry.summary?.price_change_pct)}`}>
                    {entry.summary ? formatPercent(entry.summary.price_change_pct) : "N/A"}
                  </strong>
                </div>
                <div>
                  <span>Volume</span>
                  <strong>{entry.summary ? formatRatio(entry.summary.volume_vs_avg_ratio) : "N/A"}</strong>
                </div>
                <div>
                  <span>Daily volume</span>
                  <strong>
                    {entry.summary ? formatCompactNumber(entry.summary.total_volume) : "N/A"}
                  </strong>
                </div>
              </div>

              <div className="watchlist-thresholds">
                <label>
                  <span>Price alert %</span>
                  <input
                    type="number"
                    min="0.1"
                    step="0.1"
                    value={entry.priceAlertThreshold}
                    onChange={(event) =>
                      onUpdateThreshold(entry.ticker, "priceAlertThreshold", event.target.value)
                    }
                  />
                </label>
                <label>
                  <span>Volume spike x</span>
                  <input
                    type="number"
                    min="1"
                    step="0.1"
                    value={entry.volumeAlertThreshold}
                    onChange={(event) =>
                      onUpdateThreshold(entry.ticker, "volumeAlertThreshold", event.target.value)
                    }
                  />
                </label>
                <button
                  className="secondary-button watchlist-remove"
                  onClick={() => onRemoveTicker(entry.ticker)}
                >
                  Remove
                </button>
              </div>

              <div className="watchlist-flags">
                {entry.priceAlertTriggered && (
                  <span className="summary-source fallback">Price threshold hit</span>
                )}
                {entry.volumeAlertTriggered && (
                  <span className="summary-source fallback">Volume spike</span>
                )}
                {entry.summary?.anomaly_flag && entry.summary.anomaly_flag !== "normal" && (
                  <span className="summary-source openai">
                    {getAnomalyLabel(entry.summary.anomaly_flag)}
                  </span>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="empty">No watchlist tickers configured yet.</div>
        )}
      </div>
    </section>
  );
}
