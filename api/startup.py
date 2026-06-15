import logging
import asyncio

from api.config import settings, StartupCheckMode
from api.services.market_service import market_service


logger = logging.getLogger("market.api.startup")


async def run_startup_checks():
    if settings.startup_check_mode == StartupCheckMode.OFF:
        logger.info("startup_checks_skipped", extra={"mode": settings.startup_check_mode})
        return

    try:
        readiness = await market_service.get_readiness()
    except Exception as exc:
        if settings.startup_check_mode == StartupCheckMode.STRICT:
            raise RuntimeError(f"Startup readiness checks failed: {exc}") from exc

        logger.warning(
            "startup_checks_warn_only_failure",
            extra={"mode": settings.startup_check_mode, "error": str(exc)},
        )
        return

    logger.info(
        "startup_checks_passed",
        extra={
            "mode": settings.startup_check_mode,
            "environment": settings.environment,
            "checks": readiness["checks"],
        },
    )


if __name__ == "__main__":
    asyncio.run(run_startup_checks())
