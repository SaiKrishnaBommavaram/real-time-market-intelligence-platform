import time

from api.config import settings
from api.logging import configure_logging
from api.services.async_job_service import async_job_service


configure_logging()


def main():
    while True:
        jobs = async_job_service.process_job_batch()
        if not jobs:
            time.sleep(settings.job_worker_poll_seconds)


if __name__ == "__main__":
    main()
