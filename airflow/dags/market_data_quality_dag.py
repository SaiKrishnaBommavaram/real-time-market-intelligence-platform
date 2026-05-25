from datetime import datetime, timedelta
import os

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator


MAX_EVENT_AGE_MINUTES = int(os.getenv("MARKET_DQ_MAX_EVENT_AGE_MINUTES", "90"))
MAX_SUMMARY_AGE_HOURS = int(os.getenv("MARKET_DQ_MAX_SUMMARY_AGE_HOURS", "24"))


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("MARKET_DB_HOST", "postgres"),
        port=int(os.getenv("MARKET_DB_PORT", "5432")),
        database=os.getenv("MARKET_DB_NAME", "market_data"),
        user=os.getenv("MARKET_DB_USER", "postgres"),
        password=os.getenv("MARKET_DB_PASSWORD", "postgres"),
    )


def check_postgres_stock_rows():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM stock_prices;")
    row_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    if row_count == 0:
        raise ValueError("No stock price rows found in PostgreSQL.")

    print(f"PostgreSQL stock_prices row count: {row_count}")


def check_postgres_stock_freshness():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT EXTRACT(EPOCH FROM (NOW() - MAX(inserted_at))) / 60
        FROM stock_prices;
        """
    )
    freshness_minutes = cur.fetchone()[0]

    cur.close()
    conn.close()

    if freshness_minutes is None:
        raise ValueError("Could not determine stock_prices freshness.")

    if freshness_minutes > MAX_EVENT_AGE_MINUTES:
        raise ValueError(
            "stock_prices data is stale. "
            f"Latest row is {freshness_minutes:.2f} minutes old."
        )

    print(f"stock_prices freshness OK: {freshness_minutes:.2f} minutes old")


def check_postgres_stock_duplicates():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ticker, event_time, source, COUNT(*) AS duplicate_count
            FROM stock_prices
            GROUP BY ticker, event_time, source
            HAVING COUNT(*) > 1
        ) duplicates;
        """
    )
    duplicate_group_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    if duplicate_group_count > 0:
        raise ValueError(
            f"Detected {duplicate_group_count} duplicate stock event groups in stock_prices."
        )

    print("stock_prices duplicate check OK")


def check_daily_summary_freshness():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT EXTRACT(EPOCH FROM (NOW() - MAX(last_updated_at))) / 3600
        FROM analytics.daily_stock_summary;
        """
    )
    freshness_hours = cur.fetchone()[0]

    cur.close()
    conn.close()

    if freshness_hours is None:
        raise ValueError("analytics.daily_stock_summary has no rows to validate.")

    if freshness_hours > MAX_SUMMARY_AGE_HOURS:
        raise ValueError(
            "analytics.daily_stock_summary is stale. "
            f"Latest row is {freshness_hours:.2f} hours old."
        )

    print(f"daily_stock_summary freshness OK: {freshness_hours:.2f} hours old")


default_args = {
    "owner": "sai",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="market_data_quality_check",
    default_args=default_args,
    description="Validates market data pipeline output in PostgreSQL",
    start_date=datetime(2026, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["market-data", "quality-check"],
) as dag:

    validate_postgres_data = PythonOperator(
        task_id="validate_postgres_stock_data",
        python_callable=check_postgres_stock_rows,
    )

    validate_postgres_freshness = PythonOperator(
        task_id="validate_postgres_stock_freshness",
        python_callable=check_postgres_stock_freshness,
    )

    validate_postgres_duplicates = PythonOperator(
        task_id="validate_postgres_stock_duplicates",
        python_callable=check_postgres_stock_duplicates,
    )

    validate_daily_summary_freshness = PythonOperator(
        task_id="validate_daily_summary_freshness",
        python_callable=check_daily_summary_freshness,
    )

    (
        validate_postgres_data
        >> validate_postgres_freshness
        >> validate_postgres_duplicates
        >> validate_daily_summary_freshness
    )
