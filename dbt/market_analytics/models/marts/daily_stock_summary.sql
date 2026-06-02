{{ config(
    alias='daily_stock_summary'
) }}

WITH base AS (
    SELECT
        ticker,
        DATE(event_time) AS trade_date,
        event_time,
        price,
        volume,
        COALESCE(open_price, price) AS open_price,
        COALESCE(high_price, price) AS high_price,
        COALESCE(low_price, price) AS low_price,
        COALESCE(close_price, price) AS close_price,
        inserted_at
    FROM {{ ref('stg_stock_prices') }}
),
daily_agg AS (
    SELECT
        ticker,
        trade_date,
        COUNT(*) AS event_count,
        ROUND(AVG(price), 2) AS avg_price,
        MIN(low_price) AS min_price,
        MAX(high_price) AS max_price,
        SUM(volume) AS total_volume,
        MAX(inserted_at) AS last_updated_at
    FROM base
    GROUP BY ticker, trade_date
),
daily_open AS (
    SELECT DISTINCT ON (ticker, trade_date)
        ticker,
        trade_date,
        open_price
    FROM base
    ORDER BY ticker, trade_date, event_time ASC
),
daily_close AS (
    SELECT DISTINCT ON (ticker, trade_date)
        ticker,
        trade_date,
        close_price
    FROM base
    ORDER BY ticker, trade_date, event_time DESC
),
combined AS (
    SELECT
        agg.ticker,
        agg.trade_date,
        agg.event_count,
        agg.avg_price,
        agg.min_price,
        agg.max_price,
        agg.total_volume,
        agg.last_updated_at,
        open_price.open_price,
        close_price.close_price
    FROM daily_agg AS agg
    INNER JOIN daily_open AS open_price
        ON agg.ticker = open_price.ticker
        AND agg.trade_date = open_price.trade_date
    INNER JOIN daily_close AS close_price
        ON agg.ticker = close_price.ticker
        AND agg.trade_date = close_price.trade_date
),
enriched AS (
    SELECT
        *,
        LAG(close_price) OVER (
            PARTITION BY ticker
            ORDER BY trade_date
        ) AS previous_close_price,
        AVG(total_volume) OVER (
            PARTITION BY ticker
            ORDER BY trade_date
            ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
        ) AS trailing_avg_volume
    FROM combined
)
SELECT
    ticker,
    trade_date,
    event_count,
    avg_price,
    min_price,
    max_price,
    total_volume,
    last_updated_at,
    open_price,
    close_price,
    previous_close_price,
    ROUND(
        CASE
            WHEN previous_close_price IS NULL OR previous_close_price = 0 THEN 0
            ELSE ((close_price - previous_close_price) / previous_close_price) * 100
        END,
        2
    ) AS price_change_pct,
    ROUND(
        CASE
            WHEN trailing_avg_volume IS NULL OR trailing_avg_volume = 0 THEN 1
            ELSE total_volume / trailing_avg_volume
        END,
        2
    ) AS volume_vs_avg_ratio,
    CASE
        WHEN ABS(
            CASE
                WHEN previous_close_price IS NULL OR previous_close_price = 0 THEN 0
                ELSE ((close_price - previous_close_price) / previous_close_price) * 100
            END
        ) >= 5
        AND (
            CASE
                WHEN trailing_avg_volume IS NULL OR trailing_avg_volume = 0 THEN 1
                ELSE total_volume / trailing_avg_volume
            END
        ) >= 1.5 THEN 'price_and_volume'
        WHEN ABS(
            CASE
                WHEN previous_close_price IS NULL OR previous_close_price = 0 THEN 0
                ELSE ((close_price - previous_close_price) / previous_close_price) * 100
            END
        ) >= 5 THEN 'price_move'
        WHEN (
            CASE
                WHEN trailing_avg_volume IS NULL OR trailing_avg_volume = 0 THEN 1
                ELSE total_volume / trailing_avg_volume
            END
        ) >= 1.5 THEN 'volume_spike'
        ELSE 'normal'
    END AS anomaly_flag
FROM enriched
