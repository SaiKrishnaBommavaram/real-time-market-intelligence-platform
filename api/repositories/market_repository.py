from datetime import datetime, timezone

from psycopg2.extras import Json

from api.database import get_db_connection


class MarketRepository:
    def __init__(self):
        self._search_cache_table_verified = False

    def _get_today_cache_date(self):
        return datetime.now(timezone.utc).date()

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

    def get_daily_stock_search_cache(self, ticker: str):
        self.verify_stock_search_cache_table()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM stock_search_cache
            WHERE ticker = %s AND cache_date = %s;
            """,
            (ticker, self._get_today_cache_date()),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

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
                live_updated_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ticker, cache_date)
            DO UPDATE SET
                live_price = EXCLUDED.live_price,
                live_volume = EXCLUDED.live_volume,
                live_event_time = EXCLUDED.live_event_time,
                live_source = EXCLUDED.live_source,
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
                news_updated_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ticker, cache_date)
            DO UPDATE SET
                news_articles = EXCLUDED.news_articles,
                news_summary = EXCLUDED.news_summary,
                summary_source = EXCLUDED.summary_source,
                summary_model = EXCLUDED.summary_model,
                summary_fallback_reason = EXCLUDED.summary_fallback_reason,
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
            ),
        )
        conn.commit()
        cur.close()
        conn.close()


market_repository = MarketRepository()
