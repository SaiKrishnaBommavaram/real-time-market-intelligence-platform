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
