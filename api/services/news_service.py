import re

import requests
from fastapi import HTTPException
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from api.config import settings


_summarizer_tokenizer = None
_summarizer_model = None
_summarizer_load_error = None


def fetch_news_articles(ticker: str):
    if not settings.news_api_key:
        raise HTTPException(
            status_code=503,
            detail="NEWS_API_KEY is not configured.",
        )

    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": ticker,
            "pageSize": 5,
            "apiKey": settings.news_api_key,
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
    return re.sub(r"\s+", " ", text or "").strip()


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
        _summarizer_tokenizer = AutoTokenizer.from_pretrained(settings.local_summarizer_model)
        _summarizer_model = AutoModelForSeq2SeqLM.from_pretrained(
            settings.local_summarizer_model,
        )
        return _summarizer_tokenizer, _summarizer_model
    except Exception as exc:
        _summarizer_load_error = str(exc)
        raise RuntimeError(_summarizer_load_error) from exc


def summarize_text(text: str, max_length: int, min_length: int):
    if not text.strip():
        return ""

    tokenizer, model = get_summarizer_components()
    prompt = f"summarize: {text.strip()}"
    inputs = tokenizer(
        prompt,
        max_length=settings.local_summarizer_input_max_tokens,
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
                settings.article_note_max_length,
                settings.article_note_min_length,
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
            settings.local_summarizer_max_length,
            settings.local_summarizer_min_length,
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
            "model": settings.local_summarizer_model,
            "fallback_reason": None,
        }
    except Exception as exc:
        return build_fallback_summary(ticker, articles, str(exc))
