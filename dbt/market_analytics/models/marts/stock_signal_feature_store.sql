{{ config(
    alias='stock_signal_feature_store'
) }}

WITH daily AS (
    SELECT *
    FROM {{ ref('daily_stock_summary') }}
),
risk AS (
    SELECT
        ticker,
        trade_date,
        rolling_return_7d_pct,
        rolling_volatility_7d,
        sharpe_like_ratio_7d
    FROM {{ ref('stock_risk_indicators') }}
),
drawdown AS (
    SELECT
        ticker,
        trade_date,
        drawdown_pct
    FROM {{ ref('stock_drawdown_recovery') }}
),
anomaly AS (
    SELECT
        ticker,
        trade_date,
        anomaly_severity_score
    FROM {{ ref('stock_anomaly_history') }}
),
joined AS (
    SELECT
        daily.ticker,
        daily.company_name,
        daily.sector,
        daily.benchmark_ticker,
        daily.benchmark_name,
        daily.trade_date,
        daily.close_price,
        daily.previous_close_price,
        daily.price_change_pct,
        daily.benchmark_price_change_pct,
        daily.relative_price_change_pct,
        daily.volume_vs_avg_ratio,
        drawdown.drawdown_pct,
        risk.rolling_return_7d_pct,
        risk.rolling_volatility_7d,
        risk.sharpe_like_ratio_7d,
        daily.anomaly_flag,
        COALESCE(anomaly.anomaly_severity_score, 0) AS anomaly_severity_score,
        CASE
            WHEN COALESCE(risk.rolling_volatility_7d, 0) >= 6 THEN 'high_volatility'
            WHEN COALESCE(risk.rolling_volatility_7d, 0) >= 3 THEN 'elevated_volatility'
            ELSE 'stable'
        END AS market_regime_label
    FROM daily
    LEFT JOIN risk
        ON daily.ticker = risk.ticker
        AND daily.trade_date = risk.trade_date
    LEFT JOIN drawdown
        ON daily.ticker = drawdown.ticker
        AND daily.trade_date = drawdown.trade_date
    LEFT JOIN anomaly
        ON daily.ticker = anomaly.ticker
        AND daily.trade_date = anomaly.trade_date
)
SELECT
    *,
    ROUND(
        (ABS(COALESCE(relative_price_change_pct, price_change_pct)) * 0.45)
        + (GREATEST(volume_vs_avg_ratio - 1, 0) * 2.25)
        + (COALESCE(anomaly_severity_score, 0) * 0.35)
        + (ABS(COALESCE(sharpe_like_ratio_7d, 0)) * 0.25),
        4
    ) AS signal_strength_score,
    NOW() AS feature_generated_at
FROM joined
