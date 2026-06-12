from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class CacheMetadata(BaseModel):
    state: Literal["fresh", "stale", "miss"]
    is_stale: bool
    expires_at: datetime | None = None
    updated_at: datetime | None = None
    stale_by_seconds: int | None = None
    freshness_reason: str | None = None
    market_context: dict | None = None


class RootResponse(BaseModel):
    message: str
    available_endpoints: list[str]


class HealthQueryResult(BaseModel):
    status: int


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    service: str
    environment: str
    version: str
    checks: dict[str, bool]


class AsyncJobRequest(BaseModel):
    ticker: str | None = None


class AsyncJobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    payload: dict
    result: dict | None = None
    error_message: str | None = None
    requested_by: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class DailySummaryRow(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    trade_date: date
    event_count: int
    avg_price: float
    min_price: float
    max_price: float
    total_volume: int
    last_updated_at: datetime
    open_price: float
    close_price: float
    previous_close_price: float | None = None
    benchmark_close_price: float | None = None
    benchmark_price_change_pct: float | None = None
    relative_price_change_pct: float | None = None
    price_change_pct: float
    volume_vs_avg_ratio: float
    anomaly_flag: str


class MarketSummaryResponse(BaseModel):
    count: int
    data: list[DailySummaryRow]


class StockSummaryResponse(BaseModel):
    ticker: str
    count: int
    data: list[DailySummaryRow]


class LiveStockResponse(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    price: float
    volume: int
    event_time: datetime
    source: str
    market_session: str | None = None
    market_context: dict | None = None
    cache: CacheMetadata


class NewsEntity(BaseModel):
    name: str
    count: int


class NewsClusterMetric(BaseModel):
    cluster: str
    article_count: int


class NewsMetrics(BaseModel):
    ticker: str
    avg_sentiment: float
    avg_impact_score: float
    avg_source_quality_score: float
    impact_label: str
    top_entities: list[NewsEntity]
    clusters: list[NewsClusterMetric]


class NewsArticle(BaseModel):
    title: str
    description: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    source_name: str | None = None
    sentiment: float
    entities: list[NewsEntity] = Field(default_factory=list)
    source_quality_score: float
    cluster: str
    cluster_article_count: int
    impact_score: float
    impact_label: str
    content: str | None = None
    article_summary: str | None = None
    canonical_ticker: str | None = None
    company_name: str | None = None
    canonical_entity_matches: list[str] = Field(default_factory=list)


class StockNewsResponse(BaseModel):
    ticker: str
    articles: list[NewsArticle]
    metrics: NewsMetrics
    source: str
    cache: CacheMetadata
    fallback_reason: str | None = None


class NewsSummaryResponse(BaseModel):
    ticker: str
    summary: str
    source: str
    model: str | None = None
    fallback_reason: str | None = None
    article_count: int
    metrics: NewsMetrics
    cache: CacheMetadata


class MoversRow(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    trade_date: date
    close_price: float
    previous_close_price: float | None = None
    benchmark_close_price: float | None = None
    benchmark_price_change_pct: float | None = None
    relative_price_change_pct: float | None = None
    price_change_pct: float
    total_volume: int
    volume_vs_avg_ratio: float
    anomaly_flag: str


class MoversResponse(BaseModel):
    count: int
    data: list[MoversRow]


class VolatilityRow(BaseModel):
    ticker: str
    volatility_score: float | None = None
    avg_absolute_move_pct: float | None = None
    max_absolute_move_pct: float | None = None
    observed_days: int


class VolatilityResponse(BaseModel):
    count: int
    data: list[VolatilityRow]


class SentimentTrendRow(BaseModel):
    ticker: str
    cache_date: date
    avg_sentiment: float
    avg_impact_score: float
    avg_source_quality_score: float
    article_count: int


class SentimentTrendResponse(BaseModel):
    ticker: str
    count: int
    data: list[SentimentTrendRow]


class CorrelationRow(BaseModel):
    ticker: str
    correlation: float | None = None
    overlapping_days: int


class CorrelationResponse(BaseModel):
    ticker: str
    count: int
    data: list[CorrelationRow]


class DrawdownRecoveryRow(BaseModel):
    ticker: str
    trade_date: date
    close_price: float
    rolling_peak_close: float
    drawdown_pct: float
    days_since_peak: int
    recovery_status: str
    last_updated_at: datetime


class DrawdownRecoveryResponse(BaseModel):
    count: int
    data: list[DrawdownRecoveryRow]


class RiskIndicatorRow(BaseModel):
    ticker: str
    trade_date: date
    close_price: float
    price_change_pct: float
    rolling_return_7d_pct: float | None = None
    rolling_volatility_7d: float | None = None
    sharpe_like_ratio_7d: float | None = None
    observed_days: int
    last_updated_at: datetime


class RiskIndicatorsResponse(BaseModel):
    count: int
    data: list[RiskIndicatorRow]


class SectorPerformanceRow(BaseModel):
    sector: str
    trade_date: date
    ticker_count: int
    avg_price_change_pct: float
    avg_relative_price_change_pct: float | None = None
    avg_volume_ratio: float
    total_volume: int
    anomaly_count: int
    top_ticker: str
    top_ticker_price_change_pct: float


class SectorPerformanceResponse(BaseModel):
    count: int
    data: list[SectorPerformanceRow]


class AnomalyHistoryRow(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    trade_date: date
    anomaly_flag: str
    anomaly_severity_score: float
    relative_price_change_pct: float | None = None
    price_change_pct: float
    volume_vs_avg_ratio: float
    close_price: float
    total_volume: int


class AnomalyHistoryResponse(BaseModel):
    count: int
    data: list[AnomalyHistoryRow]


class IntradayCandleRow(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    interval_start: datetime
    market_session: str | None = None
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    previous_close_price: float | None = None
    benchmark_close_price: float | None = None
    benchmark_interval_change_pct: float | None = None
    relative_interval_change_pct: float | None = None
    bar_count: int
    total_volume: int
    last_updated_at: datetime


class IntradayCandlesResponse(BaseModel):
    ticker: str
    count: int
    data: list[IntradayCandleRow]


class IntradayMoverRow(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    interval_start: datetime
    market_session: str | None = None
    close_price: float
    previous_close_price: float | None = None
    interval_change_pct: float | None = None
    benchmark_interval_change_pct: float | None = None
    relative_interval_change_pct: float | None = None
    total_volume: int
    bar_count: int


class IntradayMoversResponse(BaseModel):
    count: int
    data: list[IntradayMoverRow]


class WatchlistItem(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    price_alert_threshold: float
    volume_alert_threshold: float
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WatchlistResponse(BaseModel):
    principal_id: str
    count: int
    data: list[WatchlistItem]


class WatchlistUpsertRequest(BaseModel):
    ticker: str
    price_alert_threshold: float = Field(gt=0)
    volume_alert_threshold: float = Field(gt=0)


class WatchlistAlertHistoryRow(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    trade_date: date
    close_price: float
    relative_price_change_pct: float | None = None
    price_change_pct: float
    volume_vs_avg_ratio: float
    anomaly_flag: str
    price_alert_threshold: float
    volume_alert_threshold: float
    triggered_price_alert: bool
    triggered_volume_alert: bool


class WatchlistAlertHistoryResponse(BaseModel):
    principal_id: str
    count: int
    data: list[WatchlistAlertHistoryRow]


class DeleteResponse(BaseModel):
    deleted: bool


class MetricsTimingRow(BaseModel):
    count: int
    avg_ms: float
    max_ms: float


class ObservabilityResponse(BaseModel):
    counters: dict[str, int]
    gauges: dict[str, float | int]
    timings: dict[str, MetricsTimingRow]


class SignalFeatureRow(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    benchmark_ticker: str | None = None
    benchmark_name: str | None = None
    trade_date: date
    close_price: float
    previous_close_price: float | None = None
    price_change_pct: float
    benchmark_price_change_pct: float | None = None
    relative_price_change_pct: float | None = None
    volume_vs_avg_ratio: float
    drawdown_pct: float | None = None
    rolling_return_7d_pct: float | None = None
    rolling_volatility_7d: float | None = None
    sharpe_like_ratio_7d: float | None = None
    anomaly_flag: str
    anomaly_severity_score: float
    market_regime_label: str
    signal_strength_score: float
    feature_generated_at: datetime


class SignalFeatureResponse(BaseModel):
    ticker: str
    count: int
    data: list[SignalFeatureRow]
