import json
import os
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv
from kafka import KafkaConsumer

try:
    from consumers.event_validation import validate_stock_event
except ModuleNotFoundError:
    from event_validation import validate_stock_event


load_dotenv()

TOPIC_NAME = os.getenv("MARKET_KAFKA_TOPIC", "stock_prices")
BUCKET_NAME = os.getenv("MARKET_S3_BUCKET", "market-data-lake")


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


def main():
    consumer = create_consumer()
    s3_client = create_s3_client()

    print(f"Consuming Kafka topic: {TOPIC_NAME}")
    print(f"Writing raw events to S3 bucket: {BUCKET_NAME}")

    try:
        for message in consumer:
            try:
                event = validate_stock_event(message.value)
            except (TypeError, ValueError) as exc:
                print(f"Skipping invalid Kafka event at offset {message.offset}: {exc}")
                consumer.commit()
                continue

            s3_key = upload_event_to_s3(s3_client, event)
            consumer.commit()
            print(f"Uploaded event to s3://{BUCKET_NAME}/{s3_key}")

    except KeyboardInterrupt:
        print("Stopping S3 consumer...")

    finally:
        consumer.close()


if __name__ == "__main__":
    main()
