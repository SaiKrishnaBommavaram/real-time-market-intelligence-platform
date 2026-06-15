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

CREATE TABLE IF NOT EXISTS public.dashboard_watchlists (
    id SERIAL PRIMARY KEY,
    principal_id VARCHAR(128) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    price_alert_threshold NUMERIC(10, 2) NOT NULL,
    volume_alert_threshold NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (principal_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_watchlists_principal
ON public.dashboard_watchlists (principal_id, ticker);

CREATE TABLE IF NOT EXISTS public.async_jobs (
    id BIGSERIAL PRIMARY KEY,
    job_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    dedupe_key VARCHAR(64),
    active_job_key VARCHAR(64),
    result JSONB,
    error_message TEXT,
    requested_by VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.async_jobs
ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(64),
ADD COLUMN IF NOT EXISTS active_job_key VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_async_jobs_status_created_at
ON public.async_jobs (status, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_async_jobs_active_job_key
ON public.async_jobs (active_job_key)
WHERE active_job_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.symbol_reference (
    canonical_ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    benchmark_ticker VARCHAR(10),
    benchmark_name VARCHAR(255),
    benchmark_kind VARCHAR(50) NOT NULL DEFAULT 'broad_market',
    aliases TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    is_benchmark BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.symbol_reference (
    canonical_ticker,
    company_name,
    sector,
    benchmark_ticker,
    benchmark_name,
    benchmark_kind,
    aliases,
    is_benchmark
)
VALUES
    ('AAPL', 'Apple Inc.', 'Technology', 'XLK', 'Technology Select Sector SPDR Fund', 'sector_etf', ARRAY['Apple', 'Apple Inc', 'iPhone maker'], FALSE),
    ('MSFT', 'Microsoft Corporation', 'Technology', 'XLK', 'Technology Select Sector SPDR Fund', 'sector_etf', ARRAY['Microsoft', 'Microsoft Corp', 'Azure'], FALSE),
    ('NVDA', 'NVIDIA Corporation', 'Technology', 'XLK', 'Technology Select Sector SPDR Fund', 'sector_etf', ARRAY['NVIDIA', 'Nvidia', 'GeForce'], FALSE),
    ('AMD', 'Advanced Micro Devices, Inc.', 'Technology', 'XLK', 'Technology Select Sector SPDR Fund', 'sector_etf', ARRAY['AMD', 'Advanced Micro Devices', 'Ryzen'], FALSE),
    ('INTC', 'Intel Corporation', 'Technology', 'XLK', 'Technology Select Sector SPDR Fund', 'sector_etf', ARRAY['Intel', 'Intel Corp'], FALSE),
    ('GOOGL', 'Alphabet Inc.', 'Communication Services', 'XLC', 'Communication Services Select Sector SPDR Fund', 'sector_etf', ARRAY['Alphabet', 'Google', 'Alphabet Inc'], FALSE),
    ('META', 'Meta Platforms, Inc.', 'Communication Services', 'XLC', 'Communication Services Select Sector SPDR Fund', 'sector_etf', ARRAY['Meta', 'Facebook', 'Instagram'], FALSE),
    ('NFLX', 'Netflix, Inc.', 'Communication Services', 'XLC', 'Communication Services Select Sector SPDR Fund', 'sector_etf', ARRAY['Netflix', 'Netflix Inc'], FALSE),
    ('AMZN', 'Amazon.com, Inc.', 'Consumer Discretionary', 'XLY', 'Consumer Discretionary Select Sector SPDR Fund', 'sector_etf', ARRAY['Amazon', 'Amazon.com', 'AWS'], FALSE),
    ('TSLA', 'Tesla, Inc.', 'Consumer Discretionary', 'XLY', 'Consumer Discretionary Select Sector SPDR Fund', 'sector_etf', ARRAY['Tesla', 'Tesla Inc'], FALSE),
    ('JPM', 'JPMorgan Chase & Co.', 'Financials', 'XLF', 'Financial Select Sector SPDR Fund', 'sector_etf', ARRAY['JPMorgan', 'JP Morgan', 'JPMorgan Chase'], FALSE),
    ('BAC', 'Bank of America Corporation', 'Financials', 'XLF', 'Financial Select Sector SPDR Fund', 'sector_etf', ARRAY['Bank of America', 'BofA', 'BAC'], FALSE),
    ('XOM', 'Exxon Mobil Corporation', 'Energy', 'XLE', 'Energy Select Sector SPDR Fund', 'sector_etf', ARRAY['Exxon', 'Exxon Mobil'], FALSE),
    ('CVX', 'Chevron Corporation', 'Energy', 'XLE', 'Energy Select Sector SPDR Fund', 'sector_etf', ARRAY['Chevron', 'Chevron Corp'], FALSE),
    ('SPY', 'SPDR S&P 500 ETF Trust', 'Benchmark', NULL, NULL, 'broad_market', ARRAY['SPY', 'S&P 500'], TRUE),
    ('XLK', 'Technology Select Sector SPDR Fund', 'Technology', 'SPY', 'SPDR S&P 500 ETF Trust', 'broad_market', ARRAY['XLK', 'Technology Select Sector SPDR Fund'], TRUE),
    ('XLC', 'Communication Services Select Sector SPDR Fund', 'Communication Services', 'SPY', 'SPDR S&P 500 ETF Trust', 'broad_market', ARRAY['XLC', 'Communication Services Select Sector SPDR Fund'], TRUE),
    ('XLY', 'Consumer Discretionary Select Sector SPDR Fund', 'Consumer Discretionary', 'SPY', 'SPDR S&P 500 ETF Trust', 'broad_market', ARRAY['XLY', 'Consumer Discretionary Select Sector SPDR Fund'], TRUE),
    ('XLF', 'Financial Select Sector SPDR Fund', 'Financials', 'SPY', 'SPDR S&P 500 ETF Trust', 'broad_market', ARRAY['XLF', 'Financial Select Sector SPDR Fund'], TRUE),
    ('XLE', 'Energy Select Sector SPDR Fund', 'Energy', 'SPY', 'SPDR S&P 500 ETF Trust', 'broad_market', ARRAY['XLE', 'Energy Select Sector SPDR Fund'], TRUE)
ON CONFLICT (canonical_ticker)
DO UPDATE SET
    company_name = EXCLUDED.company_name,
    sector = EXCLUDED.sector,
    benchmark_ticker = EXCLUDED.benchmark_ticker,
    benchmark_name = EXCLUDED.benchmark_name,
    benchmark_kind = EXCLUDED.benchmark_kind,
    aliases = EXCLUDED.aliases,
    is_benchmark = EXCLUDED.is_benchmark,
    updated_at = NOW();
