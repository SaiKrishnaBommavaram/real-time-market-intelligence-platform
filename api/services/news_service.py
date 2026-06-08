import re
from collections import Counter
from urllib.parse import urlparse

import requests
from fastapi import HTTPException
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from api.config import settings
from api.observability import increment_metric


_summarizer_tokenizer = None
_summarizer_model = None
_summarizer_load_error = None
_sentiment_analyzer = SentimentIntensityAnalyzer()

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "about",
    "after",
    "before",
    "while",
    "amid",
    "over",
    "under",
    "stock",
    "shares",
    "company",
    "market",
    "markets",
    "news",
    "says",
    "said",
    "will",
    "have",
    "has",
    "had",
    "its",
    "their",
    "they",
    "them",
    "you",
    "your",
    "are",
    "was",
    "were",
    "inc",
    "corp",
    "ltd",
    "co",
    "plc",
}

HIGH_QUALITY_DOMAINS = {
    "reuters.com": 1.0,
    "bloomberg.com": 1.0,
    "wsj.com": 0.98,
    "ft.com": 0.98,
    "cnbc.com": 0.95,
    "marketwatch.com": 0.9,
    "finance.yahoo.com": 0.9,
    "seekingalpha.com": 0.82,
    "benzinga.com": 0.8,
    "fool.com": 0.76,
}


def fetch_news_articles(ticker: str):
    if not settings.news_api_key:
        increment_metric("api.news.config_missing")
        raise HTTPException(
            status_code=503,
            detail="NEWS_API_KEY is not configured.",
        )

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": ticker,
                "pageSize": 8,
                "apiKey": settings.news_api_key,
                "sortBy": "publishedAt",
                "language": "en",
            },
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException:
        increment_metric("api.news.provider_failure")
        raise

    payload = response.json()

    if payload.get("status") != "ok":
        increment_metric("api.news.provider_failure")
        raise HTTPException(
            status_code=502,
            detail=payload.get("message", "Failed to fetch news articles."),
        )

    articles = []

    for article in payload.get("articles", []):
        title = article.get("title", "")
        description = article.get("description", "")
        text = f"{title}. {description}".strip()
        sentiment = _sentiment_analyzer.polarity_scores(text)["compound"] if text else 0.0

        enriched_article = {
            "title": title,
            "description": description,
            "url": article.get("url"),
            "published_at": article.get("publishedAt"),
            "source_name": (article.get("source") or {}).get("name"),
            "sentiment": round(sentiment, 4),
        }
        articles.append(enrich_news_article(ticker, enriched_article))

    deduped_articles = dedupe_articles(articles)
    increment_metric("api.news.provider_success")
    return attach_article_clusters(deduped_articles)


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


def normalize_generated_summary(text: str):
    return re.sub(r"\s+", " ", text or "").strip()


def extract_entities(text: str, ticker: str):
    normalized_text = normalize_generated_summary(text)
    if not normalized_text:
        return []

    raw_entities = re.findall(r"\b[A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})*\b", normalized_text)
    filtered_entities = []

    for entity in raw_entities:
        cleaned = entity.strip()
        if cleaned.upper() == ticker.upper():
            filtered_entities.append(cleaned.upper())
            continue
        if cleaned.lower() in STOPWORDS:
            continue
        filtered_entities.append(cleaned)

    counts = Counter(filtered_entities)
    ranked_entities = [
        {"name": name, "count": count}
        for name, count in counts.most_common(6)
    ]
    return ranked_entities


def infer_topic_cluster(article: dict):
    text = " ".join(
        filter(
            None,
            [article.get("title", ""), article.get("description", ""), article.get("content", "")],
        )
    ).lower()

    cluster_rules = {
        "earnings": {"earnings", "revenue", "profit", "guidance", "forecast", "quarter"},
        "analyst": {"upgrade", "downgrade", "rating", "target", "analyst"},
        "deal": {"acquisition", "merger", "partnership", "deal", "buyout"},
        "product": {"launch", "product", "release", "device", "platform", "chip"},
        "regulation": {"regulator", "investigation", "lawsuit", "antitrust", "policy"},
        "macro": {"rates", "inflation", "economy", "fed", "tariff", "jobs"},
    }

    for cluster_name, keywords in cluster_rules.items():
        if any(keyword in text for keyword in keywords):
            return cluster_name

    return "general"


