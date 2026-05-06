import os
import re
from datetime import datetime, timezone

import requests
import yfinance as yf
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import Json
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from api.database import get_db_connection

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
LOCAL_SUMMARIZER_MODEL = os.getenv(
    "LOCAL_SUMMARIZER_MODEL",
    "sshleifer/distilbart-cnn-12-6",
)
LOCAL_SUMMARIZER_MAX_LENGTH = int(os.getenv("LOCAL_SUMMARIZER_MAX_LENGTH", "90"))
LOCAL_SUMMARIZER_MIN_LENGTH = int(os.getenv("LOCAL_SUMMARIZER_MIN_LENGTH", "35"))
LOCAL_SUMMARIZER_INPUT_MAX_TOKENS = int(
    os.getenv("LOCAL_SUMMARIZER_INPUT_MAX_TOKENS", "1024")
)
ARTICLE_NOTE_MAX_LENGTH = int(os.getenv("ARTICLE_NOTE_MAX_LENGTH", "60"))
ARTICLE_NOTE_MIN_LENGTH = int(os.getenv("ARTICLE_NOTE_MIN_LENGTH", "20"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX")
_summarizer_tokenizer = None
_summarizer_model = None
_summarizer_load_error = None
_search_cache_table_ready = False


app = FastAPI(
    title="Real-Time Market Intelligence API",
    description="API for serving transformed market analytics from PostgreSQL/dbt models.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_news_articles(ticker: str):
    if not NEWS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="NEWS_API_KEY is not configured.",
        )

    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": ticker,
            "pageSize": 5,
            "apiKey": NEWS_API_KEY,
            "sortBy": "publishedAt",
            "language": "en",
        },
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()

    if payload.get("status") != "ok":
        raise HTTPException(
            status_code=502,
            detail=payload.get("message", "Failed to fetch news articles."),
        )

    analyzer = SentimentIntensityAnalyzer()
    articles = []

    for article in payload.get("articles", []):
        title = article.get("title", "")
        description = article.get("description", "")
        text = f"{title}. {description}".strip()
        sentiment = analyzer.polarity_scores(text)["compound"] if text else 0.0

        articles.append(
            {
                "title": title,
                "description": description,
                "url": article.get("url"),
                "sentiment": sentiment,
            }
        )

    return articles


def normalize_article_key(article: dict):
    base_text = " ".join(
        filter(
            None,
            [
                article.get("title", ""),
                article.get("description", ""),
            ],
        )
    ).lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", base_text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return " ".join(normalized.split()[:18])


def dedupe_articles(articles: list):
    seen = set()
    deduped = []

    for article in articles:
        key = normalize_article_key(article)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(article)

    return deduped


def enrich_article_content(article: dict):
    enriched = dict(article)
    url = article.get("url")

    if not url:
        enriched["content"] = article.get("description") or article.get("title") or ""
        return enriched

    try:
        from newspaper import Article

        parsed_article = Article(url)
        parsed_article.download()
        parsed_article.parse()
        article_text = parsed_article.text.strip()
    except Exception:
        article_text = ""

    fallback_text = " ".join(
        filter(
            None,
            [
                article.get("title"),
                article.get("description"),
            ],
        )
    ).strip()

    enriched["content"] = article_text or fallback_text
    return enriched


def ensure_stock_search_cache_table():
    global _search_cache_table_ready

    if _search_cache_table_ready:
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_search_cache (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            cache_date DATE NOT NULL,
            live_price NUMERIC(10, 2),
            live_volume BIGINT,
            live_event_time TIMESTAMPTZ,
            live_source VARCHAR(100),
            news_articles JSONB,
            news_summary TEXT,
            summary_source VARCHAR(100),
            summary_model VARCHAR(255),
            summary_fallback_reason TEXT,
            live_updated_at TIMESTAMPTZ,
            news_updated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (ticker, cache_date)
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()
    _search_cache_table_ready = True


def get_today_cache_date():
    return datetime.now(timezone.utc).date()


def get_daily_stock_search_cache(ticker: str):
    ensure_stock_search_cache_table()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM stock_search_cache
        WHERE ticker = %s AND cache_date = %s;
        """,
        (ticker, get_today_cache_date()),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def upsert_live_stock_cache(ticker: str, payload: dict):
    ensure_stock_search_cache_table()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO stock_search_cache (
            ticker,
            cache_date,
            live_price,
            live_volume,
            live_event_time,
            live_source,
            live_updated_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (ticker, cache_date)
        DO UPDATE SET
            live_price = EXCLUDED.live_price,
            live_volume = EXCLUDED.live_volume,
            live_event_time = EXCLUDED.live_event_time,
            live_source = EXCLUDED.live_source,
            live_updated_at = NOW(),
            updated_at = NOW();
        """,
        (
            ticker,
            get_today_cache_date(),
            payload["price"],
            payload["volume"],
            payload["event_time"],
            payload["source"],
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def upsert_news_cache(ticker: str, articles: list, summary: dict):
    ensure_stock_search_cache_table()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO stock_search_cache (
            ticker,
            cache_date,
            news_articles,
            news_summary,
            summary_source,
            summary_model,
            summary_fallback_reason,
            news_updated_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (ticker, cache_date)
        DO UPDATE SET
            news_articles = EXCLUDED.news_articles,
            news_summary = EXCLUDED.news_summary,
            summary_source = EXCLUDED.summary_source,
            summary_model = EXCLUDED.summary_model,
            summary_fallback_reason = EXCLUDED.summary_fallback_reason,
            news_updated_at = NOW(),
            updated_at = NOW();
        """,
        (
            ticker,
            get_today_cache_date(),
            Json(articles),
            summary["summary"],
            summary["source"],
            summary["model"],
            summary["fallback_reason"],
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def build_cached_live_response(ticker: str, cached_row: dict):
    return {
        "ticker": ticker,
        "price": round(float(cached_row["live_price"]), 2),
        "volume": int(cached_row.get("live_volume") or 0),
        "event_time": cached_row["live_event_time"].isoformat(),
        "source": "daily_cache",
    }


def build_cached_news_response(ticker: str, cached_row: dict):
    return {
        "ticker": ticker,
        "articles": cached_row["news_articles"] or [],
        "source": "daily_cache",
    }


def build_cached_news_summary_response(ticker: str, cached_row: dict):
    return {
        "ticker": ticker,
        "summary": cached_row["news_summary"],
        "source": cached_row["summary_source"],
        "model": cached_row["summary_model"],
        "fallback_reason": cached_row["summary_fallback_reason"],
        "article_count": len(cached_row["news_articles"] or []),
    }


def build_fallback_summary(ticker: str, articles, reason: str | None = None):
    if not articles:
        message = f"No recent articles were available to summarize for {ticker}."
        if reason:
            message = f"{message} Fallback reason: {reason}"

        return {
            "ticker": ticker,
            "summary": message,
            "source": "fallback",
            "model": None,
            "fallback_reason": reason or "No articles available",
        }

    avg_sentiment = sum(article["sentiment"] for article in articles) / len(articles)
    sentiment_label = (
        "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "mixed"
    )
    top_headlines = ", ".join(
        article["title"] for article in articles[:3] if article.get("title")
    )

    summary = (
        f"Recent coverage for {ticker} is {sentiment_label} overall based on "
        f"{len(articles)} articles. Key headlines include: {top_headlines}."
    )

    if reason:
        summary = f"{summary} Local summarizer fallback used because: {reason}"

    return {
        "ticker": ticker,
        "summary": summary,
        "source": "fallback",
        "model": None,
        "fallback_reason": reason or "Local summary unavailable",
    }


def normalize_generated_summary(text: str):
    normalized = re.sub(r"\s+", " ", text or "").strip()
    return normalized


def is_low_quality_summary(ticker: str, summary_text: str):
    normalized = normalize_generated_summary(summary_text)

    if not normalized:
        return True

    disallowed_fragments = [
        f"{ticker} market news digest",
        "Write a concise market-facing summary",
        "Primary headlines:",
        "Condensed article notes:",
        "Headline:",
        "Article:",
    ]

    return any(fragment.lower() in normalized.lower() for fragment in disallowed_fragments)


def get_summarizer_components():
    global _summarizer_tokenizer, _summarizer_model, _summarizer_load_error

    if _summarizer_tokenizer is not None and _summarizer_model is not None:
        return _summarizer_tokenizer, _summarizer_model

    if _summarizer_load_error is not None:
        raise RuntimeError(_summarizer_load_error)

    try:
        _summarizer_tokenizer = AutoTokenizer.from_pretrained(LOCAL_SUMMARIZER_MODEL)
        _summarizer_model = AutoModelForSeq2SeqLM.from_pretrained(
            LOCAL_SUMMARIZER_MODEL,
        )
        return _summarizer_tokenizer, _summarizer_model
    except Exception as exc:
        _summarizer_load_error = str(exc)
        raise RuntimeError(_summarizer_load_error) from exc


def summarize_text(text: str, max_length: int, min_length: int):
    if not text.strip():
        return ""

    try:
        tokenizer, model = get_summarizer_components()
        prompt = f"summarize: {text.strip()}"
        inputs = tokenizer(
            prompt,
            max_length=LOCAL_SUMMARIZER_INPUT_MAX_TOKENS,
            truncation=True,
            return_tensors="pt",
        )
        summary_tokens = model.generate(
            **inputs,
            max_length=max_length,
            min_length=min_length,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3,
            length_penalty=1.1,
        )
        return normalize_generated_summary(
            tokenizer.decode(
            summary_tokens[0],
            skip_special_tokens=True,
            )
        )
    except Exception:
        raise


def build_market_summary_input(ticker: str, article_notes: list, enriched_articles: list):
    avg_sentiment = sum(article["sentiment"] for article in enriched_articles) / len(
        enriched_articles
    )
    sentiment_label = (
        "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "mixed"
    )
    notes_block = "\n".join(f"- {note}" for note in article_notes if note)
    titles_block = "\n".join(
        f"- {article.get('title', '').strip()}"
        for article in enriched_articles[:5]
        if article.get("title")
    )
    return (
        f"Ticker: {ticker}\n"
        f"Overall sentiment: {sentiment_label}\n"
        f"Top headlines:\n{titles_block}\n"
        f"Article summaries:\n{notes_block}\n"
        "Summarize the main drivers, risks, and overall direction in 2-3 sentences."
    )


def summarize_news_with_local_model(ticker: str, articles):
    if not articles:
        return build_fallback_summary(ticker, articles, "No articles available")

    try:
        deduped_articles = dedupe_articles(articles)
        enriched_articles = [enrich_article_content(article) for article in deduped_articles]
        usable_articles = [
            article for article in enriched_articles if (article.get("content") or "").strip()
        ]

        if not usable_articles:
            return build_fallback_summary(ticker, articles, "Article text was empty")

        article_notes = []
        for article in usable_articles:
            note_input = (
                f"Headline: {article.get('title', '').strip()}\n"
                f"Article: {article.get('content', '').strip()}"
            )
            article_note = summarize_text(
                note_input,
                ARTICLE_NOTE_MAX_LENGTH,
                ARTICLE_NOTE_MIN_LENGTH,
            )
            if article_note:
                article["article_summary"] = article_note
                article_notes.append(article_note)

        if not article_notes:
            return build_fallback_summary(
                ticker,
                articles,
                "Local summarizer returned empty article notes",
            )

        final_input = build_market_summary_input(ticker, article_notes, usable_articles)
        summary_text = summarize_text(
            final_input,
            LOCAL_SUMMARIZER_MAX_LENGTH,
            LOCAL_SUMMARIZER_MIN_LENGTH,
        )

        if not summary_text:
            return build_fallback_summary(
                ticker,
                articles,
                "Local summarizer returned an empty final summary",
            )

        if is_low_quality_summary(ticker, summary_text):
            return build_fallback_summary(
                ticker,
                articles,
                "Local summarizer echoed the prompt instead of generating a summary",
            )

        return {
            "ticker": ticker,
            "summary": summary_text,
            "source": "local_model",
            "model": LOCAL_SUMMARIZER_MODEL,
            "fallback_reason": None,
        }
    except Exception as exc:
        return build_fallback_summary(ticker, articles, str(exc))


@app.get("/")
def root():
    return {
        "message": "Real-Time Market Intelligence API is running",
        "available_endpoints": [
            "/health",
            "/market/summary",
            "/stocks/{ticker}/summary",
            "/stocks/{ticker}/live",
            "/stocks/{ticker}/news",
            "/stocks/{ticker}/news/summary",
        ],
    }


@app.get("/health")
def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 AS status;")
        result = cur.fetchone()
        cur.close()
        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
            "query_result": result,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/market/summary")
def get_market_summary():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                ticker,
                trade_date,
                event_count,
                avg_price,
                min_price,
                max_price,
                total_volume,
                last_updated_at
            FROM analytics.daily_stock_summary
            ORDER BY trade_date DESC, ticker
            LIMIT 100;
            """
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return {
            "count": len(rows),
            "data": rows,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/stocks/{ticker}/summary")
def get_stock_summary(ticker: str):
    ticker = ticker.upper()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ticker,
            trade_date,
            event_count,
            avg_price,
            min_price,
            max_price,
            total_volume,
            last_updated_at
        FROM analytics.daily_stock_summary
        WHERE ticker = %s
        ORDER BY trade_date DESC;
        """,
        (ticker,),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No summary found for ticker: {ticker}",
        )

    return {
        "ticker": ticker,
        "count": len(rows),
        "data": rows,
    }


@app.get("/stocks/{ticker}/live")
def get_live_stock_data(ticker: str):
    ticker = ticker.strip().upper()

    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info

        price = info.get("last_price")
        volume = info.get("last_volume")

        if price is None:
            history = stock.history(period="5d", interval="1d")

            if history.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No market data found for ticker: {ticker}",
                )

            latest_row = history.iloc[-1]
            price = latest_row["Close"]
            volume = latest_row["Volume"]

        payload = {
            "ticker": ticker,
            "price": round(float(price), 2),
            "volume": int(volume or 0),
            "event_time": datetime.now(timezone.utc).isoformat(),
            "source": "yfinance_live_api",
        }
        upsert_live_stock_cache(ticker, payload)
        return payload

    except HTTPException:
        raise

    except Exception as exc:
        cached_row = get_daily_stock_search_cache(ticker)
        if cached_row and cached_row.get("live_price") is not None:
            return build_cached_live_response(ticker, cached_row)

        error_message = str(exc)

        if "Could not resolve host" in error_message or "curl: (6)" in error_message:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Market data provider is unreachable for {ticker}. "
                    f"Yahoo request failed with: {error_message}"
                ),
            )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market data for {ticker}: {error_message}",
        )

@app.get("/stocks/{ticker}/news")
def get_stock_news(ticker: str):
    ticker = ticker.upper()

    try:
        cached_row = get_daily_stock_search_cache(ticker)
        if cached_row and cached_row.get("news_articles"):
            return build_cached_news_response(ticker, cached_row)

        articles = fetch_news_articles(ticker)
        summary = summarize_news_with_local_model(ticker, articles)
        upsert_news_cache(ticker, articles, summary)

        return {
            "ticker": ticker,
            "articles": articles,
            "source": "newsapi",
        }
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/stocks/{ticker}/news/summary")
def get_stock_news_summary(ticker: str):
    ticker = ticker.upper()

    try:
        cached_row = get_daily_stock_search_cache(ticker)
        if (
            cached_row
            and cached_row.get("news_summary")
            and not is_low_quality_summary(ticker, cached_row["news_summary"])
        ):
            return build_cached_news_summary_response(ticker, cached_row)

        if cached_row and cached_row.get("news_articles"):
            articles = cached_row["news_articles"]
        else:
            articles = fetch_news_articles(ticker)

        summary = summarize_news_with_local_model(ticker, articles)
        upsert_news_cache(ticker, articles, summary)
        summary["article_count"] = len(articles)
        return summary
    except HTTPException as exc:
        summary = build_fallback_summary(ticker, [], exc.detail)
        summary["article_count"] = 0
        return summary
    except requests.RequestException as exc:
        summary = build_fallback_summary(ticker, [], str(exc))
        summary["article_count"] = 0
        return summary
    except Exception as exc:
        summary = build_fallback_summary(ticker, [], str(exc))
        summary["article_count"] = 0
        return summary
