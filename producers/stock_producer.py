import json
import os
import time
from datetime import datetime, timedelta, timezone

import yfinance as yf
from dotenv import load_dotenv
from kafka.errors import KafkaError
from kafka import KafkaProducer

from market_calendar import infer_market_session
from market_symbols import get_symbol_profile, normalize_ticker, resolve_tracked_tickers
from pipeline_runtime import get_logger, increment_metric, log_metrics_snapshot, retry, set_gauge


load_dotenv()

TOPIC_NAME = os.getenv("MARKET_KAFKA_TOPIC", "stock_prices")
TICKERS = resolve_tracked_tickers(
    [
        ticker.strip()
        for ticker in os.getenv(
            "MARKET_TICKERS",
            "AAPL,MSFT,GOOGL,AMZN,NVDA",
        ).split(",")
        if ticker.strip()
    ]
)
PRODUCER_POLL_SECONDS = int(os.getenv("MARKET_PRODUCER_POLL_SECONDS", "60"))
PRODUCER_MAX_RETRIES = int(os.getenv("MARKET_PRODUCER_MAX_RETRIES", "3"))
PRODUCER_BACKOFF_SECONDS = float(os.getenv("MARKET_PRODUCER_BACKOFF_SECONDS", "1"))
ENABLE_HISTORY_BACKFILL = os.getenv("MARKET_ENABLE_HISTORY_BACKFILL", "true").lower() == "true"
HISTORY_PERIOD = os.getenv("MARKET_HISTORY_PERIOD", "1mo")
HISTORY_INTERVAL = os.getenv("MARKET_HISTORY_INTERVAL", "1h")
HISTORY_LOOKBACK_DAYS = int(os.getenv("MARKET_HISTORY_LOOKBACK_DAYS", "30"))

logger = get_logger("market.producer")


