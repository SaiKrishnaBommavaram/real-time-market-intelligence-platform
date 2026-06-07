import requests
from fastapi import APIRouter, HTTPException

from api.schemas import (
    AnomalyHistoryResponse,
    CorrelationResponse,
    DrawdownRecoveryResponse,
    HealthResponse,
    LiveStockResponse,
    MarketSummaryResponse,
    MoversResponse,
    NewsSummaryResponse,
    RiskIndicatorsResponse,
    RootResponse,
    SectorPerformanceResponse,
    SentimentTrendResponse,
    StockNewsResponse,
    StockSummaryResponse,
    VolatilityResponse,
)
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