def score_source_quality(url: str | None, source_name: str | None):
    if not url:
        return 0.45

    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower().removeprefix("www.")
    score = HIGH_QUALITY_DOMAINS.get(hostname, 0.65)

    if source_name and "press release" in source_name.lower():
        score = min(score, 0.55)

    return round(score, 2)


def score_news_impact(article: dict):
    text = " ".join(
        filter(
            None,
            [article.get("title", ""), article.get("description", ""), article.get("content", "")],
        )
    ).lower()
    sentiment = abs(float(article.get("sentiment") or 0))
    entity_weight = min(len(article.get("entities") or []), 4) * 0.08
    source_weight = float(article.get("source_quality_score") or 0) * 0.35

    keyword_weight = 0.0
    if any(term in text for term in {"earnings", "guidance", "forecast", "revenue"}):
        keyword_weight += 0.28
    if any(term in text for term in {"merger", "acquisition", "lawsuit", "investigation"}):
        keyword_weight += 0.24
    if any(term in text for term in {"launch", "chip", "ai", "contract", "deal"}):
        keyword_weight += 0.16

    impact_score = min(1.0, round((sentiment * 0.45) + entity_weight + source_weight + keyword_weight, 2))
    if impact_score >= 0.75:
        impact_label = "high"
    elif impact_score >= 0.45:
        impact_label = "medium"
    else:
        impact_label = "low"

    return impact_score, impact_label


def enrich_news_article(ticker: str, article: dict):
    article_text = " ".join(
        filter(None, [article.get("title"), article.get("description")]),
    ).strip()
    entities = extract_entities(article_text, ticker)
    source_quality_score = score_source_quality(article.get("url"), article.get("source_name"))

    enriched_article = {
        **article,
        "entities": entities,
        "source_quality_score": source_quality_score,
        "cluster": infer_topic_cluster(article),
    }
    impact_score, impact_label = score_news_impact(enriched_article)
    enriched_article["impact_score"] = impact_score
    enriched_article["impact_label"] = impact_label
    return enriched_article


def attach_article_clusters(articles: list[dict]):
    cluster_counts = Counter(article.get("cluster", "general") for article in articles)
    clustered_articles = []

    for article in articles:
        cluster_name = article.get("cluster", "general")
        clustered_articles.append(
            {
                **article,
                "cluster_article_count": cluster_counts[cluster_name],
            }
        )

    return clustered_articles


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
    if not enriched.get("entities"):
        enriched["entities"] = extract_entities(enriched["content"], "")
    return enriched


def summarize_cluster_distribution(articles: list[dict]):
    cluster_counts = Counter(article.get("cluster", "general") for article in articles)
    return [
        {"cluster": cluster, "article_count": count}
        for cluster, count in cluster_counts.most_common()
    ]


def build_news_metrics(ticker: str, articles: list[dict]):
    if not articles:
        return {
            "ticker": ticker,
            "avg_sentiment": 0.0,
            "avg_impact_score": 0.0,
            "avg_source_quality_score": 0.0,
            "impact_label": "low",
            "top_entities": [],
            "clusters": [],
        }

    avg_sentiment = sum(float(article.get("sentiment") or 0) for article in articles) / len(articles)
    avg_impact_score = sum(float(article.get("impact_score") or 0) for article in articles) / len(articles)
    avg_source_quality = (
        sum(float(article.get("source_quality_score") or 0) for article in articles) / len(articles)
    )

    entity_counts = Counter()
    for article in articles:
        for entity in article.get("entities") or []:
            name = entity["name"] if isinstance(entity, dict) else str(entity)
            entity_counts[name] += entity.get("count", 1) if isinstance(entity, dict) else 1

    if avg_impact_score >= 0.75:
        impact_label = "high"
    elif avg_impact_score >= 0.45:
        impact_label = "medium"
    else:
        impact_label = "low"

    return {
        "ticker": ticker,
        "avg_sentiment": round(avg_sentiment, 4),
        "avg_impact_score": round(avg_impact_score, 4),
        "avg_source_quality_score": round(avg_source_quality, 4),
        "impact_label": impact_label,
        "top_entities": [
            {"name": name, "count": count}
            for name, count in entity_counts.most_common(8)
        ],
        "clusters": summarize_cluster_distribution(articles),
    }


