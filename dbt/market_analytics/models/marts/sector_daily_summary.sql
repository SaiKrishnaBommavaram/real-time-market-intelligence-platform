{{ config(
    alias='sector_daily_summary'
) }}

WITH sector_map AS (
    SELECT *
    FROM (
        VALUES
            ('AAPL', 'Technology'),
            ('MSFT', 'Technology'),
            ('NVDA', 'Technology'),
            ('AMD', 'Technology'),
            ('INTC', 'Technology'),
            ('GOOGL', 'Communication Services'),
            ('META', 'Communication Services'),
            ('AMZN', 'Consumer Discretionary'),
            ('TSLA', 'Consumer Discretionary'),
            ('NFLX', 'Communication Services'),
            ('JPM', 'Financials'),
            ('BAC', 'Financials'),
            ('XOM', 'Energy'),
            ('CVX', 'Energy')
    ) AS mapped(ticker, sector)
),
base AS (
    SELECT
        summary.ticker,
        summary.trade_date,
        COALESCE(map.sector, 'Other') AS sector,
        summary.price_change_pct,
        summary.volume_vs_avg_ratio,
        summary.total_volume,
        summary.anomaly_flag
    FROM {{ ref('daily_stock_summary') }} AS summary
    LEFT JOIN sector_map AS map
        ON summary.ticker = map.ticker
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY sector, trade_date
            ORDER BY ABS(price_change_pct) DESC, total_volume DESC, ticker
        ) AS sector_rank
    FROM base
)
SELECT
    sector,
    trade_date,
    COUNT(*) AS ticker_count,
    ROUND(AVG(price_change_pct), 4) AS avg_price_change_pct,
    ROUND(AVG(volume_vs_avg_ratio), 4) AS avg_volume_ratio,
    SUM(total_volume) AS total_volume,
    COUNT(*) FILTER (WHERE anomaly_flag <> 'normal') AS anomaly_count,
    MAX(CASE WHEN sector_rank = 1 THEN ticker END) AS top_ticker,
    MAX(CASE WHEN sector_rank = 1 THEN price_change_pct END) AS top_ticker_price_change_pct
FROM ranked
GROUP BY sector, trade_date
