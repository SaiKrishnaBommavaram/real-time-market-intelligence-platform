import os

from dotenv import load_dotenv


load_dotenv()


def _get_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


class Settings:
    app_title = "Real-Time Market Intelligence API"
    app_description = "API for serving transformed market analytics from PostgreSQL/dbt models."
    app_version = "1.0.0"
    log_level = os.getenv("LOG_LEVEL", "INFO")

    news_api_key = os.getenv("NEWS_API_KEY")
    local_summarizer_model = os.getenv(
        "LOCAL_SUMMARIZER_MODEL",
        "sshleifer/distilbart-cnn-12-6",
    )
    local_summarizer_max_length = _get_int("LOCAL_SUMMARIZER_MAX_LENGTH", "90")
    local_summarizer_min_length = _get_int("LOCAL_SUMMARIZER_MIN_LENGTH", "35")
    local_summarizer_input_max_tokens = _get_int(
        "LOCAL_SUMMARIZER_INPUT_MAX_TOKENS",
        "1024",
    )
    article_note_max_length = _get_int("ARTICLE_NOTE_MAX_LENGTH", "60")
    article_note_min_length = _get_int("ARTICLE_NOTE_MIN_LENGTH", "20")
    allowed_origins = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    allowed_origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX")
    api_key = os.getenv("MARKET_API_KEY")
    api_key_header = os.getenv("MARKET_API_KEY_HEADER", "x-api-key")
    rate_limit_max_requests = _get_int("MARKET_RATE_LIMIT_MAX_REQUESTS", "120")
    rate_limit_window_seconds = _get_int("MARKET_RATE_LIMIT_WINDOW_SECONDS", "60")

    db_host = os.getenv("MARKET_DB_HOST", "localhost")
    db_port = _get_int("MARKET_DB_PORT", "55432")
    db_name = os.getenv("MARKET_DB_NAME", "market_data")
    db_user = os.getenv("MARKET_DB_USER", "postgres")
    db_password = os.getenv("MARKET_DB_PASSWORD", "postgres")


settings = Settings()
