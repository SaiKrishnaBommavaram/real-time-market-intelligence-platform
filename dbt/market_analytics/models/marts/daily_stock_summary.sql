SELECT
    ticker,
    DATE(event_time) AS trade_date,
    COUNT(*) AS event_count,
    ROUND(AVG(price), 2) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    SUM(volume) AS total_volume,
    MAX(inserted_at) AS last_updated_at
FROM {{ ref('stg_stock_prices') }}
GROUP BY ticker, DATE(event_time)