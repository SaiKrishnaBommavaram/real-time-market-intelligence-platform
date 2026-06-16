"""add invalid event table and api-owned indexes

Revision ID: 20260615_000003
Revises: 20260614_000002
Create Date: 2026-06-15 00:00:03
"""

from alembic import op


revision = "20260615_000003"
down_revision = "20260614_000002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_stock_search_cache_updated_at
        ON public.stock_search_cache (updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_dashboard_watchlists_updated_at
        ON public.dashboard_watchlists (updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_async_jobs_requested_by_status
        ON public.async_jobs (requested_by, status, created_at DESC);

        CREATE TABLE IF NOT EXISTS public.invalid_stock_events (
            id BIGSERIAL PRIMARY KEY,
            source_topic VARCHAR(255) NOT NULL,
            source_partition INTEGER NOT NULL,
            source_offset BIGINT NOT NULL,
            payload JSONB NOT NULL,
            validation_error TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_invalid_stock_events_created_at
        ON public.invalid_stock_events (created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_invalid_stock_events_topic_partition_offset
        ON public.invalid_stock_events (source_topic, source_partition, source_offset DESC);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS idx_invalid_stock_events_topic_partition_offset;
        DROP INDEX IF EXISTS idx_invalid_stock_events_created_at;
        DROP TABLE IF EXISTS public.invalid_stock_events;
        DROP INDEX IF EXISTS idx_async_jobs_requested_by_status;
        DROP INDEX IF EXISTS idx_dashboard_watchlists_updated_at;
        DROP INDEX IF EXISTS idx_stock_search_cache_updated_at;
        """
    )