def create_producer():
    return KafkaProducer(
        bootstrap_servers=os.getenv("MARKET_KAFKA_BOOTSTRAP_SERVERS", "localhost:59092"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
        linger_ms=250,
        retries=5,
    )


def fetch_stock_event(ticker):
    canonical_ticker = normalize_ticker(ticker)
    profile = get_symbol_profile(canonical_ticker)
    stock = yf.Ticker(canonical_ticker)
    info = stock.fast_info
    price = round(float(info["last_price"]), 2)
    event_time = datetime.now(timezone.utc)

    return {
        "ticker": canonical_ticker,
        "price": price,
        "volume": int(info.get("last_volume") or 0),
        "event_time": event_time.isoformat(),
        "source": "yfinance",
        "open_price": price,
        "high_price": price,
        "low_price": price,
        "close_price": price,
        "event_kind": "live_snapshot",
        "bar_interval": "snapshot",
        "market_session": infer_market_session(event_time),
        "company_name": profile["company_name"],
        "sector": profile["sector"],
        "benchmark_ticker": profile["benchmark_ticker"],
        "benchmark_name": profile["benchmark_name"],
    }


def fetch_stock_event_with_retry(ticker):
    return retry(
        "fetch_stock_event",
        lambda: fetch_stock_event(ticker),
        (Exception,),
        logger,
        max_attempts=PRODUCER_MAX_RETRIES,
        base_delay_seconds=PRODUCER_BACKOFF_SECONDS,
        context={"ticker": ticker},
    )


def send_batch(producer, events):
    futures = []

    for event in events:
        futures.append((event, producer.send(TOPIC_NAME, event)))

    retry(
        "flush_producer_batch",
        producer.flush,
        (KafkaError,),
        logger,
        max_attempts=PRODUCER_MAX_RETRIES,
        base_delay_seconds=PRODUCER_BACKOFF_SECONDS,
        context={"topic": TOPIC_NAME, "batch_size": len(events)},
    )

    for event, future in futures:
        retry(
            "producer_delivery_ack",
            lambda delivery_future=future: delivery_future.get(timeout=30),
            (KafkaError,),
            logger,
            max_attempts=PRODUCER_MAX_RETRIES,
            base_delay_seconds=PRODUCER_BACKOFF_SECONDS,
            context={"topic": TOPIC_NAME, "ticker": event["ticker"]},
        )


def normalize_event_time(index_value):
    if hasattr(index_value, "to_pydatetime"):
        event_time = index_value.to_pydatetime()
    else:
        event_time = index_value

    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    else:
        event_time = event_time.astimezone(timezone.utc)

    return event_time


def build_historical_events(ticker):
    canonical_ticker = normalize_ticker(ticker)
    profile = get_symbol_profile(canonical_ticker)
    stock = yf.Ticker(canonical_ticker)
    history = stock.history(period=HISTORY_PERIOD, interval=HISTORY_INTERVAL, auto_adjust=False)

    if history.empty:
        return []

    earliest_allowed = datetime.now(timezone.utc) - timedelta(days=HISTORY_LOOKBACK_DAYS)
    events = []

    for timestamp, row in history.iterrows():
        event_time = normalize_event_time(timestamp)
        if event_time < earliest_allowed:
            continue

        close_price = row.get("Close")
        if close_price is None:
            continue

        events.append(
            {
                "ticker": canonical_ticker,
                "price": round(float(close_price), 2),
                "volume": int(row.get("Volume") or 0),
                "event_time": event_time.isoformat(),
                "source": "yfinance_history",
                "open_price": round(float(row.get("Open") or close_price), 2),
                "high_price": round(float(row.get("High") or close_price), 2),
                "low_price": round(float(row.get("Low") or close_price), 2),
                "close_price": round(float(close_price), 2),
                "event_kind": "historical_bar",
                "bar_interval": HISTORY_INTERVAL,
                "market_session": infer_market_session(event_time),
                "company_name": profile["company_name"],
                "sector": profile["sector"],
                "benchmark_ticker": profile["benchmark_ticker"],
                "benchmark_name": profile["benchmark_name"],
            }
        )

    return events


def fetch_historical_events_with_retry(ticker):
    return retry(
        "fetch_historical_events",
        lambda: build_historical_events(ticker),
        (Exception,),
        logger,
        max_attempts=PRODUCER_MAX_RETRIES,
        base_delay_seconds=PRODUCER_BACKOFF_SECONDS,
        context={"ticker": ticker, "history_interval": HISTORY_INTERVAL},
    )


def send_historical_backfill(producer):
    if not ENABLE_HISTORY_BACKFILL:
        logger.info("historical_backfill_disabled", extra={"topic": TOPIC_NAME})
        return

    logger.info(
        "historical_backfill_started",
        extra={
            "topic": TOPIC_NAME,
            "ticker_count": len(TICKERS),
            "history_period": HISTORY_PERIOD,
            "history_interval": HISTORY_INTERVAL,
            "lookback_days": HISTORY_LOOKBACK_DAYS,
        },
    )

    for ticker in TICKERS:
        try:
            events = fetch_historical_events_with_retry(ticker)
            if not events:
                logger.info("historical_backfill_empty", extra={"ticker": ticker})
                continue

            send_batch(producer, events)
            logger.info(
                "historical_backfill_sent",
                extra={"ticker": ticker, "event_count": len(events), "topic": TOPIC_NAME},
            )
        except Exception as exc:
            logger.error(
                "historical_backfill_failed",
                extra={"ticker": ticker, "topic": TOPIC_NAME},
                exc_info=exc,
            )


def main():
    producer = create_producer()

    logger.info(
        "producer_started",
        extra={"topic": TOPIC_NAME, "ticker_count": len(TICKERS)},
    )
    send_historical_backfill(producer)

    while True:
        events = []

        for ticker in TICKERS:
            try:
                event = fetch_stock_event_with_retry(ticker)
                events.append(event)
                increment_metric("producer.events_fetched")
                logger.info(
                    "stock_event_fetched",
                    extra={
                        "ticker": event["ticker"],
                        "price": event["price"],
                        "volume": event["volume"],
                    },
                )
            except Exception as exc:
                increment_metric("producer.fetch_failed")
                logger.error(
                    "stock_event_fetch_failed",
                    extra={"ticker": ticker},
                    exc_info=exc,
                )

        if events:
            try:
                send_batch(producer, events)
                increment_metric("producer.batches_sent")
                increment_metric("producer.events_sent", len(events))
                set_gauge("producer.last_batch_size", len(events))
                logger.info(
                    "producer_batch_sent",
                    extra={"topic": TOPIC_NAME, "batch_size": len(events)},
                )
            except Exception as exc:
                increment_metric("producer.batch_failed")
                logger.error(
                    "producer_batch_failed",
                    extra={"topic": TOPIC_NAME, "batch_size": len(events)},
                    exc_info=exc,
                )

        log_metrics_snapshot(logger, "producer")

        time.sleep(PRODUCER_POLL_SECONDS)


if __name__ == "__main__":
    main()
