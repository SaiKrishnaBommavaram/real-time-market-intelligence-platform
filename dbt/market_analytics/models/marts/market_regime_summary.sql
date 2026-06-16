{{ config(
    alias='market_regime_summary'
) }}

WITH daily AS (
    SELECT
        trade_date,
        ticker,
        benchmark_ticker,
        relative_price_change_pct,
        price_change_pct,
        volume_vs_avg_ratio,
        anomaly_flag,
        last_updated_at
    FROM {{ ref('daily_stock_summary') }}
),
risk AS (
    SELECT
        ticker,
        trade_date,
        rolling_volatility_7d
    FROM {{ ref('stock_risk_indicators') }}
),
joined AS (
    SELECT
        daily.trade_date,
        daily.ticker,
        daily.benchmark_ticker,
        COALESCE(daily.relative_price_change_pct, daily.price_change_pct, 0) AS relative_move_pct,
        daily.volume_vs_avg_ratio,
        daily.anomaly_flag,
        risk.rolling_volatility_7d,
        daily.last_updated_at
    FROM daily
    LEFT JOIN risk
        ON daily.ticker = risk.ticker
        AND daily.trade_date = risk.trade_date
),
benchmark_leaders AS (
    SELECT
        trade_date,
        benchmark_ticker,
        COUNT(*) AS benchmark_count,
        ROW_NUMBER() OVER (
            PARTITION BY trade_date
            ORDER BY COUNT(*) DESC, benchmark_ticker
        ) AS benchmark_rank
    FROM joined
    WHERE benchmark_ticker IS NOT NULL
    GROUP BY trade_date, benchmark_ticker
)
SELECT
    joined.trade_date,
    CASE
        WHEN AVG(COALESCE(joined.rolling_volatility_7d, 0)) >= 6
            AND AVG(joined.volume_vs_avg_ratio) >= 1.4 THEN 'risk_off_high_volatility'
        WHEN AVG(COALESCE(joined.rolling_volatility_7d, 0)) >= 4 THEN 'high_volatility'
        WHEN AVG(COALESCE(joined.relative_move_pct, 0)) >= 1.5 THEN 'broad_risk_on'
        WHEN AVG(COALESCE(joined.relative_move_pct, 0)) <= -1.5 THEN 'broad_risk_off'
        ELSE 'balanced'
    END AS regime_label,
    ROUND(AVG(COALESCE(joined.relative_move_pct, 0)), 4) AS avg_relative_move_pct,
    ROUND(AVG(joined.volume_vs_avg_ratio), 4) AS avg_volume_ratio,
    ROUND(AVG(joined.rolling_volatility_7d), 4) AS avg_volatility_7d,
    ROUND(AVG(CASE WHEN COALESCE(joined.relative_move_pct, 0) < 0 THEN 1.0 ELSE 0.0 END), 4) AS risk_off_share,
    ROUND(AVG(CASE WHEN COALESCE(joined.relative_move_pct, 0) > 0 THEN 1.0 ELSE 0.0 END), 4) AS outperformer_share,
    COUNT(*) AS ticker_count,
    COUNT(*) FILTER (WHERE joined.anomaly_flag <> 'normal') AS anomaly_count,
    MAX(CASE WHEN benchmark_leaders.benchmark_rank = 1 THEN benchmark_leaders.benchmark_ticker END) AS benchmark_leader,
    MAX(joined.last_updated_at) AS last_updated_at
FROM joined
LEFT JOIN benchmark_leaders
    ON joined.trade_date = benchmark_leaders.trade_date
GROUP BY joined.trade_date
