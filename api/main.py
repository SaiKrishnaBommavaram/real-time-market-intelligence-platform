from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.logging import configure_logging, log_request_middleware
from api.routes.market import router as market_router
from api.security import enforce_api_key_middleware, rate_limit_middleware


configure_logging()

app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
)

app.middleware("http")(log_request_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(enforce_api_key_middleware)

app.include_router(market_router)
