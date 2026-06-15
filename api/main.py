from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.logging import configure_logging, log_request_middleware
from api.routes.market import router as market_router
from api.routes.v1 import router as v1_router
from api.security import enforce_api_key_middleware, rate_limit_middleware
from api.startup import run_startup_checks
from api.database import close_db_pool


configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await run_startup_checks()
    yield
    await close_db_pool()


app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

app.middleware("http")(log_request_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(enforce_api_key_middleware)

app.include_router(v1_router)
app.include_router(market_router, include_in_schema=False)
