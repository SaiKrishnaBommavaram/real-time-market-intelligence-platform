import { DataTable } from "../DataTable";
import { MetricCard } from "../MetricCard";
import { PanelStatus } from "../PanelStatus";
import { formatCompactNumber } from "../../utils/dashboard";

function buildCounterRows(counters) {
  return Object.entries(counters || {}).map(([metric, value]) => ({
    metric,
    value,
  }));
}

function buildTimingRows(timings) {
  return Object.entries(timings || {}).map(([metric, stats]) => ({
    metric,
    count: stats.count,
    avg_ms: stats.avg_ms,
    max_ms: stats.max_ms,
  }));
}

export function ObservabilityRoute({ observabilityMetrics, panelStates }) {
  const counterRows = buildCounterRows(observabilityMetrics.counters);
  const timingRows = buildTimingRows(observabilityMetrics.timings);
  const gauges = observabilityMetrics.gauges || {};
  const requestCount = observabilityMetrics.counters?.["api.request.total"] || 0;
  const requestErrors = observabilityMetrics.counters?.["api.request.error"] || 0;
  const staleFallbacks = Object.entries(observabilityMetrics.counters || {})
    .filter(([metric]) => metric.includes("stale_fallback"))
    .reduce((sum, [, value]) => sum + Number(value || 0), 0);

  return (
    <>
      <section className="metric-grid">
        <MetricCard
          label="Requests observed"
          value={formatCompactNumber(requestCount)}
          detail={`${formatCompactNumber(requestErrors)} failures tracked`}
        />
        <MetricCard
          label="Last producer batch"
          value={formatCompactNumber(gauges["producer.last_batch_size"] || 0)}
          detail="Most recent producer send volume"
        />
        <MetricCard
          label="Stale fallbacks"
          value={formatCompactNumber(staleFallbacks)}
          detail="Cache rescue events"
        />
        <MetricCard
          label="Tracked timings"
          value={formatCompactNumber(timingRows.length)}
          detail="Latency metric families"
        />
      </section>

      <section className="route-grid route-grid-observability">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Counter stream</h2>
              <p className="panel-subtitle">
                Request, auth, cache, and pipeline counters from the live metrics snapshot.
              </p>
            </div>
          </div>
          <PanelStatus state={panelStates.observability} compact />
          <DataTable
            rows={counterRows}
            columns={[
              { key: "metric", label: "Metric", accessor: (row) => row.metric },
              { key: "value", label: "Value", accessor: (row) => Number(row.value || 0) },
            ]}
            searchPlaceholder="Filter counters"
            emptyMessage="No counters reported yet."
            rowKey={(row) => row.metric}
            initialSortKey="value"
            height={380}
          />
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Timing metrics</h2>
              <p className="panel-subtitle">
                Latency samples with sortable averages and max timings.
              </p>
            </div>
          </div>
          <PanelStatus state={panelStates.observability} compact />
          <DataTable
            rows={timingRows}
            columns={[
              { key: "metric", label: "Metric", accessor: (row) => row.metric },
              { key: "count", label: "Count", accessor: (row) => Number(row.count || 0) },
              { key: "avg_ms", label: "Avg ms", accessor: (row) => Number(row.avg_ms || 0) },
              { key: "max_ms", label: "Max ms", accessor: (row) => Number(row.max_ms || 0) },
            ]}
            searchPlaceholder="Filter timings"
            emptyMessage="No timing metrics reported yet."
            rowKey={(row) => row.metric}
            initialSortKey="avg_ms"
            height={380}
          />
        </section>
      </section>
    </>
  );
}
