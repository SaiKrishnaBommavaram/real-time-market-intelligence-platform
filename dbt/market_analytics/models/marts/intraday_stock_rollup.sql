{{ config(
    alias='intraday_stock_rollup'
) }}

WITH base AS (
    SELECT
        ticker,
        DATE_TRUNC('hour', event_time) AS interval_start,
        event_time,
        COALESCE(open_price, price) AS open_price,
        COALESCE(high_price, price) AS high_price,
        COALESCE(low_price, price) AS low_price,
        COALESCE(close_price, price) AS close_price,
        volume,
        inserted_at
    FROM {{ ref('stg_stock_prices') }}
),
hourly_open AS (
    SELECT DISTINCT ON (ticker, interval_start)
        ticker,
        interval_start,
        open_price
    FROM base
    ORDER BY ticker, interval_start, event_time ASC
),
hourly_close AS (
    SELECT DISTINCT ON (ticker, interval_start)
        ticker,
        interval_start,
        close_price
    FROM base
    ORDER BY ticker, interval_start, event_time DESC
),
hourly_agg AS (
    SELECT
        ticker,
        interval_start,
        COUNT(*) AS bar_count,
        MAX(high_price) AS high_price,
        MIN(low_price) AS low_price,
        SUM(volume) AS total_volume,
        MAX(inserted_at) AS last_updated_at
    FROM base
    GROUP BY ticker, interval_start
)
SELECT
    agg.ticker,
    agg.interval_start,
    open_price.open_price,
    agg.high_price,
    agg.low_price,
    close_price.close_price,
    agg.bar_count,
    agg.total_volume,
    agg.last_updated_at
FROM hourly_agg AS agg
INNER JOIN hourly_open AS open_price
    ON agg.ticker = open_price.ticker
    AND agg.interval_start = open_price.interval_start
INNER JOIN hourly_close AS close_price
    ON agg.ticker = close_price.ticker
    AND agg.interval_start = close_price.interval_start
