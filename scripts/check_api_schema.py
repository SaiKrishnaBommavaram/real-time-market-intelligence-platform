import re
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app


DASHBOARD_API_PATH = PROJECT_ROOT / "dashboard" / "src" / "api.js"
REQUIRED_PATHS = {
    "/v1/",
    "/v1/health",
    "/v1/ready",
    "/v1/metrics",
    "/v1/market/summary",
    "/v1/stocks/{ticker}/live",
    "/v1/stocks/{ticker}/summary",
    "/v1/stocks/{ticker}/news",
    "/v1/stocks/{ticker}/news/summary",
    "/v1/analytics/intraday/movers",
    "/v1/analytics/intraday/{ticker}",
    "/v1/analytics/anomalies",
    "/v1/watchlist",
    "/v1/watchlist/alerts",
    "/v1/observability/metrics",
}


def normalize_dashboard_path(path: str) -> str:
    return f"/v1{path.replace('${ticker}', '{ticker}')}"


def collect_dashboard_api_paths() -> set[str]:
    source = DASHBOARD_API_PATH.read_text(encoding="utf-8")
    matches = re.findall(r"getApiRoot\(\)\}(/[^`]+)", source)
    return {normalize_dashboard_path(match) for match in matches}


def main():
    schema = app.openapi()
    openapi_paths = set(schema["paths"].keys())

    missing_required = sorted(path for path in REQUIRED_PATHS if path not in openapi_paths)
    if missing_required:
        raise SystemExit(f"OpenAPI schema is missing required paths: {missing_required}")

    dashboard_paths = collect_dashboard_api_paths()
    missing_dashboard = sorted(path for path in dashboard_paths if path not in openapi_paths)
    if missing_dashboard:
        raise SystemExit(
            "Dashboard API client references unknown backend routes: "
            f"{missing_dashboard}",
        )

    metrics_content = schema["paths"]["/v1/metrics"]["get"]["responses"]["200"]["content"]
    if "text/plain; version=0.0.4; charset=utf-8" not in metrics_content:
        raise SystemExit("Prometheus metrics route is missing the expected text/plain schema.")

    print("API schema checks passed.")


if __name__ == "__main__":
    main()
