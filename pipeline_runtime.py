import json
import logging
import random
import sys
import time
from collections import defaultdict
from threading import Lock


class StructuredFormatter(logging.Formatter):
    RESERVED_FIELDS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in self.RESERVED_FIELDS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


_METRIC_COUNTERS = defaultdict(int)
_METRIC_GAUGES = {}
_METRIC_LOCK = Lock()


def get_logger(name: str):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def increment_metric(name: str, value: int = 1):
    with _METRIC_LOCK:
        _METRIC_COUNTERS[name] += value


def set_gauge(name: str, value):
    with _METRIC_LOCK:
        _METRIC_GAUGES[name] = value


def get_metrics_snapshot():
    with _METRIC_LOCK:
        return {
            "counters": dict(_METRIC_COUNTERS),
            "gauges": dict(_METRIC_GAUGES),
        }


def log_metrics_snapshot(logger, process_name: str):
    snapshot = get_metrics_snapshot()
    logger.info(
        "metrics_snapshot",
        extra={
            "process": process_name,
            "counters": snapshot["counters"],
            "gauges": snapshot["gauges"],
        },
    )


def retry(
    operation_name,
    func,
    exceptions,
    logger,
    max_attempts=3,
    base_delay_seconds=1.0,
    context=None,
):
    details = context or {}

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as exc:
            if attempt == max_attempts:
                increment_metric(f"{operation_name}.failed")
                logger.error(
                    "operation_failed",
                    extra={
                        "operation": operation_name,
                        "attempt": attempt,
                        **details,
                    },
                    exc_info=exc,
                )
                raise

            delay_seconds = base_delay_seconds * (2 ** (attempt - 1))
            delay_seconds += random.uniform(0, base_delay_seconds / 4)
            increment_metric(f"{operation_name}.retry")
            logger.warning(
                "operation_retry",
                extra={
                    "operation": operation_name,
                    "attempt": attempt,
                    "next_delay_seconds": round(delay_seconds, 2),
                    **details,
                },
                exc_info=exc,
            )
            time.sleep(delay_seconds)
