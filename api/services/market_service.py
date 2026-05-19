from datetime import datetime, timezone

import yfinance as yf
from fastapi import HTTPException

from api.repositories.market_repository import market_repository
from api.services.news_service import (
    build_fallback_summary,
    fetch_news_articles,
    is_low_quality_summary,
    summarize_news_with_local_model,
)


class MarketService:
    def __init__(self, repository):
        self.repository = repository

    def get_root_payload(self):
        return {
            "message": "Real-Time Market Intelligence API is running",
            "available_endpoints": [
                "/health",
                "/market/summary",
                "/stocks/{ticker}/summary",
                "/stocks/{ticker}/live",
                "/stocks/{ticker}/news",
                "/stocks/{ticker}/news/summary",
            ],
        }

    def get_health(self):
        result = self.repository.fetch_health_status()
        return {
            "status": "healthy",
            "database": "connected",
            "query_result": result,
        }

    def get_market_summary(self):
        rows = self.repository.fetch_market_summary()
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_stock_summary(self, ticker: str):
        normalized_ticker = ticker.upper()
        rows = self.repository.fetch_stock_summary(normalized_ticker)

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found for ticker: {normalized_ticker}",
            )

        return {
            "ticker": normalized_ticker,
            "count": len(rows),
            "data": rows,
        }

    def get_live_stock_data(self, ticker: str):
        normalized_ticker = ticker.strip().upper()

        try:
            stock = yf.Ticker(normalized_ticker)
            info = stock.fast_info

            price = info.get("last_price")
            volume = info.get("last_volume")

            if price is None:
                history = stock.history(period="5d", interval="1d")

                if history.empty:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No market data found for ticker: {normalized_ticker}",
                    )

                latest_row = history.iloc[-1]
                price = latest_row["Close"]
                volume = latest_row["Volume"]

            payload = {
                "ticker": normalized_ticker,
                "price": round(float(price), 2),
                "volume": int(volume or 0),
                "event_time": datetime.now(timezone.utc).isoformat(),
                "source": "yfinance_live_api",
            }
            self.repository.upsert_live_stock_cache(normalized_ticker, payload)
            return payload

        except HTTPException:
            raise
        except Exception as exc:
            cached_row = self.repository.get_daily_stock_search_cache(normalized_ticker)
            if cached_row and cached_row.get("live_price") is not None:
                return {
                    "ticker": normalized_ticker,
                    "price": round(float(cached_row["live_price"]), 2),
                    "volume": int(cached_row.get("live_volume") or 0),
                    "event_time": cached_row["live_event_time"].isoformat(),
                    "source": "daily_cache",
                }

            error_message = str(exc)

            if "Could not resolve host" in error_message or "curl: (6)" in error_message:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"Market data provider is unreachable for {normalized_ticker}. "
                        f"Yahoo request failed with: {error_message}"
                    ),
                )

            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch market data for {normalized_ticker}: {error_message}",
            )

    def get_stock_news(self, ticker: str):
        normalized_ticker = ticker.upper()
        cached_row = self.repository.get_daily_stock_search_cache(normalized_ticker)
        if cached_row and cached_row.get("news_articles"):
            return {
                "ticker": normalized_ticker,
                "articles": cached_row["news_articles"] or [],
                "source": "daily_cache",
            }

        articles = fetch_news_articles(normalized_ticker)
        summary = summarize_news_with_local_model(normalized_ticker, articles)
        self.repository.upsert_news_cache(normalized_ticker, articles, summary)

        return {
            "ticker": normalized_ticker,
            "articles": articles,
            "source": "newsapi",
        }

    def get_stock_news_summary(self, ticker: str):
        normalized_ticker = ticker.upper()

        try:
            cached_row = self.repository.get_daily_stock_search_cache(normalized_ticker)
            if (
                cached_row
                and cached_row.get("news_summary")
                and not is_low_quality_summary(normalized_ticker, cached_row["news_summary"])
            ):
                return {
                    "ticker": normalized_ticker,
                    "summary": cached_row["news_summary"],
                    "source": cached_row["summary_source"],
                    "model": cached_row["summary_model"],
                    "fallback_reason": cached_row["summary_fallback_reason"],
                    "article_count": len(cached_row["news_articles"] or []),
                }

            if cached_row and cached_row.get("news_articles"):
                articles = cached_row["news_articles"]
            else:
                articles = fetch_news_articles(normalized_ticker)

            summary = summarize_news_with_local_model(normalized_ticker, articles)
            self.repository.upsert_news_cache(normalized_ticker, articles, summary)
            summary["article_count"] = len(articles)
            return summary
        except HTTPException as exc:
            summary = build_fallback_summary(normalized_ticker, [], exc.detail)
            summary["article_count"] = 0
            return summary
        except Exception as exc:
            summary = build_fallback_summary(normalized_ticker, [], str(exc))
            summary["article_count"] = 0
            return summary


market_service = MarketService(market_repository)
