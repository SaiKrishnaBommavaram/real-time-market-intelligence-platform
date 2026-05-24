import json
import os
import time
from datetime import datetime, timezone

import yfinance as yf
from dotenv import load_dotenv
from kafka.errors import KafkaError
from kafka import KafkaProducer

from pipeline_runtime import get_logger, retry


load_dotenv()

TOPIC_NAME = os.getenv("MARKET_KAFKA_TOPIC", "stock_prices")
TICKERS = [ticker.strip() for ticker in os.getenv(
    "MARKET_TICKERS",
    "AAPL,MSFT,GOOGL,AMZN,NVDA",
).split(",") if ticker.strip()]
PRODUCER_POLL_SECONDS = int(os.getenv("MARKET_PRODUCER_POLL_SECONDS", "60"))
PRODUCER_MAX_RETRIES = int(os.getenv("MARKET_PRODUCER_MAX_RETRIES", "3"))
PRODUCER_BACKOFF_SECONDS = float(os.getenv("MARKET_PRODUCER_BACKOFF_SECONDS", "1"))

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
    stock = yf.Ticker(ticker)
    info = stock.fast_info

    return {
        "ticker": ticker,
        "price": round(float(info["last_price"]), 2),
        "volume": int(info.get("last_volume") or 0),
        "event_time": datetime.now(timezone.utc).isoformat(),
        "source": "yfinance",
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


def main():
    producer = create_producer()

    logger.info(
        "producer_started",
        extra={"topic": TOPIC_NAME, "ticker_count": len(TICKERS)},
    )

    while True:
        events = []

        for ticker in TICKERS:
            try:
                event = fetch_stock_event_with_retry(ticker)
                events.append(event)
                logger.info(
                    "stock_event_fetched",
                    extra={
                        "ticker": event["ticker"],
                        "price": event["price"],
                        "volume": event["volume"],
                    },
                )
            except Exception as exc:
                logger.error(
                    "stock_event_fetch_failed",
                    extra={"ticker": ticker},
                    exc_info=exc,
                )

        if events:
            try:
                send_batch(producer, events)
                logger.info(
                    "producer_batch_sent",
                    extra={"topic": TOPIC_NAME, "batch_size": len(events)},
                )
            except Exception as exc:
                logger.error(
                    "producer_batch_failed",
                    extra={"topic": TOPIC_NAME, "batch_size": len(events)},
                    exc_info=exc,
                )

        time.sleep(PRODUCER_POLL_SECONDS)


if __name__ == "__main__":
    main()
