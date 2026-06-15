"""add async job dedupe fields

Revision ID: 20260614_000002
Revises: 20260611_000001
Create Date: 2026-06-14 00:00:02
"""

from alembic import op


revision = "20260614_000002"
down_revision = "20260611_000001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.async_jobs
        ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(64),
        ADD COLUMN IF NOT EXISTS active_job_key VARCHAR(64);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_async_jobs_active_job_key
        ON public.async_jobs (active_job_key)
        WHERE active_job_key IS NOT NULL;
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS uq_async_jobs_active_job_key;

        ALTER TABLE public.async_jobs
        DROP COLUMN IF EXISTS active_job_key,
        DROP COLUMN IF EXISTS dedupe_key;
        """
    )
