from datetime import datetime, timedelta, timezone

from psycopg2.extras import Json

from api.database import get_db_connection
from api.config import settings


class MarketRepository:
    def __init__(self):
        self._search_cache_table_verified = False

    def _get_today_cache_date(self):
        return datetime.now(timezone.utc).date()

    def _get_expiry_time(self, ttl_minutes: int):
        return datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

    def verify_stock_search_cache_table(self):
        if self._search_cache_table_verified:
            return

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.stock_search_cache') AS table_name;")
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not row.get("table_name"):
            raise RuntimeError(
                "public.stock_search_cache does not exist. "
                "Run the Postgres init SQL before starting the API."
            )

        self._search_cache_table_verified = True

    def fetch_health_status(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 AS status;")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result

    def fetch_market_summary(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                ticker,
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
                price_change_pct,
                volume_vs_avg_ratio,
                anomaly_flag
            FROM analytics.daily_stock_summary
            ORDER BY trade_date DESC, ticker
            LIMIT 100;
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_stock_summary(self, ticker: str):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                ticker,
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
                price_change_pct,
                volume_vs_avg_ratio,
                anomaly_flag
            FROM analytics.daily_stock_summary
            WHERE ticker = %s
            ORDER BY trade_date DESC;
            """,
            (ticker,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_top_movers(self, limit: int = 10):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            WITH latest_trade_date AS (
                SELECT MAX(trade_date) AS trade_date
                FROM analytics.daily_stock_summary
            )
            SELECT
                ticker,
                trade_date,
                close_price,
                previous_close_price,
                price_change_pct,
                total_volume,
                volume_vs_avg_ratio,
                anomaly_flag
            FROM analytics.daily_stock_summary
            WHERE trade_date = (SELECT trade_date FROM latest_trade_date)
            ORDER BY ABS(price_change_pct) DESC, total_volume DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_market_volatility(self, limit: int = 30):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_ticker_correlation(self, ticker: str, limit: int = 8):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_drawdown_recovery(self, limit: int = 30):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_risk_indicators(self, limit: int = 30):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_sector_performance(self, limit: int = 20):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
                avg_volume_ratio,
                total_volume,
                anomaly_count,
                top_ticker,
                top_ticker_price_change_pct
            FROM analytics.sector_daily_summary
            WHERE trade_date = (SELECT trade_date FROM latest_trade_date)
            ORDER BY avg_price_change_pct DESC, total_volume DESC
            LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_anomaly_history(self, limit: int = 50, ticker: str | None = None):
        conn = get_db_connection()
        cur = conn.cursor()

        if ticker:
            cur.execute(
                """
                SELECT
                    ticker,
                    trade_date,
                    anomaly_flag,
                    anomaly_severity_score,
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
        else:
            cur.execute(
                """
                SELECT
                    ticker,
                    trade_date,
                    anomaly_flag,
                    anomaly_severity_score,
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

        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def fetch_sentiment_over_time(self, ticker: str, limit: int = 30):
        self.verify_stock_search_cache_table()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def get_daily_stock_search_cache(self, ticker: str):
        self.verify_stock_search_cache_table()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM stock_search_cache
            WHERE ticker = %s
            ORDER BY cache_date DESC, updated_at DESC
            LIMIT 1;
            """,
            (ticker,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

    def get_cache_status(self, row: dict | None, expires_field: str, updated_field: str):
        if not row:
            return {
                "state": "miss",
                "is_stale": True,
                "expires_at": None,
                "updated_at": None,
                "stale_by_seconds": None,
            }

        now = datetime.now(timezone.utc)
        expires_at = row.get(expires_field)
        updated_at = row.get(updated_field)
        is_stale = expires_at is None or expires_at <= now
        stale_by_seconds = None

        if expires_at and is_stale:
            stale_by_seconds = max(int((now - expires_at).total_seconds()), 0)

        return {
            "state": "stale" if is_stale else "fresh",
            "is_stale": is_stale,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "stale_by_seconds": stale_by_seconds,
        }

    def upsert_live_stock_cache(self, ticker: str, payload: dict):
        self.verify_stock_search_cache_table()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
        conn.commit()
        cur.close()
        conn.close()

    def upsert_news_cache(self, ticker: str, articles: list, summary: dict):
        self.verify_stock_search_cache_table()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
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
        conn.commit()
        cur.close()
        conn.close()


market_repository = MarketRepository()
