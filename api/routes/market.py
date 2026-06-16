import requests
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import PlainTextResponse

from api.observability import PROMETHEUS_CONTENT_TYPE, render_prometheus_metrics
from api.schemas import (
    AnomalyHistoryResponse,
    AsyncJobRequest,
    AsyncJobResponse,
    BenchmarkRelativeStrengthResponse,
    CacheAdminRequest,
    CacheAdminResponse,
    CorrelationResponse,
    DeleteResponse,
    DrawdownRecoveryResponse,
    HealthResponse,
    IntradayCandlesResponse,
    IntradayMoversResponse,
    LiveStockResponse,
    MarketSummaryResponse,
    MarketRegimeSummaryResponse,
    MoversResponse,
    NewsSummaryResponse,
    ObservabilityResponse,
    ReadinessResponse,
    RiskIndicatorsResponse,
    RootResponse,
    SectorPerformanceResponse,
    SentimentTrendResponse,
    SignalFeatureResponse,
    StockNewsResponse,
    StockSummaryResponse,
    TickerPattern,
    VolatilityResponse,
    WatchlistAlertHistoryResponse,
    WatchlistItem,
    WatchlistResponse,
    WatchlistUpsertRequest,
)
from api.services.async_job_service import async_job_service
from api.services.market_service import market_service


router = APIRouter()

TickerPath = Annotated[str, Path(pattern=TickerPattern)]
TickerQuery = Annotated[str | None, Query(default=None, pattern=TickerPattern)]
SmallLimitQuery = Annotated[int, Query(ge=1, le=100)]
MediumLimitQuery = Annotated[int, Query(ge=1, le=250)]
IntradayLimitQuery = Annotated[int, Query(ge=1, le=390)]
JobIdPath = Annotated[int, Path(ge=1)]


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
async def readiness_check():
    try:
        return await market_service.get_readiness()
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
async def get_market_summary():
    try:
        return await market_service.get_market_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stocks/{ticker}/summary", response_model=StockSummaryResponse)
async def get_stock_summary(ticker: TickerPath):
    return await market_service.get_stock_summary(ticker)


@router.get("/stocks/{ticker}/live", response_model=LiveStockResponse)
async def get_live_stock_data(ticker: TickerPath):
    return await market_service.get_live_stock_data(ticker)


@router.get("/stocks/{ticker}/news", response_model=StockNewsResponse)
async def get_stock_news(ticker: TickerPath):
    try:
        return await market_service.get_stock_news(ticker)
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stocks/{ticker}/news/summary", response_model=NewsSummaryResponse)
async def get_stock_news_summary(ticker: TickerPath):
    return await market_service.get_stock_news_summary(ticker)


@router.post("/stocks/{ticker}/news/summary/refresh", response_model=AsyncJobResponse)
async def refresh_stock_news_summary(request: Request, ticker: TickerPath):
    try:
        return await async_job_service.create_news_summary_job(
            ticker=ticker,
            requested_by=request.state.principal_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/jobs/historical-backfill", response_model=AsyncJobResponse)
async def create_historical_backfill_job(
    request: Request,
    payload: AsyncJobRequest | None = None,
):
    try:
        return await async_job_service.create_historical_backfill_job(
            requested_by=request.state.principal_id,
            ticker=payload.ticker if payload else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/jobs/{job_id}", response_model=AsyncJobResponse)
async def get_async_job(request: Request, job_id: JobIdPath):
    try:
        return await async_job_service.get_job(job_id, request.state.principal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/analytics/intraday/movers", response_model=IntradayMoversResponse)
async def get_intraday_movers(limit: SmallLimitQuery = 12):
    try:
        return await market_service.get_intraday_movers(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/intraday/{ticker}", response_model=IntradayCandlesResponse)
async def get_intraday_candles(ticker: TickerPath, limit: IntradayLimitQuery = 48):
    try:
        return await market_service.get_intraday_candles(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/movers", response_model=MoversResponse)
async def get_top_movers(limit: SmallLimitQuery = 10):
    try:
        return await market_service.get_top_movers(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/volatility", response_model=VolatilityResponse)
async def get_market_volatility(limit: SmallLimitQuery = 30):
    try:
        return await market_service.get_market_volatility(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/sentiment/{ticker}", response_model=SentimentTrendResponse)
async def get_sentiment_over_time(ticker: TickerPath, limit: MediumLimitQuery = 30):
    try:
        return await market_service.get_sentiment_over_time(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/correlations/{ticker}", response_model=CorrelationResponse)
async def get_ticker_correlation(ticker: TickerPath, limit: SmallLimitQuery = 8):
    try:
        return await market_service.get_ticker_correlation(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/drawdowns", response_model=DrawdownRecoveryResponse)
async def get_drawdown_recovery(limit: SmallLimitQuery = 30):
    try:
        return await market_service.get_drawdown_recovery(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/risk", response_model=RiskIndicatorsResponse)
async def get_risk_indicators(limit: SmallLimitQuery = 30):
    try:
        return await market_service.get_risk_indicators(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/sectors", response_model=SectorPerformanceResponse)
async def get_sector_performance(limit: SmallLimitQuery = 20):
    try:
        return await market_service.get_sector_performance(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/benchmarks", response_model=BenchmarkRelativeStrengthResponse)
async def get_benchmark_relative_strength(limit: SmallLimitQuery = 20):
    try:
        return await market_service.get_benchmark_relative_strength(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/regimes", response_model=MarketRegimeSummaryResponse)
async def get_market_regime_summary(limit: SmallLimitQuery = 30):
    try:
        return await market_service.get_market_regime_summary(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/anomalies", response_model=AnomalyHistoryResponse)
async def get_anomaly_history(limit: MediumLimitQuery = 50, ticker: TickerQuery = None):
    try:
        return await market_service.get_anomaly_history(limit=limit, ticker=ticker)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/features/{ticker}", response_model=SignalFeatureResponse)
async def get_signal_features(ticker: TickerPath, limit: MediumLimitQuery = 30):
    try:
        return await market_service.get_signal_features(ticker, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist(request: Request):
    try:
        return await market_service.get_watchlist(request.state.principal_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/watchlist", response_model=WatchlistItem)
async def upsert_watchlist_item(request: Request, payload: WatchlistUpsertRequest):
    try:
        return await market_service.upsert_watchlist_item(
            request.state.principal_id,
            payload.ticker,
            payload.price_alert_threshold,
            payload.volume_alert_threshold,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/watchlist/{ticker}", response_model=DeleteResponse)
async def delete_watchlist_item(request: Request, ticker: TickerPath):
    try:
        return await market_service.delete_watchlist_item(request.state.principal_id, ticker)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/watchlist/alerts", response_model=WatchlistAlertHistoryResponse)
async def get_watchlist_alert_history(request: Request, limit: MediumLimitQuery = 50):
    try:
        return await market_service.get_watchlist_alert_history(request.state.principal_id, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/observability/metrics", response_model=ObservabilityResponse)
def get_observability_metrics():
    try:
        return market_service.get_observability_metrics()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/admin/cache/invalidate", response_model=CacheAdminResponse)
async def invalidate_cache(payload: CacheAdminRequest):
    try:
        result = await market_service.invalidate_cache(payload.ticker, payload.scopes)
        return {
            "ticker": result["ticker"],
            "scopes": result["scopes"],
            "invalidated": result["outcome"]["invalidated"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/admin/cache/refresh", response_model=CacheAdminResponse)
async def refresh_cache(payload: CacheAdminRequest):
    try:
        return await market_service.refresh_cache(payload.ticker, payload.scopes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
