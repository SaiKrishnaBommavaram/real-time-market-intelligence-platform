import logging
import time
import uuid

from fastapi import Request

from api.config import settings
from api.observability import increment_metric, observe_timing_ms
from pipeline_runtime import StructuredFormatter


def configure_logging():
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setFormatter(StructuredFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(handler)

    root_logger.setLevel(settings.log_level.upper())


logger = logging.getLogger("market.api")


async def log_request_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        increment_metric("api.request.error")
        increment_metric(f"api.request.error.{request.method.lower()}")
        observe_timing_ms("api.request.duration", duration_ms)
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "duration_ms": duration_ms,
                "client_host": request.client.host if request.client else None,
            },
        )
        raise exc

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    increment_metric("api.request.total")
    increment_metric(f"api.request.status.{response.status_code}")
    observe_timing_ms("api.request.duration", duration_ms)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_host": request.client.host if request.client else None,
        },
    )
    return response
