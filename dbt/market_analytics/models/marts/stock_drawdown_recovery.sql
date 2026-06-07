{{ config(
    alias='stock_drawdown_recovery'
) }}

WITH ordered AS (
    SELECT
        ticker,
        trade_date,
        close_price,
        last_updated_at,
        MAX(close_price) OVER (
            PARTITION BY ticker
            ORDER BY trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS rolling_peak_close,
        CASE
            WHEN close_price = MAX(close_price) OVER (
                PARTITION BY ticker
                ORDER BY trade_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) THEN trade_date
        END AS peak_trade_date_candidate
    FROM {{ ref('daily_stock_summary') }}
),
peaks AS (
    SELECT
        ticker,
        trade_date,
        close_price,
        last_updated_at,
        rolling_peak_close,
        MAX(
            peak_trade_date_candidate
        ) OVER (
            PARTITION BY ticker
            ORDER BY trade_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS latest_peak_date
    FROM ordered
),
drawdowns AS (
    SELECT
        ticker,
        trade_date,
        close_price,
        rolling_peak_close,
        ROUND(
            CASE
                WHEN rolling_peak_close = 0 THEN 0
                ELSE ((close_price - rolling_peak_close) / rolling_peak_close) * 100
            END,
            2
        ) AS drawdown_pct,
        (trade_date - latest_peak_date) AS days_since_peak,
        last_updated_at
    FROM peaks
)
SELECT
    ticker,
    trade_date,
    close_price,
    rolling_peak_close,
    drawdown_pct,
    days_since_peak,
    CASE
        WHEN drawdown_pct <= -20 THEN 'deep_drawdown'
        WHEN drawdown_pct < 0 THEN 'underwater'
        ELSE 'recovered'
    END AS recovery_status,
    last_updated_at
FROM drawdowns
