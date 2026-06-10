{{ config(
    alias='stock_anomaly_history'
) }}

SELECT
    ticker,
    company_name,
    sector,
    benchmark_ticker,
    benchmark_name,
    trade_date,
    anomaly_flag,
    ROUND(ABS(COALESCE(relative_price_change_pct, price_change_pct)) + volume_vs_avg_ratio, 4) AS anomaly_severity_score,
    relative_price_change_pct,
    price_change_pct,
    volume_vs_avg_ratio,
    close_price,
    total_volume
FROM {{ ref('daily_stock_summary') }}
WHERE anomaly_flag <> 'normal'
