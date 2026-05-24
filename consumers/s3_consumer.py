import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from pipeline_runtime import get_logger, retry

try:
    from consumers.event_validation import validate_stock_event
except ModuleNotFoundError:
    from event_validation import validate_stock_event


load_dotenv()

TOPIC_NAME = os.getenv("MARKET_KAFKA_TOPIC", "stock_prices")
BUCKET_NAME = os.getenv("MARKET_S3_BUCKET", "market-data-lake")
CONSUMER_MAX_RETRIES = int(os.getenv("MARKET_CONSUMER_MAX_RETRIES", "3"))
CONSUMER_BACKOFF_SECONDS = float(os.getenv("MARKET_CONSUMER_BACKOFF_SECONDS", "1"))

logger = get_logger("market.s3_consumer")


def create_consumer():
    return KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=os.getenv("MARKET_KAFKA_BOOTSTRAP_SERVERS", "localhost:59092"),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id="stock_price_s3_consumer",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def create_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("MARKET_S3_ENDPOINT_URL", "http://localhost:59000"),
        aws_access_key_id=os.getenv("MARKET_MINIO_ROOT_USER", "minioadmin"),
        aws_secret_access_key=os.getenv("MARKET_MINIO_ROOT_PASSWORD", "minioadmin"),
        region_name=os.getenv("MARKET_S3_REGION", "us-east-1"),
    )


def upload_event_to_s3(s3_client, event):
    now = datetime.now(timezone.utc)

    date_partition = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%dT%H%M%S%f")

    ticker = event["ticker"]

    s3_key = (
        f"raw/stocks/date={date_partition}/"
        f"ticker={ticker}/"
        f"event_{timestamp}.json"
    )

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(event),
        ContentType="application/json",
    )

    return s3_key


def upload_event_to_s3_with_retry(s3_client, event, message):
    return retry(
        "upload_event_to_s3",
        lambda: upload_event_to_s3(s3_client, event),
        (BotoCoreError, ClientError),
        logger,
        max_attempts=CONSUMER_MAX_RETRIES,
        base_delay_seconds=CONSUMER_BACKOFF_SECONDS,
        context={
            "ticker": event["ticker"],
            "topic": message.topic,
            "partition": message.partition,
            "offset": message.offset,
            "bucket": BUCKET_NAME,
        },
    )


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


def main():
    consumer = create_consumer()
    s3_client = create_s3_client()

    logger.info(
        "consumer_started",
        extra={"topic": TOPIC_NAME, "sink": "s3", "bucket": BUCKET_NAME},
    )

    try:
        for message in consumer:
            try:
                event = validate_stock_event(message.value)
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "invalid_event_skipped",
                    extra={
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "sink": "s3",
                    },
                    exc_info=exc,
                )
                commit_offset(consumer, message, "invalid_event")
                continue

            try:
                s3_key = upload_event_to_s3_with_retry(s3_client, event, message)
                commit_offset(consumer, message, "persisted")
                logger.info(
                    "event_persisted",
                    extra={
                        "ticker": event["ticker"],
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "sink": "s3",
                        "bucket": BUCKET_NAME,
                        "s3_key": s3_key,
                    },
                )
            except (BotoCoreError, ClientError) as exc:
                logger.error(
                    "event_persist_failed",
                    extra={
                        "ticker": event["ticker"],
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "sink": "s3",
                        "bucket": BUCKET_NAME,
                    },
                    exc_info=exc,
                )

    except KeyboardInterrupt:
        logger.info("consumer_stopping", extra={"topic": TOPIC_NAME, "sink": "s3"})

    finally:
        consumer.close()


if __name__ == "__main__":
    main()
