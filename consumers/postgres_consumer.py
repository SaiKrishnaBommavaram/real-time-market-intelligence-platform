import json

import psycopg2
from kafka import KafkaConsumer


TOPIC_NAME = "stock_prices"


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="market_data",
        user="postgres",
        password="postgres",
    )


def create_table():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_prices (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            volume BIGINT NOT NULL,
            event_time TIMESTAMPTZ NOT NULL,
            source VARCHAR(100),
            inserted_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def create_consumer():
    return KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers="localhost:9092",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="stock_price_postgres_consumer",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def insert_event(conn, event):
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO stock_prices (
            ticker,
            price,
            volume,
            event_time,
            source
        )
        VALUES (%s, %s, %s, %s, %s);
        """,
        (
            event["ticker"],
            event["price"],
            event["volume"],
            event["event_time"],
            event["source"],
        ),
    )

    conn.commit()
    cur.close()


def main():
    create_table()

    conn = get_db_connection()
    consumer = create_consumer()

    print(f"Consuming Kafka topic: {TOPIC_NAME}")
    print("Writing events into PostgreSQL...")

    try:
        for message in consumer:
            event = message.value
            insert_event(conn, event)
            print(f"Inserted event: {event}")

    except KeyboardInterrupt:
        print("Stopping consumer...")

    finally:
        consumer.close()
        conn.close()


if __name__ == "__main__":
    main()