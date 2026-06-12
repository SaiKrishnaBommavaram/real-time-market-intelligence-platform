"""create api owned tables

Revision ID: 20260611_000001
Revises:
Create Date: 2026-06-11 00:00:01
"""

from alembic import op


revision = "20260611_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
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

        CREATE TABLE IF NOT EXISTS public.async_jobs (
            id BIGSERIAL PRIMARY KEY,
            job_type VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            result JSONB,
            error_message TEXT,
            requested_by VARCHAR(128) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_async_jobs_status_created_at
        ON public.async_jobs (status, created_at);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.async_jobs;
        DROP TABLE IF EXISTS public.symbol_reference;
        DROP TABLE IF EXISTS public.dashboard_watchlists;
        DROP TABLE IF EXISTS public.stock_search_cache;
        """
    )
