import hashlib
import logging
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from starlette.responses import JSONResponse

from api.config import settings
from api.observability import increment_metric


logger = logging.getLogger("market.api.security")
EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


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


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, dict[str, str]]:
        now = time.time()

        with self._lock:
            bucket = self._buckets[key]
            window_start = now - self.window_seconds

            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(bucket[0] + self.window_seconds - now))
                return False, {
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(self.window_seconds),
                }

            bucket.append(now)
            remaining = max(self.max_requests - len(bucket), 0)
            return True, {
                "X-RateLimit-Limit": str(self.max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Window": str(self.window_seconds),
            }


rate_limiter = InMemoryRateLimiter(
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

    allowed, headers = rate_limiter.check(get_client_identifier(request))
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
