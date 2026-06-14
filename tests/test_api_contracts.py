import re
from pathlib import Path

from api.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_API_PATH = PROJECT_ROOT / "dashboard" / "src" / "api.js"


def _normalize_dashboard_path(path: str) -> str:
    normalized = path.replace("${ticker}", "{ticker}")
    return f"/v1{normalized}"


def _collect_dashboard_api_paths() -> set[str]:
    source = DASHBOARD_API_PATH.read_text(encoding="utf-8")
    matches = re.findall(r"getApiRoot\(\)\}(/[^`]+)", source)
    return {_normalize_dashboard_path(match) for match in matches}


def test_openapi_exposes_metrics_and_core_analytics_contracts():
    schema = app.openapi()
    paths = schema["paths"]

    assert "/v1/metrics" in paths
    assert "/v1/market/summary" in paths
    assert "/v1/analytics/intraday/{ticker}" in paths
    assert "/v1/analytics/anomalies" in paths
    assert "/v1/observability/metrics" in paths

    market_summary_ref = (
        paths["/v1/market/summary"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
    )
    intraday_ref = (
        paths["/v1/analytics/intraday/{ticker}"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
    )
    observability_ref = (
        paths["/v1/observability/metrics"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
    )

    assert market_summary_ref.endswith("/MarketSummaryResponse")
    assert intraday_ref.endswith("/IntradayCandlesResponse")
    assert observability_ref.endswith("/ObservabilityResponse")
    assert "text/plain; version=0.0.4; charset=utf-8" in paths["/v1/metrics"]["get"]["responses"]["200"]["content"]


def test_dashboard_api_client_paths_exist_in_openapi():
    schema = app.openapi()
    openapi_paths = set(schema["paths"].keys())
    dashboard_paths = _collect_dashboard_api_paths()

    missing = sorted(path for path in dashboard_paths if path not in openapi_paths)
    assert not missing, f"Dashboard API client references unknown backend routes: {missing}"
