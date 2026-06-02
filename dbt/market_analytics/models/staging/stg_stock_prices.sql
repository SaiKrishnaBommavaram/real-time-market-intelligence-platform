{{ config(
    alias='stg_stock_prices'
) }}

SELECT
    id,
    UPPER(TRIM(ticker)) AS ticker,
    CAST(price AS NUMERIC(10, 2)) AS price,
    CAST(volume AS BIGINT) AS volume,
    CAST(event_time AS TIMESTAMPTZ) AS event_time,
    COALESCE(NULLIF(TRIM(source), ''), 'unknown') AS source,
    CAST(open_price AS NUMERIC(10, 2)) AS open_price,
    CAST(high_price AS NUMERIC(10, 2)) AS high_price,
    CAST(low_price AS NUMERIC(10, 2)) AS low_price,
    CAST(close_price AS NUMERIC(10, 2)) AS close_price,
    COALESCE(NULLIF(TRIM(event_kind), ''), 'live_snapshot') AS event_kind,
    COALESCE(NULLIF(TRIM(bar_interval), ''), 'snapshot') AS bar_interval,
    COALESCE(NULLIF(TRIM(market_session), ''), 'regular') AS market_session,
    inserted_at
FROM {{ source('market_data', 'stock_prices') }}
WHERE ticker IS NOT NULL
