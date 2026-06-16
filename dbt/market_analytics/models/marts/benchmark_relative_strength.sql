{{ config(
    alias='benchmark_relative_strength'
) }}

WITH base AS (
    SELECT
        benchmark_ticker,
        benchmark_name,
        trade_date,
        benchmark_price_change_pct,
        ticker,
        relative_price_change_pct,
        total_volume,
        last_updated_at
    FROM {{ ref('daily_stock_summary') }}
    WHERE benchmark_ticker IS NOT NULL
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY benchmark_ticker, trade_date
            ORDER BY ABS(COALESCE(relative_price_change_pct, 0)) DESC, total_volume DESC, ticker
        ) AS relative_rank
    FROM base
)
SELECT
    benchmark_ticker,
    MAX(benchmark_name) AS benchmark_name,
    trade_date,
    MAX(benchmark_price_change_pct) AS benchmark_price_change_pct,
    COUNT(*) AS ticker_count,
    ROUND(AVG(COALESCE(relative_price_change_pct, 0)), 4) AS avg_relative_price_change_pct,
    COUNT(*) FILTER (WHERE COALESCE(relative_price_change_pct, 0) > 0) AS outperformer_count,
    COUNT(*) FILTER (WHERE COALESCE(relative_price_change_pct, 0) < 0) AS underperformer_count,
    MAX(CASE WHEN relative_rank = 1 THEN ticker END) AS top_relative_ticker,
    MAX(CASE WHEN relative_rank = 1 THEN relative_price_change_pct END) AS top_relative_price_change_pct,
    SUM(total_volume) AS total_volume,
    MAX(last_updated_at) AS last_updated_at
FROM ranked
GROUP BY benchmark_ticker, trade_date
