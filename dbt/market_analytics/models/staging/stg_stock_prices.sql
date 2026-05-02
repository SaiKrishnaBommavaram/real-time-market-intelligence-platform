SELECT
    id,
    ticker,
    price,
    volume,
    event_time,
    source,
    inserted_at
FROM public.stock_prices
WHERE ticker IS NOT NULL