from collections import defaultdict
from threading import Lock


class MetricsRegistry:
    def __init__(self):
        self._counters = defaultdict(int)
        self._gauges = {}
        self._histograms = defaultdict(lambda: {"count": 0, "sum": 0.0, "max": 0.0})
        self._lock = Lock()

    def increment(self, name: str, value: int = 1):
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float):
        with self._lock:
            self._gauges[name] = value

    def observe_ms(self, name: str, value_ms: float):
        with self._lock:
            histogram = self._histograms[name]
            histogram["count"] += 1
            histogram["sum"] += float(value_ms)
            histogram["max"] = max(histogram["max"], float(value_ms))

    def snapshot(self):
        with self._lock:
            timings = {}
            for name, histogram in self._histograms.items():
                average = histogram["sum"] / histogram["count"] if histogram["count"] else 0.0
                timings[name] = {
                    "count": histogram["count"],
                    "avg_ms": round(average, 2),
                    "max_ms": round(histogram["max"], 2),
                }

            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timings": timings,
            }


metrics_registry = MetricsRegistry()


def increment_metric(name: str, value: int = 1):
    metrics_registry.increment(name, value=value)


def set_gauge(name: str, value: float):
    metrics_registry.set_gauge(name, value=value)


def observe_timing_ms(name: str, value_ms: float):
    metrics_registry.observe_ms(name, value_ms=value_ms)


def get_metrics_snapshot():
    return metrics_registry.snapshot()
