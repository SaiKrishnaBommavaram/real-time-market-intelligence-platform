import { formatRelativeTime, formatTimestamp } from "../utils/dashboard";

export function PanelStatus({ state, compact = false }) {
  if (!state) {
    return null;
  }

  const classes = ["panel-status"];
  if (compact) {
    classes.push("compact");
  }
  if (state.isError) {
    classes.push("error");
  } else if (state.isStale) {
    classes.push("stale");
  } else {
    classes.push("fresh");
  }

  const statusText = state.isError
    ? "Needs attention"
    : state.isFetching
      ? "Refreshing"
      : state.isStale
        ? "Stale"
        : "Fresh";

  return (
    <div className={classes.join(" ")}>
      <div>
        <strong>{statusText}</strong>
        <span title={state.updatedAt ? formatTimestamp(state.updatedAt) : "Never updated"}>
          {formatRelativeTime(state.updatedAt)}
        </span>
      </div>

      <div className="panel-status-actions">
        {state.isError && state.error ? <span className="panel-status-copy">{state.error}</span> : null}
        <button className="secondary-button" onClick={() => state.refresh()} disabled={state.isFetching}>
          {state.isFetching ? "Refreshing..." : "Retry"}
        </button>
      </div>
    </div>
  );
}
