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
    inserted_at
FROM {{ source('market_data', 'stock_prices') }}
WHERE ticker IS NOT NULL
