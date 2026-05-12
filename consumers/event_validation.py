import math
from datetime import datetime


REQUIRED_EVENT_FIELDS = ("ticker", "price", "volume", "event_time", "source")


def validate_stock_event(event):
    if not isinstance(event, dict):
        raise ValueError("Kafka message value must be a JSON object.")

    missing_fields = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
    if missing_fields:
        raise ValueError(f"Kafka message is missing fields: {', '.join(missing_fields)}")

    ticker = str(event["ticker"]).strip().upper()
    if not ticker:
        raise ValueError("Kafka message ticker must not be empty.")
    if len(ticker) > 10:
        raise ValueError("Kafka message ticker must be 10 characters or fewer.")

    price = round(float(event["price"]), 2)
    if not math.isfinite(price) or price < 0:
        raise ValueError("Kafka message price must be a finite non-negative number.")

    volume = int(event["volume"])
    if volume < 0:
        raise ValueError("Kafka message volume must be non-negative.")

    event_time = datetime.fromisoformat(str(event["event_time"]).replace("Z", "+00:00"))
    source = str(event["source"]).strip() or "unknown"

    return {
        "ticker": ticker,
        "price": price,
        "volume": volume,
        "event_time": event_time.isoformat(),
        "source": source[:100],
    }
