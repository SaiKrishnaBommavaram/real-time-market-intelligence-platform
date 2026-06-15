import asyncio
import time

from api.config import settings
from api.logging import configure_logging
from api.services.async_job_service import async_job_service


configure_logging()


async def run_worker():
    while True:
        jobs = await async_job_service.process_job_batch()
        if not jobs:
            await asyncio.sleep(settings.job_worker_poll_seconds)


def main():
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
