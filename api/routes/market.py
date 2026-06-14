import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from api.observability import PROMETHEUS_CONTENT_TYPE, render_prometheus_metrics
from api.schemas import (
    AnomalyHistoryResponse,
    AsyncJobRequest,
    AsyncJobResponse,
    DeleteResponse,
    CorrelationResponse,
    DrawdownRecoveryResponse,
    HealthResponse,
    IntradayCandlesResponse,
    IntradayMoversResponse,
    LiveStockResponse,
    MarketSummaryResponse,
    MoversResponse,
    NewsSummaryResponse,
    ObservabilityResponse,
    RiskIndicatorsResponse,
    ReadinessResponse,
    RootResponse,
    SectorPerformanceResponse,
    SignalFeatureResponse,
    SentimentTrendResponse,
    StockNewsResponse,
    StockSummaryResponse,
    VolatilityResponse,
    WatchlistAlertHistoryResponse,
    WatchlistItem,
    WatchlistResponse,
    WatchlistUpsertRequest,
)
from api.services.async_job_service import async_job_service
from api.services.market_service import market_service


router = APIRouter()


@router.get("/", response_model=RootResponse)
def root():
    return market_service.get_root_payload()


@router.get("/health", response_model=HealthResponse)
def health_check():
    try:
        return market_service.get_health()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/ready", response_model=ReadinessResponse)
def readiness_check():
    try:
        return market_service.get_readiness()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    responses={
        200: {
            "content": {
                PROMETHEUS_CONTENT_TYPE: {
                    "schema": {"type": "string"},
                },
            },
            "description": "Prometheus scrape output for API counters, gauges, and timings.",
        },
    },
)
def prometheus_metrics():
    try:
        return PlainTextResponse(
            content=render_prometheus_metrics(),
            media_type=PROMETHEUS_CONTENT_TYPE,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/market/summary", response_model=MarketSummaryResponse)
def get_market_summary():
    try:
        return market_service.get_market_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stocks/{ticker}/summary", response_model=StockSummaryResponse)
def get_stock_summary(ticker: str):
    return market_service.get_stock_summary(ticker)


@router.get("/stocks/{ticker}/live", response_model=LiveStockResponse)
def get_live_stock_data(ticker: str):
    return market_service.get_live_stock_data(ticker)


@router.get("/stocks/{ticker}/news", response_model=StockNewsResponse)
def get_stock_news(ticker: str):
    try:
        return market_service.get_stock_news(ticker)
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stocks/{ticker}/news/summary", response_model=NewsSummaryResponse)
def get_stock_news_summary(ticker: str):
    return market_service.get_stock_news_summary(ticker)


@router.post("/stocks/{ticker}/news/summary/refresh", response_model=AsyncJobResponse)
def refresh_stock_news_summary(request: Request, ticker: str):
    try:
        return async_job_service.create_news_summary_job(
            ticker=ticker,
            requested_by=request.state.principal_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/jobs/historical-backfill", response_model=AsyncJobResponse)
def create_historical_backfill_job(
    request: Request,
    payload: AsyncJobRequest | None = None,
):
    try:
        return async_job_service.create_historical_backfill_job(
            requested_by=request.state.principal_id,
            ticker=payload.ticker if payload else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/jobs/{job_id}", response_model=AsyncJobResponse)
def get_async_job(request: Request, job_id: int):
    try:
        return async_job_service.get_job(job_id, request.state.principal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/analytics/intraday/movers", response_model=IntradayMoversResponse)
def get_intraday_movers(limit: int = 12):
    try:
        return market_service.get_intraday_movers(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/intraday/{ticker}", response_model=IntradayCandlesResponse)
def get_intraday_candles(ticker: str, limit: int = 48):
    try:
        return market_service.get_intraday_candles(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/movers", response_model=MoversResponse)
def get_top_movers(limit: int = 10):
    try:
        return market_service.get_top_movers(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/volatility", response_model=VolatilityResponse)
def get_market_volatility(limit: int = 30):
    try:
        return market_service.get_market_volatility(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/sentiment/{ticker}", response_model=SentimentTrendResponse)
def get_sentiment_over_time(ticker: str, limit: int = 30):
    try:
        return market_service.get_sentiment_over_time(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/correlations/{ticker}", response_model=CorrelationResponse)
def get_ticker_correlation(ticker: str, limit: int = 8):
    try:
        return market_service.get_ticker_correlation(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/drawdowns", response_model=DrawdownRecoveryResponse)
def get_drawdown_recovery(limit: int = 30):
    try:
        return market_service.get_drawdown_recovery(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/risk", response_model=RiskIndicatorsResponse)
def get_risk_indicators(limit: int = 30):
    try:
        return market_service.get_risk_indicators(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/sectors", response_model=SectorPerformanceResponse)
def get_sector_performance(limit: int = 20):
    try:
        return market_service.get_sector_performance(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/anomalies", response_model=AnomalyHistoryResponse)
def get_anomaly_history(limit: int = 50, ticker: str | None = None):
    try:
        return market_service.get_anomaly_history(limit=limit, ticker=ticker)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/features/{ticker}", response_model=SignalFeatureResponse)
def get_signal_features(ticker: str, limit: int = 30):
    try:
        return market_service.get_signal_features(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/watchlist", response_model=WatchlistResponse)
def get_watchlist(request: Request):
    try:
        return market_service.get_watchlist(request.state.principal_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/watchlist", response_model=WatchlistItem)
def upsert_watchlist_item(request: Request, payload: WatchlistUpsertRequest):
    try:
        return market_service.upsert_watchlist_item(
            request.state.principal_id,
            payload.ticker,
            payload.price_alert_threshold,
            payload.volume_alert_threshold,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/watchlist/{ticker}", response_model=DeleteResponse)
def delete_watchlist_item(request: Request, ticker: str):
    try:
        return market_service.delete_watchlist_item(request.state.principal_id, ticker)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/watchlist/alerts", response_model=WatchlistAlertHistoryResponse)
def get_watchlist_alert_history(request: Request, limit: int = 50):
    try:
        return market_service.get_watchlist_alert_history(request.state.principal_id, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/observability/metrics", response_model=ObservabilityResponse)
def get_observability_metrics():
    try:
        return market_service.get_observability_metrics()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
