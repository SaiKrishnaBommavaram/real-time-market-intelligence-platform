import os
from dataclasses import dataclass
from enum import StrEnum

from dotenv import load_dotenv


load_dotenv()


class AppEnvironment(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _get_required_env(name: str) -> str:
    value = _get_env(name)
    if value is None:
        raise ValueError(f"Required environment variable {name} is not set.")
    return value


def _get_int(name: str, default: str) -> int:
    raw_value = _get_required_env(name) if default is None else _get_env(name, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


def _get_bool(name: str, default: str) -> bool:
    raw_value = (_get_env(name, default) or "").lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Environment variable {name} must be a boolean.")


def _get_csv(name: str, default: str) -> list[str]:
    raw_value = _get_env(name, default) or ""
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _get_environment() -> AppEnvironment:
    raw_value = (_get_env("MARKET_ENV", "local") or "local").lower()
    try:
        return AppEnvironment(raw_value)
    except ValueError as exc:
        raise ValueError("MARKET_ENV must be one of: local, dev, prod.") from exc


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass(frozen=True)
class CorsSettings:
    allowed_origins: list[str]
    allowed_origin_regex: str | None


@dataclass(frozen=True)
class SecuritySettings:
    api_key: str | None
    api_key_header: str
    rate_limit_max_requests: int
    rate_limit_window_seconds: int


@dataclass(frozen=True)
class NewsSettings:
    api_key: str | None
    local_summarizer_model: str
    local_summarizer_max_length: int
    local_summarizer_min_length: int
    local_summarizer_input_max_tokens: int
    article_note_max_length: int
    article_note_min_length: int


@dataclass(frozen=True)
class CacheSettings:
    live_ttl_minutes: int
    news_ttl_minutes: int
    news_summary_ttl_minutes: int
    allow_stale_fallback: bool


@dataclass(frozen=True)
class Settings:
    environment: AppEnvironment
    app_title: str
    app_description: str
    app_version: str
    log_level: str
    debug: bool
    database: DatabaseSettings
    cors: CorsSettings
    security: SecuritySettings
    news: NewsSettings
    cache: CacheSettings

    @property
    def is_local(self) -> bool:
        return self.environment == AppEnvironment.LOCAL

    @property
    def is_development(self) -> bool:
        return self.environment in {AppEnvironment.LOCAL, AppEnvironment.DEV}

    @property
    def is_production(self) -> bool:
        return self.environment == AppEnvironment.PROD

    @property
    def db_host(self) -> str:
        return self.database.host

    @property
    def db_port(self) -> int:
        return self.database.port

    @property
    def db_name(self) -> str:
        return self.database.name

    @property
    def db_user(self) -> str:
        return self.database.user

    @property
    def db_password(self) -> str:
        return self.database.password

    @property
    def allowed_origins(self) -> list[str]:
        return self.cors.allowed_origins

    @property
    def allowed_origin_regex(self) -> str | None:
        return self.cors.allowed_origin_regex

    @property
    def api_key(self) -> str | None:
        return self.security.api_key

    @property
    def api_key_header(self) -> str:
        return self.security.api_key_header

    @property
    def rate_limit_max_requests(self) -> int:
        return self.security.rate_limit_max_requests

    @property
    def rate_limit_window_seconds(self) -> int:
        return self.security.rate_limit_window_seconds

    @property
    def news_api_key(self) -> str | None:
        return self.news.api_key

    @property
    def local_summarizer_model(self) -> str:
        return self.news.local_summarizer_model

    @property
    def local_summarizer_max_length(self) -> int:
        return self.news.local_summarizer_max_length

    @property
    def local_summarizer_min_length(self) -> int:
        return self.news.local_summarizer_min_length

    @property
    def local_summarizer_input_max_tokens(self) -> int:
        return self.news.local_summarizer_input_max_tokens

    @property
    def article_note_max_length(self) -> int:
        return self.news.article_note_max_length

    @property
    def article_note_min_length(self) -> int:
        return self.news.article_note_min_length

    @property
    def live_cache_ttl_minutes(self) -> int:
        return self.cache.live_ttl_minutes

    @property
    def news_cache_ttl_minutes(self) -> int:
        return self.cache.news_ttl_minutes

    @property
    def news_summary_cache_ttl_minutes(self) -> int:
        return self.cache.news_summary_ttl_minutes

    @property
    def allow_stale_cache_fallback(self) -> bool:
        return self.cache.allow_stale_fallback


def _validate_positive(name: str, value: int):
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0.")


def build_settings() -> Settings:
    environment = _get_environment()
    log_level = (_get_env("LOG_LEVEL", "DEBUG" if environment == AppEnvironment.LOCAL else "INFO") or "INFO").upper()
    debug = _get_bool("MARKET_DEBUG", "true" if environment == AppEnvironment.LOCAL else "false")

    database = DatabaseSettings(
        host=_get_env("MARKET_DB_HOST", "localhost") or "localhost",
        port=_get_int("MARKET_DB_PORT", "55432"),
        name=_get_env("MARKET_DB_NAME", "market_data") or "market_data",
        user=_get_env("MARKET_DB_USER", "postgres") or "postgres",
        password=_get_env("MARKET_DB_PASSWORD", "postgres") or "postgres",
    )

    cors = CorsSettings(
        allowed_origins=_get_csv("ALLOWED_ORIGINS", "http://localhost:5173"),
        allowed_origin_regex=_get_env("ALLOWED_ORIGIN_REGEX"),
    )

    security = SecuritySettings(
        api_key=_get_env("MARKET_API_KEY"),
        api_key_header=_get_env("MARKET_API_KEY_HEADER", "x-api-key") or "x-api-key",
        rate_limit_max_requests=_get_int("MARKET_RATE_LIMIT_MAX_REQUESTS", "120"),
        rate_limit_window_seconds=_get_int("MARKET_RATE_LIMIT_WINDOW_SECONDS", "60"),
    )

    news = NewsSettings(
        api_key=_get_env("NEWS_API_KEY"),
        local_summarizer_model=_get_env(
            "LOCAL_SUMMARIZER_MODEL",
            "sshleifer/distilbart-cnn-12-6",
        ) or "sshleifer/distilbart-cnn-12-6",
        local_summarizer_max_length=_get_int("LOCAL_SUMMARIZER_MAX_LENGTH", "90"),
        local_summarizer_min_length=_get_int("LOCAL_SUMMARIZER_MIN_LENGTH", "35"),
        local_summarizer_input_max_tokens=_get_int("LOCAL_SUMMARIZER_INPUT_MAX_TOKENS", "1024"),
        article_note_max_length=_get_int("ARTICLE_NOTE_MAX_LENGTH", "60"),
        article_note_min_length=_get_int("ARTICLE_NOTE_MIN_LENGTH", "20"),
    )

    cache = CacheSettings(
        live_ttl_minutes=_get_int("MARKET_LIVE_CACHE_TTL_MINUTES", "15"),
        news_ttl_minutes=_get_int("MARKET_NEWS_CACHE_TTL_MINUTES", "180"),
        news_summary_ttl_minutes=_get_int("MARKET_NEWS_SUMMARY_CACHE_TTL_MINUTES", "180"),
        allow_stale_fallback=_get_bool("MARKET_ALLOW_STALE_CACHE_FALLBACK", "true"),
    )

    for name, value in (
        ("MARKET_RATE_LIMIT_MAX_REQUESTS", security.rate_limit_max_requests),
        ("MARKET_RATE_LIMIT_WINDOW_SECONDS", security.rate_limit_window_seconds),
        ("MARKET_LIVE_CACHE_TTL_MINUTES", cache.live_ttl_minutes),
        ("MARKET_NEWS_CACHE_TTL_MINUTES", cache.news_ttl_minutes),
        ("MARKET_NEWS_SUMMARY_CACHE_TTL_MINUTES", cache.news_summary_ttl_minutes),
        ("LOCAL_SUMMARIZER_MAX_LENGTH", news.local_summarizer_max_length),
        ("LOCAL_SUMMARIZER_MIN_LENGTH", news.local_summarizer_min_length),
        ("LOCAL_SUMMARIZER_INPUT_MAX_TOKENS", news.local_summarizer_input_max_tokens),
        ("ARTICLE_NOTE_MAX_LENGTH", news.article_note_max_length),
        ("ARTICLE_NOTE_MIN_LENGTH", news.article_note_min_length),
    ):
        _validate_positive(name, value)

    if environment == AppEnvironment.PROD:
        if database.password == "postgres":
            raise ValueError("MARKET_DB_PASSWORD must not use the default value in prod.")
        if not security.api_key:
            raise ValueError("MARKET_API_KEY is required in prod.")
        if not news.api_key:
            raise ValueError("NEWS_API_KEY is required in prod.")
        if any("localhost" in origin for origin in cors.allowed_origins):
            raise ValueError("ALLOWED_ORIGINS must not contain localhost in prod.")

    return Settings(
        environment=environment,
        app_title="Real-Time Market Intelligence API",
        app_description="API for serving transformed market analytics from PostgreSQL/dbt models.",
        app_version="1.0.0",
        log_level=log_level,
        debug=debug,
        database=database,
        cors=cors,
        security=security,
        news=news,
        cache=cache,
    )


settings = build_settings()
