import hashlib
import logging

from fastapi import Request
from starlette.responses import JSONResponse

from api.config import settings
from api.observability import increment_metric
from api.redis_client import get_redis_client


logger = logging.getLogger("market.api.security")
EXEMPT_PATHS = {
    "/",
    "/health",
    "/metrics",
    "/ready",
    "/v1/",
    "/v1/health",
    "/v1/metrics",
    "/v1/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def is_exempt_path(path: str) -> bool:
    return path in EXEMPT_PATHS


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_principal_id(request: Request) -> str:
    api_key = request.headers.get(settings.api_key_header)
    if api_key:
        return f"api_key:{hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:24]}"
    return f"anonymous:{get_client_identifier(request)}"


class RedisRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis = get_redis_client()

    def check(self, key: str) -> tuple[bool, dict[str, str]]:
        redis_key = (
            f"{settings.redis_key_prefix}:rate-limit:"
            f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}"
        )
        current_count = self.redis.incr(redis_key)
        if current_count == 1:
            self.redis.expire(redis_key, self.window_seconds)

        ttl_seconds = max(self.redis.ttl(redis_key), 0)
        remaining = max(self.max_requests - current_count, 0)
        headers = {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Window": str(self.window_seconds),
        }

        if current_count > self.max_requests:
            headers["Retry-After"] = str(max(ttl_seconds, 1))
            headers["X-RateLimit-Remaining"] = "0"
            return False, headers

        return True, headers


rate_limiter = RedisRateLimiter(
    settings.rate_limit_max_requests,
    settings.rate_limit_window_seconds,
)


async def enforce_api_key_middleware(request: Request, call_next):
    request.state.principal_id = get_principal_id(request)
    if settings.api_key and not is_exempt_path(request.url.path):
        provided_api_key = request.headers.get(settings.api_key_header)
        if provided_api_key != settings.api_key:
            increment_metric("api.auth.failure")
            logger.warning(
                "authentication_failed",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": get_client_identifier(request),
                },
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
            )
        increment_metric("api.auth.success")

    return await call_next(request)


async def rate_limit_middleware(request: Request, call_next):
    if is_exempt_path(request.url.path):
        return await call_next(request)

    try:
        allowed, headers = rate_limiter.check(get_client_identifier(request))
    except Exception as exc:
        increment_metric("api.rate_limit.backend_error")
        logger.exception(
            "rate_limit_backend_failed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_host": get_client_identifier(request),
            },
        )
        return JSONResponse(
            status_code=503,
            content={"detail": f"Rate limit backend unavailable: {exc}"},
        )

    if not allowed:
        increment_metric("api.rate_limit.exceeded")
        logger.warning(
            "rate_limit_exceeded",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_host": get_client_identifier(request),
            },
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers=headers,
        )

    response = await call_next(request)
    response.headers.update(headers)
    return response
