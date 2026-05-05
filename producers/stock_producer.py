import json
import os
import time
from datetime import datetime, timezone

import yfinance as yf
from dotenv import load_dotenv
from kafka import KafkaProducer


load_dotenv()

TOPIC_NAME = os.getenv("MARKET_KAFKA_TOPIC", "stock_prices")
TICKERS = [ticker.strip() for ticker in os.getenv(
    "MARKET_TICKERS",
    "AAPL,MSFT,GOOGL,AMZN,NVDA",
).split(",") if ticker.strip()]


def create_producer():
    return KafkaProducer(
        bootstrap_servers=os.getenv("MARKET_KAFKA_BOOTSTRAP_SERVERS", "localhost:59092"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
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


def main():
    producer = create_producer()

    print(f"Producing real stock events to Kafka topic: {TOPIC_NAME}")

    while True:
        for ticker in TICKERS:
            try:
                event = fetch_stock_event(ticker)
                producer.send(TOPIC_NAME, event)
                producer.flush()
                print(event)
            except Exception as exc:
                print(f"Failed to fetch {ticker}: {exc}")

        time.sleep(60)


if __name__ == "__main__":
    main()