def build_fallback_summary(ticker: str, articles, reason: str | None = None):
    metrics = build_news_metrics(ticker, articles)

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
            "metrics": metrics,
        }

    avg_sentiment = metrics["avg_sentiment"]
    sentiment_label = (
        "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "mixed"
    )
    top_headlines = ", ".join(
        article["title"] for article in articles[:3] if article.get("title")
    )

    summary = (
        f"Recent coverage for {ticker} is {sentiment_label} overall based on "
        f"{len(articles)} articles. Impact is {metrics['impact_label']} with "
        f"source quality averaging {metrics['avg_source_quality_score']:.2f}. "
        f"Key headlines include: {top_headlines}."
    )

    if reason:
        summary = f"{summary} Local summarizer fallback used because: {reason}"

    return {
        "ticker": ticker,
        "summary": summary,
        "source": "fallback",
        "model": None,
        "fallback_reason": reason or "Local summary unavailable",
        "metrics": metrics,
    }


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
    metrics = build_news_metrics(ticker, enriched_articles)
    avg_sentiment = metrics["avg_sentiment"]
    sentiment_label = (
        "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "mixed"
    )
    notes_block = "\n".join(f"- {note}" for note in article_notes if note)
    titles_block = "\n".join(
        f"- {article.get('title', '').strip()}"
        for article in enriched_articles[:5]
        if article.get("title")
    )
    clusters_block = ", ".join(
        f"{cluster['cluster']} ({cluster['article_count']})"
        for cluster in metrics["clusters"][:4]
    )
    entities_block = ", ".join(entity["name"] for entity in metrics["top_entities"][:6])
    return (
        f"Ticker: {ticker}\n"
        f"Overall sentiment: {sentiment_label}\n"
        f"Average impact: {metrics['impact_label']}\n"
        f"Dominant clusters: {clusters_block}\n"
        f"Named entities: {entities_block}\n"
        f"Top headlines:\n{titles_block}\n"
        f"Article summaries:\n{notes_block}\n"
        "Summarize the main drivers, risks, and likely market impact in 2-3 sentences."
    )


def summarize_news_with_local_model(ticker: str, articles):
    if not articles:
        increment_metric("api.news.summary_fallback")
        return build_fallback_summary(ticker, articles, "No articles available")

    try:
        deduped_articles = dedupe_articles(articles)
        enriched_articles = [enrich_article_content(article) for article in deduped_articles]
        usable_articles = [
            article for article in enriched_articles if (article.get("content") or "").strip()
        ]

        if not usable_articles:
            increment_metric("api.news.summary_fallback")
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
            increment_metric("api.news.summary_fallback")
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
            increment_metric("api.news.summary_fallback")
            return build_fallback_summary(
                ticker,
                articles,
                "Local summarizer returned an empty final summary",
            )

        if is_low_quality_summary(ticker, summary_text):
            increment_metric("api.news.summary_fallback")
            return build_fallback_summary(
                ticker,
                articles,
                "Local summarizer echoed the prompt instead of generating a summary",
            )

        increment_metric("api.news.summary_success")
        return {
            "ticker": ticker,
            "summary": summary_text,
            "source": "local_model",
            "model": settings.local_summarizer_model,
            "fallback_reason": None,
            "metrics": build_news_metrics(ticker, usable_articles),
        }
    except HTTPException:
        raise
    except Exception as exc:
        increment_metric("api.news.summary_failure")
        return build_fallback_summary(ticker, articles, str(exc))
