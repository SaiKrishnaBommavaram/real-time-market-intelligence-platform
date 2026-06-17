import {
  formatCompactNumber,
  formatCurrency,
  formatPercent,
  formatRelativeTime,
  formatRatio,
  getAnomalyLabel,
  getPriceChangeClass,
} from "../utils/dashboard";
import { PanelStatus } from "./PanelStatus";

export function WatchlistPanel({
  activeTicker,
  focusedTicker,
  onAddActiveTicker,
  onFocusTicker,
  onOpenTicker,
  onRemoveTicker,
  onUpdateThreshold,
  panelState,
  triggeredAlerts,
  watchlistMutationState,
  watchlistEntries,
}) {
  const activeMutation = watchlistMutationState?.[activeTicker];
  const addButtonLabel =
    activeMutation?.state === "saving"
      ? `Adding ${activeTicker}...`
      : `Add ${activeTicker}`;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Watchlist and alerts</h2>
          <p className="panel-subtitle">
            Track symbols with price-change and volume-spike thresholds.
          </p>
        </div>
        <button
          className="secondary-button"
          onClick={onAddActiveTicker}
          disabled={activeMutation?.state === "saving"}
        >
          {addButtonLabel}
        </button>
      </div>
      <PanelStatus state={panelState} compact />

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
              {watchlistMutationState?.[entry.ticker] ? (
                <div
                  className={`watchlist-sync watchlist-sync-${watchlistMutationState[entry.ticker].state}`}
                >
                  <span>{watchlistMutationState[entry.ticker].message}</span>
                  <span>{formatRelativeTime(watchlistMutationState[entry.ticker].updatedAt)}</span>
                </div>
              ) : null}

              <button
                className={`watchlist-symbol ${entry.ticker === (focusedTicker || activeTicker) ? "active" : ""}`}
                onClick={() => onFocusTicker(entry.ticker)}
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
                    disabled={watchlistMutationState?.[entry.ticker]?.state === "removing"}
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
                    disabled={watchlistMutationState?.[entry.ticker]?.state === "removing"}
                    onChange={(event) =>
                      onUpdateThreshold(entry.ticker, "volumeAlertThreshold", event.target.value)
                    }
                  />
                </label>
                <button
                  className="secondary-button"
                  onClick={() => onOpenTicker(entry.ticker)}
                  disabled={watchlistMutationState?.[entry.ticker]?.state === "removing"}
                >
                  Open ticker
                </button>
                <button
                  className="secondary-button watchlist-remove"
                  onClick={() => onRemoveTicker(entry.ticker)}
                  disabled={watchlistMutationState?.[entry.ticker]?.state === "removing"}
                >
                  {watchlistMutationState?.[entry.ticker]?.state === "removing"
                    ? "Removing..."
                    : "Remove"}
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
