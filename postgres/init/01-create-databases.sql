SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'airflow'
)\gexec

CREATE TABLE IF NOT EXISTS public.stock_prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    source VARCHAR(100),
    inserted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_event_time
ON public.stock_prices (ticker, event_time DESC);

CREATE TABLE IF NOT EXISTS public.stock_search_cache (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    cache_date DATE NOT NULL,
    live_price NUMERIC(10, 2),
    live_volume BIGINT,
    live_event_time TIMESTAMPTZ,
    live_source VARCHAR(100),
    news_articles JSONB,
    news_summary TEXT,
    summary_source VARCHAR(100),
    summary_model VARCHAR(255),
    summary_fallback_reason TEXT,
    live_updated_at TIMESTAMPTZ,
    news_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, cache_date)
);

CREATE INDEX IF NOT EXISTS idx_stock_search_cache_ticker_cache_date
ON public.stock_search_cache (ticker, cache_date DESC);
