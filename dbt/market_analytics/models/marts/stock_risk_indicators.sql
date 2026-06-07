{{ config(
    alias='stock_risk_indicators'
) }}

SELECT
    ticker,
    trade_date,
    close_price,
    price_change_pct,
    ROUND(
        SUM(price_change_pct) OVER (
            PARTITION BY ticker
            ORDER BY trade_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        4
    ) AS rolling_return_7d_pct,
    ROUND(
        STDDEV_POP(price_change_pct) OVER (
            PARTITION BY ticker
            ORDER BY trade_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        4
    ) AS rolling_volatility_7d,
    ROUND(
        CASE
            WHEN STDDEV_POP(price_change_pct) OVER (
                PARTITION BY ticker
                ORDER BY trade_date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) IS NULL
            OR STDDEV_POP(price_change_pct) OVER (
                PARTITION BY ticker
                ORDER BY trade_date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) = 0 THEN NULL
            ELSE (
                AVG(price_change_pct) OVER (
                    PARTITION BY ticker
                    ORDER BY trade_date
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) /
                STDDEV_POP(price_change_pct) OVER (
                    PARTITION BY ticker
                    ORDER BY trade_date
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                )
            )
        END,
        4
    ) AS sharpe_like_ratio_7d,
    COUNT(*) OVER (
        PARTITION BY ticker
        ORDER BY trade_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS observed_days,
    last_updated_at
FROM {{ ref('daily_stock_summary') }}
