{{ config(
    alias='stg_symbol_reference'
) }}

SELECT
    UPPER(TRIM(canonical_ticker)) AS ticker,
    company_name,
    sector,
    UPPER(NULLIF(TRIM(benchmark_ticker), '')) AS benchmark_ticker,
    benchmark_name,
    COALESCE(NULLIF(TRIM(benchmark_kind), ''), 'broad_market') AS benchmark_kind,
    aliases,
    is_benchmark,
    created_at,
    updated_at
FROM {{ source('market_data', 'symbol_reference') }}
