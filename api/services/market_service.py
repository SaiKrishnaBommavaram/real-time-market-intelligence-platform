from datetime import datetime, timezone

import yfinance as yf
from fastapi import HTTPException

from api.config import settings
from api.observability import get_metrics_snapshot, increment_metric
from api.repositories.market_repository import market_repository
from api.services.news_service import (
    build_fallback_summary,
    build_news_metrics,
    fetch_news_articles,
    is_low_quality_summary,
    summarize_news_with_local_model,
)
from market_calendar import get_market_calendar_context, infer_market_session, serialize_market_context
from market_symbols import get_symbol_profile, normalize_ticker


class MarketService:
    def __init__(self, repository):
        self.repository = repository

    def _build_cache_metadata(self, row: dict | None, expires_field: str, updated_field: str):
        return self.repository.get_cache_status(row, expires_field, updated_field)

    def _build_fresh_cache_metadata(self, ttl_minutes: int):
        market_context = get_market_calendar_context()
        expires_at = datetime.now(timezone.utc).timestamp() + (ttl_minutes * 60)
        return {
            "state": "fresh",
            "is_stale": False,
            "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stale_by_seconds": None,
            "freshness_reason": "fresh_within_ttl",
            "market_context": serialize_market_context(market_context),
        }

    def get_root_payload(self):
        return {
            "message": "Real-Time Market Intelligence API is running",
            "available_endpoints": [
                "/v1/health",
                "/v1/metrics",
                "/v1/ready",
                "/v1/market/summary",
                "/v1/stocks/{ticker}/summary",
                "/v1/stocks/{ticker}/live",
                "/v1/stocks/{ticker}/news",
                "/v1/stocks/{ticker}/news/summary",
                "/v1/stocks/{ticker}/news/summary/refresh",
                "/v1/jobs/{job_id}",
                "/v1/jobs/historical-backfill",
                "/v1/analytics/intraday/movers",
                "/v1/analytics/intraday/{ticker}",
                "/v1/analytics/movers",
                "/v1/analytics/volatility",
                "/v1/analytics/sentiment/{ticker}",
                "/v1/analytics/correlations/{ticker}",
                "/v1/analytics/drawdowns",
                "/v1/analytics/risk",
                "/v1/analytics/sectors",
                "/v1/analytics/anomalies",
                "/v1/analytics/features/{ticker}",
                "/v1/watchlist",
                "/v1/watchlist/alerts",
                "/v1/observability/metrics",
            ],
        }

    def get_health(self):
        return {
            "status": "healthy",
            "service": "market-api",
            "environment": settings.environment,
            "version": settings.app_version,
        }

    def get_readiness(self):
        checks = self.repository.fetch_readiness_status()
        return {
            "status": "ready" if all(checks.values()) else "degraded",
            "service": "market-api",
            "environment": settings.environment,
            "version": settings.app_version,
            "checks": checks,
        }

    def get_market_summary(self):
        rows = self.repository.fetch_market_summary()
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_stock_summary(self, ticker: str):
        normalized_ticker = normalize_ticker(ticker)
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
        normalized_ticker = normalize_ticker(ticker)
        symbol_profile = get_symbol_profile(normalized_ticker)
        market_context = get_market_calendar_context()
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
                "company_name": symbol_profile["company_name"],
                "sector": symbol_profile["sector"],
                "benchmark_ticker": symbol_profile["benchmark_ticker"],
                "benchmark_name": symbol_profile["benchmark_name"],
                "price": round(float(price), 2),
                "volume": int(volume or 0),
                "event_time": datetime.now(timezone.utc).isoformat(),
                "source": "yfinance_live_api",
                "market_session": infer_market_session(datetime.now(timezone.utc)),
                "market_context": serialize_market_context(market_context),
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
                increment_metric("api.cache.live.stale_fallback")
                return {
                    "ticker": normalized_ticker,
                    "company_name": symbol_profile["company_name"],
                    "sector": symbol_profile["sector"],
                    "benchmark_ticker": symbol_profile["benchmark_ticker"],
                    "benchmark_name": symbol_profile["benchmark_name"],
                    "price": round(float(cached_row["live_price"]), 2),
                    "volume": int(cached_row.get("live_volume") or 0),
                    "event_time": cached_row["live_event_time"].isoformat(),
                    "source": "daily_cache_stale",
                    "market_session": market_context["session"],
                    "market_context": serialize_market_context(market_context),
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
        normalized_ticker = normalize_ticker(ticker)
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
            increment_metric("api.cache.news.hit")
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
            increment_metric("api.news.provider.error")
            raise
        except Exception as exc:
            if settings.allow_stale_cache_fallback and cached_row and cached_row.get("news_articles"):
                increment_metric("api.cache.news.stale_fallback")
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
        normalized_ticker = normalize_ticker(ticker)

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
                increment_metric("api.cache.news_summary.hit")
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
            increment_metric("api.news.summary.error")
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
                increment_metric("api.cache.news_summary.stale_fallback")
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

    def refresh_stock_news_summary(self, ticker: str):
        normalized_ticker = normalize_ticker(ticker)
        cached_row = self.repository.get_daily_stock_search_cache(normalized_ticker)
        articles = cached_row["news_articles"] if cached_row and cached_row.get("news_articles") else fetch_news_articles(normalized_ticker)
        summary = summarize_news_with_local_model(normalized_ticker, articles)
        self.repository.upsert_news_cache(normalized_ticker, articles, summary)
        summary["article_count"] = len(articles)
        summary["cache"] = self._build_fresh_cache_metadata(settings.news_summary_cache_ttl_minutes)
        return summary

    def get_intraday_candles(self, ticker: str, limit: int = 48):
        normalized_ticker = normalize_ticker(ticker)
        rows = self.repository.fetch_intraday_candles(normalized_ticker, limit=limit)
        return {
            "ticker": normalized_ticker,
            "count": len(rows),
            "data": rows,
        }

    def get_intraday_movers(self, limit: int = 12):
        rows = self.repository.fetch_intraday_movers(limit=limit)
        return {
            "count": len(rows),
            "data": rows,
        }

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
        normalized_ticker = normalize_ticker(ticker)
        rows = self.repository.fetch_sentiment_over_time(normalized_ticker, limit=limit)

        return {
            "ticker": normalized_ticker,
            "count": len(rows),
            "data": rows,
        }

    def get_ticker_correlation(self, ticker: str, limit: int = 8):
        normalized_ticker = normalize_ticker(ticker)
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
        normalized_ticker = normalize_ticker(ticker) if ticker else None
        rows = self.repository.fetch_anomaly_history(limit=limit, ticker=normalized_ticker)
        return {
            "count": len(rows),
            "data": rows,
        }

    def get_watchlist(self, principal_id: str):
        rows = self.repository.fetch_watchlist(principal_id)
        return {
            "principal_id": principal_id,
            "count": len(rows),
            "data": rows,
        }

    def upsert_watchlist_item(
        self,
        principal_id: str,
        ticker: str,
        price_alert_threshold: float,
        volume_alert_threshold: float,
    ):
        row = self.repository.upsert_watchlist_item(
            principal_id=principal_id,
            ticker=normalize_ticker(ticker),
            price_alert_threshold=price_alert_threshold,
            volume_alert_threshold=volume_alert_threshold,
        )
        increment_metric("api.watchlist.upsert")
        return row

    def delete_watchlist_item(self, principal_id: str, ticker: str):
        deleted_count = self.repository.delete_watchlist_item(principal_id, normalize_ticker(ticker))
        increment_metric("api.watchlist.delete")
        return {"deleted": deleted_count > 0}

    def get_watchlist_alert_history(self, principal_id: str, limit: int = 50):
        rows = self.repository.fetch_watchlist_alert_history(principal_id, limit=limit)
        return {
            "principal_id": principal_id,
            "count": len(rows),
            "data": rows,
        }

    def get_observability_metrics(self):
        return get_metrics_snapshot()

    def get_signal_features(self, ticker: str, limit: int = 30):
        normalized_ticker = normalize_ticker(ticker)
        rows = self.repository.fetch_signal_features(normalized_ticker, limit=limit)
        return {
            "ticker": normalized_ticker,
            "count": len(rows),
            "data": rows,
        }


market_service = MarketService(market_repository)
