import requests
from fastapi import APIRouter, HTTPException

from api.services.market_service import market_service


router = APIRouter()


@router.get("/")
def root():
    return market_service.get_root_payload()


@router.get("/health")
def health_check():
    try:
        return market_service.get_health()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/market/summary")
def get_market_summary():
    try:
        return market_service.get_market_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stocks/{ticker}/summary")
def get_stock_summary(ticker: str):
    return market_service.get_stock_summary(ticker)


@router.get("/stocks/{ticker}/live")
def get_live_stock_data(ticker: str):
    return market_service.get_live_stock_data(ticker)


@router.get("/stocks/{ticker}/news")
def get_stock_news(ticker: str):
    try:
        return market_service.get_stock_news(ticker)
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stocks/{ticker}/news/summary")
def get_stock_news_summary(ticker: str):
    return market_service.get_stock_news_summary(ticker)
