import inspect
from pathlib import Path

import yaml

from api.repositories.market_repository import MarketRepository
from api.schemas import (
    AnomalyHistoryRow,
    DailySummaryRow,
    DrawdownRecoveryRow,
    IntradayCandleRow,
    IntradayMoverRow,
    RiskIndicatorRow,
    SectorPerformanceRow,
    SignalFeatureRow,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_SCHEMA_PATH = PROJECT_ROOT / "dbt" / "market_analytics" / "models" / "marts" / "schema.yml"


CONTRACTS = [
    {
        "method": "fetch_market_summary",
        "row_model": DailySummaryRow,
        "dbt_model": "daily_stock_summary",
        "columns": [
            "ticker",
            "company_name",
            "sector",
            "benchmark_ticker",
            "benchmark_name",
            "trade_date",
            "event_count",
            "avg_price",
            "min_price",
            "max_price",
            "total_volume",
            "last_updated_at",
            "open_price",
            "close_price",
            "previous_close_price",
            "benchmark_close_price",
            "benchmark_price_change_pct",
            "relative_price_change_pct",
            "price_change_pct",
            "volume_vs_avg_ratio",
            "anomaly_flag",
        ],
    },
    {
        "method": "fetch_stock_summary",
        "row_model": DailySummaryRow,
        "dbt_model": "daily_stock_summary",
        "columns": [
            "ticker",
            "company_name",
            "sector",
            "benchmark_ticker",
            "benchmark_name",
            "trade_date",
            "event_count",
            "avg_price",
            "min_price",
            "max_price",
            "total_volume",
            "last_updated_at",
            "open_price",
            "close_price",
            "previous_close_price",
            "benchmark_close_price",
            "benchmark_price_change_pct",
            "relative_price_change_pct",
            "price_change_pct",
            "volume_vs_avg_ratio",
            "anomaly_flag",
        ],
    },
    {
        "method": "fetch_intraday_candles",
        "row_model": IntradayCandleRow,
        "dbt_model": "intraday_stock_rollup",
        "columns": [
            "ticker",
            "company_name",
            "sector",
            "benchmark_ticker",
            "benchmark_name",
            "interval_start",
            "market_session",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "previous_close_price",
            "benchmark_close_price",
            "benchmark_interval_change_pct",
            "relative_interval_change_pct",
            "bar_count",
            "total_volume",
            "last_updated_at",
        ],
    },
    {
        "method": "fetch_intraday_movers",
        "row_model": IntradayMoverRow,
        "dbt_model": "intraday_stock_rollup",
        "columns": [
            "ticker",
            "company_name",
            "sector",
            "benchmark_ticker",
            "benchmark_name",
            "interval_start",
            "market_session",
            "close_price",
            "previous_close_price",
            "interval_change_pct",
            "benchmark_interval_change_pct",
            "relative_interval_change_pct",
            "total_volume",
            "bar_count",
        ],
        "dbt_columns": [
            "ticker",
            "company_name",
            "sector",
            "benchmark_ticker",
            "benchmark_name",
            "interval_start",
            "market_session",
            "close_price",
            "previous_close_price",
            "benchmark_interval_change_pct",
            "relative_interval_change_pct",
            "total_volume",
            "bar_count",
        ],
    },
    {
        "method": "fetch_drawdown_recovery",
        "row_model": DrawdownRecoveryRow,
        "dbt_model": "stock_drawdown_recovery",
        "columns": [
            "ticker",
            "trade_date",
            "close_price",
            "rolling_peak_close",
            "drawdown_pct",
            "days_since_peak",
            "recovery_status",
            "last_updated_at",
        ],
    },
    {
        "method": "fetch_risk_indicators",
        "row_model": RiskIndicatorRow,
        "dbt_model": "stock_risk_indicators",
        "columns": [
            "ticker",
            "trade_date",
            "close_price",
            "price_change_pct",
            "rolling_return_7d_pct",
            "rolling_volatility_7d",
            "sharpe_like_ratio_7d",
            "observed_days",
            "last_updated_at",
        ],
    },
    {
        "method": "fetch_sector_performance",
        "row_model": SectorPerformanceRow,
        "dbt_model": "sector_daily_summary",
        "columns": [
            "sector",
            "trade_date",
            "ticker_count",
            "avg_price_change_pct",
            "avg_relative_price_change_pct",
            "avg_volume_ratio",
            "total_volume",
            "anomaly_count",
            "top_ticker",
            "top_ticker_price_change_pct",
        ],
    },
    {
        "method": "fetch_anomaly_history",
        "row_model": AnomalyHistoryRow,
        "dbt_model": "stock_anomaly_history",
        "columns": [
            "ticker",
            "company_name",
            "sector",
            "benchmark_ticker",
            "benchmark_name",
            "trade_date",
            "anomaly_flag",
            "anomaly_severity_score",
            "relative_price_change_pct",
            "price_change_pct",
            "volume_vs_avg_ratio",
            "close_price",
            "total_volume",
        ],
        "dbt_columns": [
            "ticker",
            "trade_date",
            "anomaly_flag",
            "anomaly_severity_score",
            "price_change_pct",
            "volume_vs_avg_ratio",
            "close_price",
            "total_volume",
        ],
    },
    {
        "method": "fetch_signal_features",
        "row_model": SignalFeatureRow,
        "dbt_model": "stock_signal_feature_store",
        "columns": [
            "ticker",
            "company_name",
            "sector",
            "benchmark_ticker",
            "benchmark_name",
            "trade_date",
            "close_price",
            "previous_close_price",
            "price_change_pct",
            "benchmark_price_change_pct",
            "relative_price_change_pct",
            "volume_vs_avg_ratio",
            "drawdown_pct",
            "rolling_return_7d_pct",
            "rolling_volatility_7d",
            "sharpe_like_ratio_7d",
            "anomaly_flag",
            "anomaly_severity_score",
            "market_regime_label",
            "signal_strength_score",
            "feature_generated_at",
        ],
    },
]


def _load_dbt_columns() -> dict[str, set[str]]:
    parsed = yaml.safe_load(DBT_SCHEMA_PATH.read_text(encoding="utf-8"))
    return {
        model["name"]: {column["name"] for column in model.get("columns", [])}
        for model in parsed["models"]
    }


def test_repository_sql_mentions_expected_columns():
    for contract in CONTRACTS:
        method = getattr(MarketRepository, contract["method"])
        source = inspect.getsource(method)
        missing = [column for column in contract["columns"] if column not in source]
        assert not missing, f"{contract['method']} is missing expected SQL columns: {missing}"


def test_pydantic_row_models_cover_repository_contracts():
    for contract in CONTRACTS:
        model_fields = set(contract["row_model"].model_fields.keys())
        missing = [column for column in contract["columns"] if column not in model_fields]
        assert not missing, f"{contract['row_model'].__name__} is missing fields: {missing}"


def test_dbt_marts_cover_repository_contracts():
    dbt_columns = _load_dbt_columns()

    for contract in CONTRACTS:
        expected_columns = contract.get("dbt_columns", contract["columns"])
        missing = [
            column
            for column in expected_columns
            if column not in dbt_columns[contract["dbt_model"]]
        ]
        assert not missing, f"{contract['dbt_model']} is missing dbt columns: {missing}"
