from datetime import datetime, timedelta

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator


def check_postgres_stock_rows():
    conn = psycopg2.connect(
        host="postgres",
        port=5432,
        database="market_data",
        user="postgres",
        password="postgres",
    )

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM stock_prices;")
    row_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    if row_count == 0:
        raise ValueError("No stock price rows found in PostgreSQL.")

    print(f"PostgreSQL stock_prices row count: {row_count}")


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

    validate_postgres_data