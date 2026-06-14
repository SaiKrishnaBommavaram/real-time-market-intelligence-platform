from fastapi.testclient import TestClient

import api.main as api_main
from api.observability import (
    increment_metric,
    observe_timing_ms,
    render_prometheus_metrics,
    set_gauge,
)


def test_render_prometheus_metrics_exports_counters_gauges_and_timings():
    increment_metric("test.export.counter")
    set_gauge("test.export.gauge", 42)
    observe_timing_ms("test.export.duration", 12.5)
    observe_timing_ms("test.export.duration", 7.5)

    body = render_prometheus_metrics()

    assert "test_export_counter_total" in body
    assert "test_export_gauge" in body
    assert "test_export_duration_milliseconds_count" in body
    assert "test_export_duration_milliseconds_sum" in body
    assert "test_export_duration_milliseconds_max" in body
    assert "test_export_duration_milliseconds_avg" in body


def test_metrics_route_returns_prometheus_scrape_output(monkeypatch):
    monkeypatch.setattr(api_main, "run_startup_checks", lambda: None)
    increment_metric("test.route.counter")

    with TestClient(api_main.app) as client:
        response = client.get("/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "test_route_counter_total" in response.text
