SELECT
    ticker,
    event_time,
    source,
    COUNT(*) AS duplicate_count
FROM {{ ref('stg_stock_prices') }}
GROUP BY 1, 2, 3
HAVING COUNT(*) > 1
