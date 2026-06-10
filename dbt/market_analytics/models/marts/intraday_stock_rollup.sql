{{ config(
    alias='intraday_stock_rollup'
) }}

WITH base AS (
    SELECT
        ticker,
        DATE_TRUNC('hour', event_time AT TIME ZONE 'America/New_York') AT TIME ZONE 'America/New_York' AS interval_start,
        event_time,
        COALESCE(open_price, price) AS open_price,
        COALESCE(high_price, price) AS high_price,
        COALESCE(low_price, price) AS low_price,
        COALESCE(close_price, price) AS close_price,
        volume,
        market_session,
        inserted_at
    FROM {{ ref('stg_stock_prices') }}
    WHERE market_session <> 'closed'
),
symbol_meta AS (
    SELECT *
    FROM {{ ref('stg_symbol_reference') }}
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
),
hourly_session AS (
    SELECT DISTINCT ON (ticker, interval_start)
        ticker,
        interval_start,
        market_session
    FROM base
    ORDER BY ticker, interval_start, event_time ASC
),
assembled AS (
    SELECT
        agg.ticker,
        meta.company_name,
        COALESCE(meta.sector, 'Other') AS sector,
        meta.benchmark_ticker,
        meta.benchmark_name,
        agg.interval_start,
        hourly_session.market_session,
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
    INNER JOIN hourly_session
        ON agg.ticker = hourly_session.ticker
        AND agg.interval_start = hourly_session.interval_start
    LEFT JOIN symbol_meta AS meta
        ON agg.ticker = meta.ticker
),
interval_features AS (
    SELECT
        *,
        LAG(close_price) OVER (
            PARTITION BY ticker
            ORDER BY interval_start
        ) AS previous_close_price
    FROM assembled
),
benchmark_joined AS (
    SELECT
        current_bar.*,
        benchmark.close_price AS benchmark_close_price,
        ROUND(
            CASE
                WHEN benchmark.previous_close_price IS NULL OR benchmark.previous_close_price = 0 THEN NULL
                ELSE ((benchmark.close_price - benchmark.previous_close_price) / benchmark.previous_close_price) * 100
            END,
            4
        ) AS benchmark_interval_change_pct
    FROM interval_features AS current_bar
    LEFT JOIN interval_features AS benchmark
        ON current_bar.benchmark_ticker = benchmark.ticker
        AND current_bar.interval_start = benchmark.interval_start
)
SELECT
    ticker,
    company_name,
    sector,
    benchmark_ticker,
    benchmark_name,
    interval_start,
    market_session,
    open_price,
    high_price,
    low_price,
    close_price,
    previous_close_price,
    benchmark_close_price,
    benchmark_interval_change_pct,
    ROUND(
        CASE
            WHEN previous_close_price IS NULL OR previous_close_price = 0 THEN NULL
            ELSE ((close_price - previous_close_price) / previous_close_price) * 100
        END,
        4
    ) - COALESCE(benchmark_interval_change_pct, 0) AS relative_interval_change_pct,
    bar_count,
    total_volume,
    last_updated_at
FROM benchmark_joined
