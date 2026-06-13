import {
  getSentimentClass,
  getSentimentLabel,
} from "../utils/dashboard";
import { PanelStatus } from "./PanelStatus";

export function NewsPanel({
  activeTicker,
  news,
  panelState,
  newsSummary,
  newsSummaryError,
  newsSummaryLoading,
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Latest news and sentiment</h2>
          <p className="panel-subtitle">
            Article sentiment with an aggregated summary for {activeTicker}.
          </p>
        </div>
      </div>
      <PanelStatus state={panelState} compact />

      {newsSummaryLoading && (
        <div className="summary-card">
          <div className="summary-header">
            <h3>News summary</h3>
            <span className="summary-source fallback">Generating</span>
          </div>
          <p>Building a summary from the latest articles.</p>
        </div>
      )}

      {newsSummary && (
        <div className="summary-card">
          <div className="summary-header">
            <h3>News summary</h3>
            <span
              className={`summary-source ${
                newsSummary.source === "local_model" ? "openai" : "fallback"
              }`}
            >
              {newsSummary.source === "local_model"
                ? `Local ${newsSummary.model}`
                : "Fallback"}
            </span>
          </div>
          <p>{newsSummary.summary}</p>
        </div>
      )}

      {!newsSummaryLoading && newsSummaryError && (
        <div className="summary-card">
          <div className="summary-header">
            <h3>News summary</h3>
            <span className="summary-source fallback">Unavailable</span>
          </div>
          <p>{newsSummaryError}</p>
        </div>
      )}

      <div className="news-list">
        {news.length ? (
          news.map((item, idx) => (
            <article key={`${item.url}-${idx}`} className="news-card">
              <div className="news-header">
                <h3>{item.title}</h3>
                <span className={`sentiment ${getSentimentClass(item.sentiment)}`}>
                  {getSentimentLabel(item.sentiment)}
                </span>
              </div>
              <p>{item.description || "No article summary provided."}</p>
              <div className="news-footer">
                <span>Score {Number(item.sentiment || 0).toFixed(2)}</span>
                <a href={item.url} target="_blank" rel="noreferrer">
                  Open article
                </a>
              </div>
            </article>
          ))
        ) : (
          <div className="empty">No news articles are available for this ticker.</div>
        )}
      </div>
    </section>
  );
}
