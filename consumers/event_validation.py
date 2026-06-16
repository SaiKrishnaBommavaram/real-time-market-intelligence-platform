import math
from datetime import datetime


REQUIRED_EVENT_FIELDS = ("ticker", "price", "volume", "event_time", "source")
ALLOWED_EVENT_KINDS = {"live_snapshot", "historical_bar", "intraday_bar"}
ALLOWED_BAR_INTERVALS = {"snapshot", "1m", "5m", "15m", "30m", "60m", "1d"}
ALLOWED_MARKET_SESSIONS = {"pre", "regular", "post", "closed"}


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
    if event_time.tzinfo is None:
        raise ValueError("Kafka message event_time must include timezone information.")
    source = str(event["source"]).strip() or "unknown"
    open_price = event.get("open_price")
    high_price = event.get("high_price")
    low_price = event.get("low_price")
    close_price = event.get("close_price")
    event_kind = str(event.get("event_kind") or "live_snapshot").strip() or "live_snapshot"
    bar_interval = str(event.get("bar_interval") or "snapshot").strip() or "snapshot"
    market_session = str(event.get("market_session") or "regular").strip() or "regular"

    if event_kind not in ALLOWED_EVENT_KINDS:
        raise ValueError(f"Kafka message event_kind must be one of: {', '.join(sorted(ALLOWED_EVENT_KINDS))}.")
    if bar_interval not in ALLOWED_BAR_INTERVALS:
        raise ValueError(f"Kafka message bar_interval must be one of: {', '.join(sorted(ALLOWED_BAR_INTERVALS))}.")
    if market_session not in ALLOWED_MARKET_SESSIONS:
        raise ValueError(
            f"Kafka message market_session must be one of: {', '.join(sorted(ALLOWED_MARKET_SESSIONS))}."
        )

    def _normalize_optional_price(value, field_name):
        if value is None:
            return None
        normalized = round(float(value), 2)
        if not math.isfinite(normalized) or normalized < 0:
            raise ValueError(
                f"Kafka message {field_name} must be a finite non-negative number.",
            )
        return normalized

    if all(value is not None for value in (open_price, high_price, low_price, close_price)):
        normalized_prices = {
            "open_price": _normalize_optional_price(open_price, "open_price"),
            "high_price": _normalize_optional_price(high_price, "high_price"),
            "low_price": _normalize_optional_price(low_price, "low_price"),
            "close_price": _normalize_optional_price(close_price, "close_price"),
        }
        if normalized_prices["high_price"] < max(
            normalized_prices["open_price"],
            normalized_prices["close_price"],
            normalized_prices["low_price"],
        ):
            raise ValueError("Kafka message high_price must be greater than or equal to open/close/low.")
        if normalized_prices["low_price"] > min(
            normalized_prices["open_price"],
            normalized_prices["close_price"],
            normalized_prices["high_price"],
        ):
            raise ValueError("Kafka message low_price must be less than or equal to open/close/high.")
    else:
        normalized_prices = {
            "open_price": _normalize_optional_price(open_price, "open_price"),
            "high_price": _normalize_optional_price(high_price, "high_price"),
            "low_price": _normalize_optional_price(low_price, "low_price"),
            "close_price": _normalize_optional_price(close_price, "close_price"),
        }

    return {
        "ticker": ticker,
        "price": price,
        "volume": volume,
        "event_time": event_time.isoformat(),
        "source": source[:100],
        "open_price": normalized_prices["open_price"],
        "high_price": normalized_prices["high_price"],
        "low_price": normalized_prices["low_price"],
        "close_price": normalized_prices["close_price"],
        "event_kind": event_kind[:50],
        "bar_interval": bar_interval[:20],
        "market_session": market_session[:20],
    }
