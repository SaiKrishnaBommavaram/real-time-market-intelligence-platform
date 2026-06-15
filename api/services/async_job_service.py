import logging

from api.config import settings
from api.jobs import AsyncJobType
from api.observability import increment_metric
from api.repositories.market_repository import market_repository
from api.services.market_service import market_service
from market_symbols import normalize_ticker
from producers.stock_producer import run_historical_backfill


logger = logging.getLogger("market.api.jobs")


class AsyncJobService:
    def __init__(self, repository):
        self.repository = repository

    async def create_news_summary_job(self, ticker: str, requested_by: str):
        if not settings.enable_async_news_summary:
            raise ValueError("Async news-summary jobs are disabled.")
        normalized_ticker = normalize_ticker(ticker)
        payload = {"ticker": normalized_ticker}
        row = await self.repository.create_async_job(
            AsyncJobType.NEWS_SUMMARY_REFRESH,
            payload,
            requested_by,
        )
        if row.get("deduplicated"):
            increment_metric("api.jobs.deduplicated.news_summary")
        increment_metric("api.jobs.enqueued.news_summary")
        return row

    async def create_historical_backfill_job(self, requested_by: str, ticker: str | None = None):
        if not settings.enable_async_backfill:
            raise ValueError("Async historical-backfill jobs are disabled.")
        payload = {"ticker": normalize_ticker(ticker)} if ticker else {}
        row = await self.repository.create_async_job(
            AsyncJobType.HISTORICAL_BACKFILL,
            payload,
            requested_by,
        )
        if row.get("deduplicated"):
            increment_metric("api.jobs.deduplicated.historical_backfill")
        increment_metric("api.jobs.enqueued.historical_backfill")
        return row

    async def get_job(self, job_id: int, requested_by: str):
        row = await self.repository.fetch_async_job(job_id)
        if not row:
            raise ValueError(f"Async job {job_id} was not found.")
        if row["requested_by"] != requested_by:
            raise ValueError(f"Async job {job_id} was not found.")
        return row

    async def process_next_job(self):
        job = await self.repository.claim_pending_async_job()
        if not job:
            return None

        job_id = job["id"]
        job_type = job["job_type"]
        payload = job.get("payload") or {}

        logger.info(
            "async_job_started",
            extra={"job_id": job_id, "job_type": job_type, "payload": payload},
        )

        try:
            if job_type == AsyncJobType.NEWS_SUMMARY_REFRESH:
                result = await market_service.refresh_stock_news_summary(payload["ticker"])
            elif job_type == AsyncJobType.HISTORICAL_BACKFILL:
                target_ticker = payload.get("ticker")
                result = run_historical_backfill([target_ticker] if target_ticker else None)
            else:
                raise ValueError(f"Unsupported job type: {job_type}")

            await self.repository.complete_async_job(job_id, result)
            increment_metric(f"api.jobs.completed.{job_type}")
            logger.info(
                "async_job_completed",
                extra={"job_id": job_id, "job_type": job_type},
            )
            return await self.repository.fetch_async_job(job_id)
        except Exception as exc:
            await self.repository.fail_async_job(job_id, str(exc))
            increment_metric(f"api.jobs.failed.{job_type}")
            logger.exception(
                "async_job_failed",
                extra={"job_id": job_id, "job_type": job_type},
            )
            return await self.repository.fetch_async_job(job_id)

    async def process_job_batch(self):
        processed_jobs = []
        for _ in range(settings.job_worker_batch_size):
            job = await self.process_next_job()
            if job is None:
                break
            processed_jobs.append(job)
        return processed_jobs


async_job_service = AsyncJobService(market_repository)
