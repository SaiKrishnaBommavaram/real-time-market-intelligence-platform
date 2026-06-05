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
    open_price NUMERIC(10, 2),
    high_price NUMERIC(10, 2),
    low_price NUMERIC(10, 2),
    close_price NUMERIC(10, 2),
    event_kind VARCHAR(50) NOT NULL DEFAULT 'live_snapshot',
    bar_interval VARCHAR(20) NOT NULL DEFAULT 'snapshot',
    market_session VARCHAR(20) NOT NULL DEFAULT 'regular',
    inserted_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.stock_prices
ADD COLUMN IF NOT EXISTS open_price NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS high_price NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS low_price NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS close_price NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS event_kind VARCHAR(50) NOT NULL DEFAULT 'live_snapshot',
ADD COLUMN IF NOT EXISTS bar_interval VARCHAR(20) NOT NULL DEFAULT 'snapshot',
ADD COLUMN IF NOT EXISTS market_session VARCHAR(20) NOT NULL DEFAULT 'regular';

CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_event_time
ON public.stock_prices (ticker, event_time DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_prices_event_identity
ON public.stock_prices (ticker, event_time, source, event_kind, bar_interval);

CREATE TABLE IF NOT EXISTS public.stock_search_cache (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    cache_date DATE NOT NULL,
    live_price NUMERIC(10, 2),
    live_volume BIGINT,
    live_event_time TIMESTAMPTZ,
    live_source VARCHAR(100),
    live_expires_at TIMESTAMPTZ,
    news_articles JSONB,
    news_summary TEXT,
    summary_source VARCHAR(100),
    summary_model VARCHAR(255),
    summary_fallback_reason TEXT,
    news_expires_at TIMESTAMPTZ,
    news_summary_expires_at TIMESTAMPTZ,
    live_updated_at TIMESTAMPTZ,
    news_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, cache_date)
);

ALTER TABLE public.stock_search_cache
ADD COLUMN IF NOT EXISTS live_expires_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS news_expires_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS news_summary_expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_stock_search_cache_ticker_cache_date
ON public.stock_search_cache (ticker, cache_date DESC);
