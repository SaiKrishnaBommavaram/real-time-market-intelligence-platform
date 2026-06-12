from enum import StrEnum


class AsyncJobType(StrEnum):
    NEWS_SUMMARY_REFRESH = "news_summary_refresh"
    HISTORICAL_BACKFILL = "historical_backfill"


class AsyncJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
