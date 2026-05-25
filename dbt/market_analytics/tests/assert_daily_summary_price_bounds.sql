SELECT
    ticker,
    trade_date,
    min_price,
    avg_price,
    max_price
FROM {{ ref('daily_stock_summary') }}
WHERE min_price > avg_price
   OR avg_price > max_price
