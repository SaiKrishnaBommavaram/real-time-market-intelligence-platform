import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone

from psycopg2.extras import Json

from api.database import get_db_connection, release_db_connection
from api.config import settings
from market_calendar import get_market_calendar_context, serialize_market_context


class MarketRepository:
    def __init__(self):
        self._search_cache_table_verified = False
        self._async_jobs_table_verified = False

    def _get_today_cache_date(self):
        return datetime.now(timezone.utc).date()

    def _get_expiry_time(self, ttl_minutes: int):
        return datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

    async def fetch_lineage_metadata(
        self,
        source_table: str,
        source_event_field: str | None = "event_time",
        source_inserted_field: str | None = "inserted_at",
        mart_table: str | None = None,
        mart_timestamp_field: str | None = None,
        mart_date_field: str | None = None,
    ):
        source_select = [
            f"MAX({source_event_field}) AS source_max_event_time"
            if source_event_field
            else "NULL AS source_max_event_time",
            f"MAX({source_inserted_field}) AS source_max_inserted_at"
            if source_inserted_field
            else "NULL AS source_max_inserted_at",
        ]
        source_row = await self._fetchone(
            f"""
            SELECT
                {", ".join(source_select)}
            FROM {source_table};
            """
        )
        mart_row = None
        if mart_table and mart_timestamp_field:
            mart_row = await self._fetchone(
                f"""
                SELECT
                    MAX({mart_timestamp_field}) AS mart_max_timestamp
                    {f", MAX({mart_date_field}) AS latest_data_date" if mart_date_field else ""}
                FROM {mart_table};
                """
            )

        return {
            "source_table": source_table,
            "mart_table": mart_table,
            "source_max_event_time": source_row.get("source_max_event_time") if source_row else None,
            "source_max_inserted_at": source_row.get("source_max_inserted_at") if source_row else None,
            "mart_max_timestamp": mart_row.get("mart_max_timestamp") if mart_row else None,
            "latest_data_date": mart_row.get("latest_data_date") if mart_row and mart_date_field else None,
        }

    async def _fetchone(self, query: str, params=None):
        connection = await get_db_connection()

        def _run():
            cur = connection.cursor()
            try:
                cur.execute(query, params) if params is not None else cur.execute(query)
                return cur.fetchone()
            finally:
                cur.close()

        try:
            return await asyncio.to_thread(_run)
        finally:
            await release_db_connection(connection)

    async def _fetchall(self, query: str, params=None):
        connection = await get_db_connection()

        def _run():
            cur = connection.cursor()
            try:
                cur.execute(query, params) if params is not None else cur.execute(query)
                return cur.fetchall()
            finally:
                cur.close()

        try:
            return await asyncio.to_thread(_run)
        finally:
            await release_db_connection(connection)

    async def _execute(self, query: str, params=None):
        connection = await get_db_connection()

        def _run():
            cur = connection.cursor()
            try:
                cur.execute(query, params) if params is not None else cur.execute(query)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cur.close()

        try:
            await asyncio.to_thread(_run)
        finally:
            await release_db_connection(connection)

    async def _execute_returning_one(self, query: str, params=None):
        connection = await get_db_connection()

        def _run():
            cur = connection.cursor()
            try:
                cur.execute(query, params) if params is not None else cur.execute(query)
                row = cur.fetchone()
                connection.commit()
                return row
            except Exception:
                connection.rollback()
                raise
            finally:
                cur.close()

        try:
            return await asyncio.to_thread(_run)
        finally:
            await release_db_connection(connection)

    def build_job_dedupe_key(self, job_type: str, requested_by: str, payload: dict):
        canonical_payload = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(
            f"{job_type}:{requested_by}:{canonical_payload}".encode("utf-8"),
        ).hexdigest()
        return digest

    async def verify_stock_search_cache_table(self):
        if self._search_cache_table_verified:
            return

        row = await self._fetchone(
            "SELECT to_regclass('public.stock_search_cache') AS table_name;",
        )

        if not row or not row.get("table_name"):
            raise RuntimeError(
                "public.stock_search_cache does not exist. "
                "Run the Postgres init SQL before starting the API."
            )

        self._search_cache_table_verified = True

    async def verify_async_jobs_table(self):
        if self._async_jobs_table_verified:
            return

        row = await self._fetchone("SELECT to_regclass('public.async_jobs') AS table_name;")

        if not row or not row.get("table_name"):
            raise RuntimeError(
                "public.async_jobs does not exist. "
                "Run the Postgres init SQL or Alembic migrations before starting the API."
            )

        self._async_jobs_table_verified = True

    async def fetch_health_status(self):
        return await self._fetchone("SELECT 1 AS status;")

    async def fetch_readiness_status(self):
        health_result = await self.fetch_health_status()
        await self.verify_stock_search_cache_table()
        await self.verify_async_jobs_table()
        redis_ready = False
        try:
            from api.redis_client import get_redis_client

            redis_ready = bool(get_redis_client().ping())
        except Exception:
            redis_ready = False
        return {
            "database": bool(health_result and health_result.get("status") == 1),
            "stock_search_cache_table": True,
            "async_jobs_table": True,
            "redis": redis_ready,
        }

    async def create_async_job(self, job_type: str, payload: dict, requested_by: str):
        await self.verify_async_jobs_table()

        dedupe_key = self.build_job_dedupe_key(job_type, requested_by, payload)
        row = await self._execute_returning_one(
            """
            INSERT INTO public.async_jobs (
                job_type,
                status,
                payload,
                dedupe_key,
                active_job_key,
                requested_by,
                created_at,
                updated_at
            )
            VALUES (%s, 'pending', %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (active_job_key)
            DO NOTHING
            RETURNING *;
            """,
            (job_type, Json(payload), dedupe_key, dedupe_key, requested_by),
        )
        if row:
            row["deduplicated"] = False
            return row

        row = await self._fetchone(
            """
            SELECT *, TRUE AS deduplicated
            FROM public.async_jobs
            WHERE active_job_key = %s;
            """,
            (dedupe_key,),
        )
        return row

    async def fetch_async_job(self, job_id: int):
        await self.verify_async_jobs_table()

        return await self._fetchone(
            """
            SELECT *
            FROM public.async_jobs
            WHERE id = %s;
            """,
            (job_id,),
        )

    async def claim_pending_async_job(self):
        await self.verify_async_jobs_table()

        return await self._execute_returning_one(
            """
            WITH next_job AS (
                SELECT id
                FROM public.async_jobs
                WHERE status = 'pending'
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE public.async_jobs AS jobs
            SET
                status = 'running',
                started_at = NOW(),
                updated_at = NOW()
            FROM next_job
            WHERE jobs.id = next_job.id
            RETURNING jobs.*;
            """
        )

    async def complete_async_job(self, job_id: int, result: dict):
        await self.verify_async_jobs_table()

        await self._execute(
            """
            UPDATE public.async_jobs
            SET
                status = 'succeeded',
                active_job_key = NULL,
                result = %s,
                error_message = NULL,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s;
            """,
            (Json(result), job_id),
        )

    async def fail_async_job(self, job_id: int, error_message: str):
        await self.verify_async_jobs_table()

        await self._execute(
            """
            UPDATE public.async_jobs
            SET
                status = 'failed',
                active_job_key = NULL,
                error_message = %s,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s;
            """,
            (error_message[:2000], job_id),
        )

    async def fetch_market_summary(self):
        return await self._fetchall(
            """
            SELECT
                ticker,
                company_name,
                sector,
                benchmark_ticker,
                benchmark_name,
                trade_date,
                event_count,
                avg_price,
                min_price,
                max_price,
                total_volume,
                last_updated_at,
                open_price,
                close_price,
                previous_close_price,
                benchmark_close_price,
                benchmark_price_change_pct,
                relative_price_change_pct,
                price_change_pct,
                volume_vs_avg_ratio,
                anomaly_flag
            FROM analytics.daily_stock_summary
            ORDER BY trade_date DESC, ticker
            LIMIT 100;
            """
        )

    async def fetch_stock_summary(self, ticker: str):
        return await self._fetchall(
            """
            SELECT
                ticker,
                company_name,
                sector,
                benchmark_ticker,
                benchmark_name,
                trade_date,
                event_count,
                avg_price,
                min_price,
                max_price,
                total_volume,
                last_updated_at,
                open_price,
                close_price,
                previous_close_price,
                benchmark_close_price,
                benchmark_price_change_pct,
                relative_price_change_pct,
                price_change_pct,
                volume_vs_avg_ratio,
                anomaly_flag
            FROM analytics.daily_stock_summary
            WHERE ticker = %s
            ORDER BY trade_date DESC;
            """,
            (ticker,),
        )

    async def fetch_top_movers(self, limit: int = 10):
        return await self._fetchall(
            """
            WITH latest_trade_date AS (
                SELECT MAX(trade_date) AS trade_date
                FROM analytics.daily_stock_summary
            )
            SELECT
                ticker,
                company_name,
                sector,
                benchmark_ticker,
                benchmark_name,
                trade_date,
                close_price,
                previous_close_price,
                benchmark_close_price,
                benchmark_price_change_pct,
                relative_price_change_pct,
                price_change_pct,
                total_volume,
                volume_vs_avg_ratio,
                anomaly_flag
            FROM analytics.daily_stock_summary
            WHERE trade_date = (SELECT trade_date FROM latest_trade_date)
            ORDER BY ABS(COALESCE(relative_price_change_pct, price_change_pct)) DESC, total_volume DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_intraday_candles(self, ticker: str, limit: int = 48):
        return await self._fetchall(
            """
            SELECT
                ticker,
                company_name,
                sector,
                benchmark_ticker,
                benchmark_name,
                interval_start,
                market_session,
                open_price,
                high_price,
                low_price,
                close_price,
                previous_close_price,
                benchmark_close_price,
                benchmark_interval_change_pct,
                relative_interval_change_pct,
                bar_count,
                total_volume,
                last_updated_at
            FROM analytics.intraday_stock_rollup
            WHERE ticker = %s
            ORDER BY interval_start DESC
            LIMIT %s;
            """,
            (ticker, limit),
        )

    async def fetch_intraday_movers(self, limit: int = 12):
        return await self._fetchall(
            """
            WITH ranked AS (
                SELECT
                    ticker,
                    company_name,
                    sector,
                    benchmark_ticker,
                    benchmark_name,
                    interval_start,
                    market_session,
                    close_price,
                    previous_close_price,
                    benchmark_interval_change_pct,
                    relative_interval_change_pct,
                    total_volume,
                    bar_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY ticker
                        ORDER BY interval_start DESC
                    ) AS row_num
                FROM analytics.intraday_stock_rollup
                WHERE market_session <> 'closed'
            )
            SELECT
                ticker,
                company_name,
                sector,
                benchmark_ticker,
                benchmark_name,
                interval_start,
                market_session,
                close_price,
                previous_close_price,
                ROUND(COALESCE(
                    relative_interval_change_pct,
                    CASE
                        WHEN previous_close_price IS NULL OR previous_close_price = 0 THEN NULL
                        ELSE ((close_price - previous_close_price) / previous_close_price) * 100
                    END
                ), 4) AS interval_change_pct,
                benchmark_interval_change_pct,
                relative_interval_change_pct,
                total_volume,
                bar_count
            FROM ranked
            WHERE row_num = 1
            ORDER BY ABS(
                COALESCE(
                    relative_interval_change_pct,
                    CASE
                        WHEN previous_close_price IS NULL OR previous_close_price = 0 THEN NULL
                        ELSE ((close_price - previous_close_price) / previous_close_price) * 100
                    END
                )
            ) DESC NULLS LAST, total_volume DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_market_volatility(self, limit: int = 30):
        return await self._fetchall(
            """
            SELECT
                ticker,
                ROUND(STDDEV_POP(price_change_pct), 4) AS volatility_score,
                ROUND(AVG(ABS(price_change_pct)), 4) AS avg_absolute_move_pct,
                ROUND(MAX(ABS(price_change_pct)), 4) AS max_absolute_move_pct,
                COUNT(*) AS observed_days
            FROM analytics.daily_stock_summary
            GROUP BY ticker
            HAVING COUNT(*) >= 2
            ORDER BY volatility_score DESC NULLS LAST, avg_absolute_move_pct DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_ticker_correlation(self, ticker: str, limit: int = 8):
        return await self._fetchall(
            """
            WITH target_ticker AS (
                SELECT
                    trade_date,
                    price_change_pct
                FROM analytics.daily_stock_summary
                WHERE ticker = %s
            )
            SELECT
                candidate.ticker,
                ROUND(CORR(target.price_change_pct, candidate.price_change_pct), 4) AS correlation,
                COUNT(*) AS overlapping_days
            FROM analytics.daily_stock_summary AS candidate
            INNER JOIN target_ticker AS target
                ON candidate.trade_date = target.trade_date
            WHERE candidate.ticker <> %s
            GROUP BY candidate.ticker
            HAVING COUNT(*) >= 2
            ORDER BY ABS(CORR(target.price_change_pct, candidate.price_change_pct)) DESC NULLS LAST
            LIMIT %s;
            """,
            (ticker, ticker, limit),
        )

    async def fetch_drawdown_recovery(self, limit: int = 30):
        return await self._fetchall(
            """
            WITH latest_per_ticker AS (
                SELECT DISTINCT ON (ticker)
                    ticker,
                    trade_date,
                    close_price,
                    rolling_peak_close,
                    drawdown_pct,
                    days_since_peak,
                    recovery_status,
                    last_updated_at
                FROM analytics.stock_drawdown_recovery
                ORDER BY ticker, trade_date DESC
            )
            SELECT *
            FROM latest_per_ticker
            ORDER BY ABS(drawdown_pct) DESC, days_since_peak DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_risk_indicators(self, limit: int = 30):
        return await self._fetchall(
            """
            WITH latest_per_ticker AS (
                SELECT DISTINCT ON (ticker)
                    ticker,
                    trade_date,
                    close_price,
                    price_change_pct,
                    rolling_return_7d_pct,
                    rolling_volatility_7d,
                    sharpe_like_ratio_7d,
                    observed_days,
                    last_updated_at
                FROM analytics.stock_risk_indicators
                ORDER BY ticker, trade_date DESC
            )
            SELECT *
            FROM latest_per_ticker
            ORDER BY rolling_volatility_7d DESC NULLS LAST, sharpe_like_ratio_7d ASC NULLS LAST
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_sector_performance(self, limit: int = 20):
        return await self._fetchall(
            """
            WITH latest_trade_date AS (
                SELECT MAX(trade_date) AS trade_date
                FROM analytics.sector_daily_summary
            )
            SELECT
                sector,
                trade_date,
                ticker_count,
                avg_price_change_pct,
                avg_relative_price_change_pct,
                avg_volume_ratio,
                total_volume,
                anomaly_count,
                top_ticker,
                top_ticker_price_change_pct
            FROM analytics.sector_daily_summary
            WHERE trade_date = (SELECT trade_date FROM latest_trade_date)
            ORDER BY COALESCE(avg_relative_price_change_pct, avg_price_change_pct) DESC, total_volume DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_benchmark_relative_strength(self, limit: int = 20):
        return await self._fetchall(
            """
            WITH latest_trade_date AS (
                SELECT MAX(trade_date) AS trade_date
                FROM analytics.benchmark_relative_strength
            )
            SELECT
                benchmark_ticker,
                benchmark_name,
                trade_date,
                benchmark_price_change_pct,
                ticker_count,
                avg_relative_price_change_pct,
                outperformer_count,
                underperformer_count,
                top_relative_ticker,
                top_relative_price_change_pct,
                total_volume,
                last_updated_at
            FROM analytics.benchmark_relative_strength
            WHERE trade_date = (SELECT trade_date FROM latest_trade_date)
            ORDER BY ABS(avg_relative_price_change_pct) DESC, total_volume DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_market_regime_summary(self, limit: int = 30):
        return await self._fetchall(
            """
            SELECT
                trade_date,
                regime_label,
                avg_relative_move_pct,
                avg_volume_ratio,
                avg_volatility_7d,
                risk_off_share,
                outperformer_share,
                ticker_count,
                anomaly_count,
                benchmark_leader,
                last_updated_at
            FROM analytics.market_regime_summary
            ORDER BY trade_date DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_anomaly_history(self, limit: int = 50, ticker: str | None = None):
        if ticker:
            return await self._fetchall(
                """
                SELECT
                ticker,
                company_name,
                sector,
                benchmark_ticker,
                benchmark_name,
                trade_date,
                anomaly_flag,
                anomaly_severity_score,
                relative_price_change_pct,
                price_change_pct,
                volume_vs_avg_ratio,
                close_price,
                    total_volume
                FROM analytics.stock_anomaly_history
                WHERE ticker = %s
                ORDER BY trade_date DESC, anomaly_severity_score DESC
                LIMIT %s;
                """,
                (ticker, limit),
            )
        return await self._fetchall(
            """
            SELECT
            ticker,
            company_name,
            sector,
            benchmark_ticker,
            benchmark_name,
            trade_date,
            anomaly_flag,
            anomaly_severity_score,
            relative_price_change_pct,
            price_change_pct,
            volume_vs_avg_ratio,
            close_price,
                total_volume
            FROM analytics.stock_anomaly_history
            ORDER BY trade_date DESC, anomaly_severity_score DESC
            LIMIT %s;
            """,
            (limit,),
        )

    async def fetch_watchlist(self, principal_id: str):
        return await self._fetchall(
            """
            SELECT
                watchlist.ticker,
                symbols.company_name,
                symbols.sector,
                symbols.benchmark_ticker,
                symbols.benchmark_name,
                price_alert_threshold,
                volume_alert_threshold,
                created_at,
                updated_at
            FROM dashboard_watchlists AS watchlist
            LEFT JOIN public.symbol_reference AS symbols
                ON watchlist.ticker = symbols.canonical_ticker
            WHERE watchlist.principal_id = %s
            ORDER BY watchlist.ticker;
            """,
            (principal_id,),
        )

    async def upsert_watchlist_item(
        self,
        principal_id: str,
        ticker: str,
        price_alert_threshold: float,
        volume_alert_threshold: float,
    ):
        return await self._execute_returning_one(
            """
            INSERT INTO dashboard_watchlists (
                principal_id,
                ticker,
                price_alert_threshold,
                volume_alert_threshold,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (principal_id, ticker)
            DO UPDATE SET
                price_alert_threshold = EXCLUDED.price_alert_threshold,
                volume_alert_threshold = EXCLUDED.volume_alert_threshold,
                updated_at = NOW()
            RETURNING
                ticker,
                price_alert_threshold,
                volume_alert_threshold,
                created_at,
                updated_at;
            """,
            (principal_id, ticker, price_alert_threshold, volume_alert_threshold),
        )

    async def delete_watchlist_item(self, principal_id: str, ticker: str):
        connection = await get_db_connection()

        def _run():
            cur = connection.cursor()
            try:
                cur.execute(
                    """
                    DELETE FROM dashboard_watchlists
                    WHERE principal_id = %s AND ticker = %s;
                    """,
                    (principal_id, ticker),
                )
                deleted = cur.rowcount
                connection.commit()
                return deleted
            except Exception:
                connection.rollback()
                raise
            finally:
                cur.close()

        try:
            return await asyncio.to_thread(_run)
        finally:
            await release_db_connection(connection)

    async def fetch_watchlist_alert_history(self, principal_id: str, limit: int = 50):
        return await self._fetchall(
            """
            SELECT
                watchlist.ticker,
                symbols.company_name,
                symbols.sector,
                symbols.benchmark_ticker,
                symbols.benchmark_name,
                summary.trade_date,
                summary.close_price,
                summary.relative_price_change_pct,
                summary.price_change_pct,
                summary.volume_vs_avg_ratio,
                summary.anomaly_flag,
                watchlist.price_alert_threshold,
                watchlist.volume_alert_threshold,
                ABS(summary.price_change_pct) >= watchlist.price_alert_threshold AS triggered_price_alert,
                summary.volume_vs_avg_ratio >= watchlist.volume_alert_threshold AS triggered_volume_alert
            FROM dashboard_watchlists AS watchlist
            INNER JOIN analytics.daily_stock_summary AS summary
                ON watchlist.ticker = summary.ticker
            LEFT JOIN public.symbol_reference AS symbols
                ON watchlist.ticker = symbols.canonical_ticker
            WHERE watchlist.principal_id = %s
            AND (
                ABS(summary.price_change_pct) >= watchlist.price_alert_threshold
                OR summary.volume_vs_avg_ratio >= watchlist.volume_alert_threshold
                OR summary.anomaly_flag <> 'normal'
            )
            ORDER BY summary.trade_date DESC, ABS(summary.price_change_pct) DESC
            LIMIT %s;
            """,
            (principal_id, limit),
        )

    async def fetch_sentiment_over_time(self, ticker: str, limit: int = 30):
        await self.verify_stock_search_cache_table()

        return await self._fetchall(
            """
            SELECT
                ticker,
                cache_date,
                ROUND(AVG(COALESCE((article ->> 'sentiment')::numeric, 0)), 4) AS avg_sentiment,
                ROUND(AVG(COALESCE((article ->> 'impact_score')::numeric, 0)), 4) AS avg_impact_score,
                ROUND(AVG(COALESCE((article ->> 'source_quality_score')::numeric, 0)), 4) AS avg_source_quality_score,
                COUNT(*) AS article_count
            FROM stock_search_cache
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(news_articles, '[]'::jsonb)) AS article
            WHERE ticker = %s
            GROUP BY ticker, cache_date
            ORDER BY cache_date DESC
            LIMIT %s;
            """,
            (ticker, limit),
        )

    async def get_daily_stock_search_cache(self, ticker: str):
        await self.verify_stock_search_cache_table()

        return await self._fetchone(
            """
            SELECT *
            FROM stock_search_cache
            WHERE ticker = %s
            ORDER BY cache_date DESC, updated_at DESC
            LIMIT 1;
            """,
            (ticker,),
        )

    def get_cache_status(self, row: dict | None, expires_field: str, updated_field: str):
        market_context = get_market_calendar_context()
        if not row:
            return {
                "state": "miss",
                "is_stale": True,
                "expires_at": None,
                "updated_at": None,
                "stale_by_seconds": None,
                "freshness_reason": "cache_miss",
                "market_context": serialize_market_context(market_context),
            }

        now = datetime.now(timezone.utc)
        expires_at = row.get(expires_field)
        updated_at = row.get(updated_field)
        is_stale = expires_at is None or expires_at <= now
        stale_by_seconds = None
        freshness_reason = "ttl_expired" if is_stale else "fresh_within_ttl"

        if (
            is_stale
            and updated_at
            and not market_context["is_market_open"]
            and updated_at >= market_context["last_session_close_at"]
        ):
            is_stale = False
            freshness_reason = "market_closed_since_last_update"

        if expires_at and is_stale:
            stale_by_seconds = max(int((now - expires_at).total_seconds()), 0)

        return {
            "state": "stale" if is_stale else "fresh",
            "is_stale": is_stale,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "stale_by_seconds": stale_by_seconds,
            "freshness_reason": freshness_reason,
            "market_context": serialize_market_context(market_context),
        }

    async def fetch_signal_features(self, ticker: str, limit: int = 30):
        return await self._fetchall(
            """
            SELECT
                ticker,
                company_name,
                sector,
                benchmark_ticker,
                benchmark_name,
                trade_date,
                close_price,
                previous_close_price,
                price_change_pct,
                benchmark_price_change_pct,
                relative_price_change_pct,
                volume_vs_avg_ratio,
                drawdown_pct,
                rolling_return_7d_pct,
                rolling_volatility_7d,
                sharpe_like_ratio_7d,
                anomaly_flag,
                anomaly_severity_score,
                market_regime_label,
                signal_strength_score,
                feature_generated_at
            FROM analytics.stock_signal_feature_store
            WHERE ticker = %s
            ORDER BY trade_date DESC
            LIMIT %s;
            """,
            (ticker, limit),
        )

    async def upsert_live_stock_cache(self, ticker: str, payload: dict):
        await self.verify_stock_search_cache_table()

        await self._execute(
            """
            INSERT INTO stock_search_cache (
                ticker,
                cache_date,
                live_price,
                live_volume,
                live_event_time,
                live_source,
                live_expires_at,
                live_updated_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ticker, cache_date)
            DO UPDATE SET
                live_price = EXCLUDED.live_price,
                live_volume = EXCLUDED.live_volume,
                live_event_time = EXCLUDED.live_event_time,
                live_source = EXCLUDED.live_source,
                live_expires_at = EXCLUDED.live_expires_at,
                live_updated_at = NOW(),
                updated_at = NOW();
            """,
            (
                ticker,
                self._get_today_cache_date(),
                payload["price"],
                payload["volume"],
                payload["event_time"],
                payload["source"],
                self._get_expiry_time(settings.live_cache_ttl_minutes),
            ),
        )

    async def upsert_news_cache(self, ticker: str, articles: list, summary: dict):
        await self.verify_stock_search_cache_table()

        await self._execute(
            """
            INSERT INTO stock_search_cache (
                ticker,
                cache_date,
                news_articles,
                news_summary,
                summary_source,
                summary_model,
                summary_fallback_reason,
                news_expires_at,
                news_summary_expires_at,
                news_updated_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ticker, cache_date)
            DO UPDATE SET
                news_articles = EXCLUDED.news_articles,
                news_summary = EXCLUDED.news_summary,
                summary_source = EXCLUDED.summary_source,
                summary_model = EXCLUDED.summary_model,
                summary_fallback_reason = EXCLUDED.summary_fallback_reason,
                news_expires_at = EXCLUDED.news_expires_at,
                news_summary_expires_at = EXCLUDED.news_summary_expires_at,
                news_updated_at = NOW(),
                updated_at = NOW();
            """,
            (
                ticker,
                self._get_today_cache_date(),
                Json(articles),
                summary["summary"],
                summary["source"],
                summary["model"],
                summary["fallback_reason"],
                self._get_expiry_time(settings.news_cache_ttl_minutes),
                self._get_expiry_time(settings.news_summary_cache_ttl_minutes),
            ),
        )

    async def invalidate_stock_cache(self, ticker: str, scopes: list[str]):
        await self.verify_stock_search_cache_table()

        normalized_scopes = set(scopes)
        all_scopes = {"live", "news", "news_summary"}

        if normalized_scopes == all_scopes:
            connection = await get_db_connection()

            def _delete():
                cur = connection.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM stock_search_cache
                        WHERE ticker = %s;
                        """,
                        (ticker,),
                    )
                    deleted_rows = cur.rowcount
                    connection.commit()
                    return {"invalidated": deleted_rows > 0, "deleted_rows": deleted_rows}
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    cur.close()

            try:
                return await asyncio.to_thread(_delete)
            finally:
                await release_db_connection(connection)

        set_clauses = ["updated_at = NOW()"]
        if "live" in normalized_scopes:
            set_clauses.extend(
                [
                    "live_price = NULL",
                    "live_volume = NULL",
                    "live_event_time = NULL",
                    "live_source = NULL",
                    "live_expires_at = NULL",
                    "live_updated_at = NULL",
                ],
            )
        if "news" in normalized_scopes:
            set_clauses.extend(
                [
                    "news_articles = NULL",
                    "news_expires_at = NULL",
                    "news_updated_at = NULL",
                ],
            )
        if "news_summary" in normalized_scopes:
            set_clauses.extend(
                [
                    "news_summary = NULL",
                    "summary_source = NULL",
                    "summary_model = NULL",
                    "summary_fallback_reason = NULL",
                    "news_summary_expires_at = NULL",
                ],
            )

        connection = await get_db_connection()

        def _update():
            cur = connection.cursor()
            try:
                cur.execute(
                    f"""
                    UPDATE stock_search_cache
                    SET {", ".join(set_clauses)}
                    WHERE ticker = %s;
                    """,
                    (ticker,),
                )
                updated_rows = cur.rowcount
                connection.commit()
                return {"invalidated": updated_rows > 0, "updated_rows": updated_rows}
            except Exception:
                connection.rollback()
                raise
            finally:
                cur.close()

        try:
            return await asyncio.to_thread(_update)
        finally:
            await release_db_connection(connection)


market_repository = MarketRepository()
