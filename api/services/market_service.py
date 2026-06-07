from datetime import datetime, timezone

import yfinance as yf
from fastapi import HTTPException

from api.config import settings
from api.repositories.market_repository import market_repository
from api.services.news_service import (
    build_fallback_summary,
    build_news_metrics,
    fetch_news_articles,
    is_low_quality_summary,
    summarize_news_with_local_model,
)


class MarketService:
    def __init__(self, repository):
        self.repository = repository

    def _build_cache_metadata(self, row: dict | None, expires_field: str, updated_field: str):
        return self.repository.get_cache_status(row, expires_field, updated_field)

    def _build_fresh_cache_metadata(self, ttl_minutes: int):
        expires_at = datetime.now(timezone.utc).timestamp() + (ttl_minutes * 60)
        return {
            "state": "fresh",
            "is_stale": False,
            "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stale_by_seconds": None,
        }

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
                "/analytics/movers",
                "/analytics/volatility",
                "/analytics/sentiment/{ticker}",
                "/analytics/correlations/{ticker}",
                "/analytics/drawdowns",
                "/analytics/risk",
                "/analytics/sectors",
                "/analytics/anomalies",
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
        cached_row = self.repository.get_daily_stock_search_cache(normalized_ticker)
        live_cache = self._build_cache_metadata(
            cached_row,
            "live_expires_at",
            "live_updated_at",
        )

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
                "cache": self._build_fresh_cache_metadata(settings.live_cache_ttl_minutes),
            }
            self.repository.upsert_live_stock_cache(normalized_ticker, payload)
            return payload

        except HTTPException:
            raise
        except Exception as exc:
            if (
                settings.allow_stale_cache_fallback
                and cached_row
                and cached_row.get("live_price") is not None
            ):
                return {
                    "ticker": normalized_ticker,
                    "price": round(float(cached_row["live_price"]), 2),
                    "volume": int(cached_row.get("live_volume") or 0),
                    "event_time": cached_row["live_event_time"].isoformat(),
                    "source": "daily_cache_stale",
                    "cache": live_cache,
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
        news_cache = self._build_cache_metadata(
            cached_row,
            "news_expires_at",
            "news_updated_at",
        )
        if (
            cached_row
            and cached_row.get("news_articles")
            and not news_cache["is_stale"]
        ):
            return {
                "ticker": normalized_ticker,
                "articles": cached_row["news_articles"] or [],
                "metrics": build_news_metrics(
                    normalized_ticker,
                    cached_row["news_articles"] or [],
                ),
                "source": "daily_cache",
                "cache": news_cache,
            }

        try:
            articles = fetch_news_articles(normalized_ticker)
            summary = summarize_news_with_local_model(normalized_ticker, articles)
            self.repository.upsert_news_cache(normalized_ticker, articles, summary)

            return {
                "ticker": normalized_ticker,
                "articles": articles,
                "metrics": summary.get("metrics") or build_news_metrics(normalized_ticker, articles),
                "source": "newsapi",
                "cache": self._build_fresh_cache_metadata(settings.news_cache_ttl_minutes),
            }
        except HTTPException:
            raise
        except Exception as exc:
            if settings.allow_stale_cache_fallback and cached_row and cached_row.get("news_articles"):
                return {
                    "ticker": normalized_ticker,
                    "articles": cached_row["news_articles"] or [],
                    "metrics": build_news_metrics(
                        normalized_ticker,
                        cached_row["news_articles"] or [],
                    ),
                    "source": "daily_cache_stale",
                    "cache": news_cache,
                    "fallback_reason": f"Served stale cache because refresh failed: {exc}",
                }
            raise

    def get_stock_news_summary(self, ticker: str):
        normalized_ticker = ticker.upper()

        try:
            cached_row = self.repository.get_daily_stock_search_cache(normalized_ticker)
            news_summary_cache = self._build_cache_metadata(
                cached_row,
                "news_summary_expires_at",
                "news_updated_at",
            )
            if (
                cached_row
                and cached_row.get("news_summary")
                and not news_summary_cache["is_stale"]
                and not is_low_quality_summary(normalized_ticker, cached_row["news_summary"])
            ):
                return {
                    "ticker": normalized_ticker,
                    "summary": cached_row["news_summary"],
                    "source": cached_row["summary_source"],
                    "model": cached_row["summary_model"],
                    "fallback_reason": cached_row["summary_fallback_reason"],
                    "article_count": len(cached_row["news_articles"] or []),
                    "metrics": build_news_metrics(
                        normalized_ticker,
                        cached_row["news_articles"] or [],
                    ),
                    "cache": news_summary_cache,
                }

            if cached_row and cached_row.get("news_articles"):
                articles = cached_row["news_articles"]
            else:
                articles = fetch_news_articles(normalized_ticker)

            summary = summarize_news_with_local_model(normalized_ticker, articles)
            self.repository.upsert_news_cache(normalized_ticker, articles, summary)
            summary["article_count"] = len(articles)
            summary["cache"] = self._build_fresh_cache_metadata(
                settings.news_summary_cache_ttl_minutes,
            )
            return summary
        except HTTPException as exc:
            summary = build_fallback_summary(normalized_ticker, [], exc.detail)
            summary["article_count"] = 0
            summary["cache"] = {
                "state": "miss",
                "is_stale": True,
                "expires_at": None,
                "updated_at": None,
                "stale_by_seconds": None,
            }
            return summary
        except Exception as exc:
            cached_row = self.repository.get_daily_stock_search_cache(normalized_ticker)
            news_summary_cache = self._build_cache_metadata(
                cached_row,
                "news_summary_expires_at",
                "news_updated_at",
            )
            if (
                settings.allow_stale_cache_fallback
                and cached_row
                and cached_row.get("news_summary")
                and not is_low_quality_summary(normalized_ticker, cached_row["news_summary"])
            ):
                return {
                    "ticker": normalized_ticker,
                    "summary": cached_row["news_summary"],
                    "source": "daily_cache_stale",
                    "model": cached_row["summary_model"],
                    "fallback_reason": f"Served stale cache because refresh failed: {exc}",
                    "article_count": len(cached_row["news_articles"] or []),
                    "metrics": build_news_metrics(
                        normalized_ticker,
                        cached_row["news_articles"] or [],
                    ),
                    "cache": news_summary_cache,
                }

            summary = build_fallback_summary(normalized_ticker, [], str(exc))
            summary["article_count"] = 0
            summary["cache"] = news_summary_cache
            return summary

    def get_top_movers(self, limit: int = 10):
        rows = self.repository.fetch_top_movers(limit=limit)
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_market_volatility(self, limit: int = 30):
        rows = self.repository.fetch_market_volatility(limit=limit)
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_sentiment_over_time(self, ticker: str, limit: int = 30):
        normalized_ticker = ticker.upper()
        rows = self.repository.fetch_sentiment_over_time(normalized_ticker, limit=limit)

        return {
            "ticker": normalized_ticker,
            "count": len(rows),
            "data": rows,
        }

    def get_ticker_correlation(self, ticker: str, limit: int = 8):
        normalized_ticker = ticker.upper()
        rows = self.repository.fetch_ticker_correlation(normalized_ticker, limit=limit)

        return {
            "ticker": normalized_ticker,
            "count": len(rows),
            "data": rows,
        }

    def get_drawdown_recovery(self, limit: int = 30):
        rows = self.repository.fetch_drawdown_recovery(limit=limit)
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_risk_indicators(self, limit: int = 30):
        rows = self.repository.fetch_risk_indicators(limit=limit)
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_sector_performance(self, limit: int = 20):
        rows = self.repository.fetch_sector_performance(limit=limit)
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_anomaly_history(self, limit: int = 50, ticker: str | None = None):
        normalized_ticker = ticker.upper() if ticker else None
        rows = self.repository.fetch_anomaly_history(limit=limit, ticker=normalized_ticker)
        return {
            "count": len(rows),
            "data": rows,
        }


market_service = MarketService(market_repository)
