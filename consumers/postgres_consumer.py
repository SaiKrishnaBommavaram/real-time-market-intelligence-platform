import json
import os

import psycopg2
from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from pipeline_runtime import get_logger, increment_metric, log_metrics_snapshot, retry, set_gauge

try:
    from consumers.event_validation import validate_stock_event
except ModuleNotFoundError:
    from event_validation import validate_stock_event


load_dotenv()

TOPIC_NAME = os.getenv("MARKET_KAFKA_TOPIC", "stock_prices")
CONSUMER_MAX_RETRIES = int(os.getenv("MARKET_CONSUMER_MAX_RETRIES", "3"))
CONSUMER_BACKOFF_SECONDS = float(os.getenv("MARKET_CONSUMER_BACKOFF_SECONDS", "1"))

logger = get_logger("market.postgres_consumer")


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("MARKET_DB_HOST", "localhost"),
        port=int(os.getenv("MARKET_DB_PORT", "55432")),
        database=os.getenv("MARKET_DB_NAME", "market_data"),
        user=os.getenv("MARKET_DB_USER", "postgres"),
        password=os.getenv("MARKET_DB_PASSWORD", "postgres"),
    )


def create_consumer():
    return KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=os.getenv("MARKET_KAFKA_BOOTSTRAP_SERVERS", "localhost:59092"),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id="stock_price_postgres_consumer",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def insert_event(conn, event):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO stock_prices (
                ticker,
                price,
                volume,
                event_time,
                source,
                open_price,
                high_price,
                low_price,
                close_price,
                event_kind,
                bar_interval,
                market_session
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (
                event["ticker"],
                event["price"],
                event["volume"],
                event["event_time"],
                event["source"],
                event["open_price"],
                event["high_price"],
                event["low_price"],
                event["close_price"],
                event["event_kind"],
                event["bar_interval"],
                event["market_session"],
            ),
        )
        conn.commit()
    finally:
        cur.close()


def commit_offset(consumer, message, reason):
    retry(
        "commit_offset",
        consumer.commit,
        (KafkaError,),
        logger,
        max_attempts=CONSUMER_MAX_RETRIES,
        base_delay_seconds=CONSUMER_BACKOFF_SECONDS,
        context={
            "topic": message.topic,
            "partition": message.partition,
            "offset": message.offset,
            "reason": reason,
        },
    )


def insert_event_with_retry(conn, event, message):
    def _insert():
        insert_event(conn, event)

    try:
        retry(
            "insert_postgres_event",
            _insert,
            (psycopg2.Error,),
            logger,
            max_attempts=CONSUMER_MAX_RETRIES,
            base_delay_seconds=CONSUMER_BACKOFF_SECONDS,
            context={
                "ticker": event["ticker"],
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset,
            },
        )
    except psycopg2.Error:
        conn.rollback()
        raise


def main():
    conn = get_db_connection()
    consumer = create_consumer()

    logger.info(
        "consumer_started",
        extra={"topic": TOPIC_NAME, "sink": "postgres"},
    )

    try:
        for message in consumer:
            try:
                event = validate_stock_event(message.value)
            except (TypeError, ValueError) as exc:
                increment_metric("postgres_consumer.invalid_event")
                logger.warning(
                    "invalid_event_skipped",
                    extra={
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                    },
                    exc_info=exc,
                )
                commit_offset(consumer, message, "invalid_event")
                continue

            try:
                insert_event_with_retry(conn, event, message)
                commit_offset(consumer, message, "persisted")
                increment_metric("postgres_consumer.events_persisted")
                set_gauge("postgres_consumer.last_offset", message.offset)
                logger.info(
                    "event_persisted",
                    extra={
                        "ticker": event["ticker"],
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "sink": "postgres",
                    },
                )
            except psycopg2.Error as exc:
                conn.rollback()
                increment_metric("postgres_consumer.persist_failed")
                logger.error(
                    "event_persist_failed",
                    extra={
                        "ticker": event["ticker"],
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "sink": "postgres",
                    },
                    exc_info=exc,
                )
            log_metrics_snapshot(logger, "postgres_consumer")

    except KeyboardInterrupt:
        logger.info("consumer_stopping", extra={"topic": TOPIC_NAME, "sink": "postgres"})

    finally:
        consumer.close()
        conn.close()


if __name__ == "__main__":
    main()
