from collections import defaultdict
import re
from threading import Lock

from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, SummaryMetricFamily


PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _sanitize_metric_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized.lower() or "metric"


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

    def export(self):
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: {
                        "count": values["count"],
                        "sum": float(values["sum"]),
                        "max": float(values["max"]),
                    }
                    for name, values in self._histograms.items()
                },
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


class PrometheusMetricsCollector:
    def collect(self):
        exported = metrics_registry.export()

        for name, value in exported["counters"].items():
            metric_name = _sanitize_metric_name(name)
            if not metric_name.endswith("_total"):
                metric_name = f"{metric_name}_total"
            family = CounterMetricFamily(metric_name, f"Counter for {name}")
            family.add_metric([], value)
            yield family

        for name, value in exported["gauges"].items():
            family = GaugeMetricFamily(
                _sanitize_metric_name(name),
                f"Gauge for {name}",
            )
            family.add_metric([], float(value))
            yield family

        for name, values in exported["histograms"].items():
            base_name = f"{_sanitize_metric_name(name)}_milliseconds"
            summary = SummaryMetricFamily(base_name, f"Timing summary for {name}")
            summary.add_metric([], values["count"], values["sum"])
            yield summary

            max_gauge = GaugeMetricFamily(
                f"{base_name}_max",
                f"Maximum observed milliseconds for {name}",
            )
            max_gauge.add_metric([], values["max"])
            yield max_gauge

            avg_gauge = GaugeMetricFamily(
                f"{base_name}_avg",
                f"Average observed milliseconds for {name}",
            )
            average = (values["sum"] / values["count"]) if values["count"] else 0.0
            avg_gauge.add_metric([], average)
            yield avg_gauge


def render_prometheus_metrics() -> str:
    registry = CollectorRegistry()
    registry.register(PrometheusMetricsCollector())
    return generate_latest(registry).decode("utf-8")
