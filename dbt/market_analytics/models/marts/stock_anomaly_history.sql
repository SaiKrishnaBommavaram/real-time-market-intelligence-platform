{{ config(
    alias='stock_anomaly_history'
) }}

SELECT
    ticker,
    trade_date,
    anomaly_flag,
    ROUND(ABS(price_change_pct) + volume_vs_avg_ratio, 4) AS anomaly_severity_score,
    price_change_pct,
    volume_vs_avg_ratio,
    close_price,
    total_volume
FROM {{ ref('daily_stock_summary') }}
WHERE anomaly_flag <> 'normal'
