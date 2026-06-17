import { DataTable } from "../DataTable";
import { PanelStatus } from "../PanelStatus";
import { WatchlistPanel } from "../WatchlistPanel";
import {
  formatCompactNumber,
  formatCurrency,
  formatDate,
  formatPercent,
  formatRatio,
  getAnomalyLabel,
} from "../../utils/dashboard";

export function WatchlistRoute({
  panelStates,
  activeTicker,
  addTickerToWatchlist,
  anomalyHistory,
  anomalySearch,
  anomalySort,
  anomalySortDirection,
  focusedTicker,
  onAnomalySearchChange,
  onAnomalySortChange,
  onFocusTicker,
  removeTickerFromWatchlist,
  searchTicker,
  triggeredAlerts,
  updateWatchlistThreshold,
  watchlistMutationState,
  watchlistEntries,
}) {
  const anomalyColumns = [
    {
      key: "ticker",
      label: "Ticker",
      accessor: (row) => row.ticker,
    },
    {
      key: "trade_date",
      label: "Date",
      accessor: (row) => row.trade_date,
      render: (row) => formatDate(row.trade_date),
    },
    {
      key: "anomaly_flag",
      label: "Flag",
      accessor: (row) => row.anomaly_flag,
      render: (row) => getAnomalyLabel(row.anomaly_flag),
    },
    {
      key: "price_change_pct",
      label: "Move",
      accessor: (row) => Number(row.price_change_pct || 0),
      render: (row) => formatPercent(row.price_change_pct),
    },
    {
      key: "volume_vs_avg_ratio",
      label: "Volume",
      accessor: (row) => Number(row.volume_vs_avg_ratio || 0),
      render: (row) => formatRatio(row.volume_vs_avg_ratio),
    },
    {
      key: "close_price",
      label: "Close",
      accessor: (row) => Number(row.close_price || 0),
      render: (row) => formatCurrency(row.close_price),
    },
    {
      key: "total_volume",
      label: "Daily volume",
      accessor: (row) => Number(row.total_volume || 0),
      render: (row) => formatCompactNumber(row.total_volume),
    },
  ];
  const filteredAnomalyHistory = focusedTicker
    ? anomalyHistory.filter((row) => row.ticker === focusedTicker)
    : anomalyHistory;

  return (
    <div className="route-grid">
      <WatchlistPanel
        activeTicker={activeTicker}
        focusedTicker={focusedTicker}
        onAddActiveTicker={() => addTickerToWatchlist(activeTicker)}
        onFocusTicker={onFocusTicker}
        onOpenTicker={searchTicker}
        onRemoveTicker={removeTickerFromWatchlist}
        onUpdateThreshold={updateWatchlistThreshold}
        panelState={panelStates.watchlist}
        triggeredAlerts={triggeredAlerts}
        watchlistMutationState={watchlistMutationState}
        watchlistEntries={watchlistEntries}
      />

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Anomaly history</h2>
            <p className="panel-subtitle">
              {focusedTicker
                ? `Virtualized anomaly log for ${focusedTicker} with sortable, shareable filters.`
                : "Virtualized anomaly log with sorting, filtering, and column controls."}
            </p>
          </div>
        </div>
        <PanelStatus state={panelStates.anomalies} compact />
        <DataTable
          rows={filteredAnomalyHistory}
          columns={anomalyColumns}
          searchPlaceholder="Filter anomaly history"
          emptyMessage="No anomaly history is available yet."
          rowKey={(row) => `${row.ticker}-${row.trade_date}-${row.anomaly_flag}`}
          initialSortKey="trade_date"
          height={440}
          searchTerm={anomalySearch}
          sortDirection={anomalySortDirection}
          sortKey={anomalySort}
          onSearchTermChange={onAnomalySearchChange}
          onSortChange={onAnomalySortChange}
        />
      </section>
    </div>
  );
}
