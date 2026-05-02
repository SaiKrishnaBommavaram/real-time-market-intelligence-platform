from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.database import get_db_connection


app = FastAPI(
    title="Real-Time Market Intelligence API",
    description="API for serving transformed market analytics from PostgreSQL/dbt models.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Real-Time Market Intelligence API is running",
        "available_endpoints": [
            "/health",
            "/market/summary",
            "/stocks/{ticker}/summary",
        ],
    }


@app.get("/health")
def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 AS status;")
        result = cur.fetchone()
        cur.close()
        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
            "query_result": result,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/market/summary")
def get_market_summary():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ticker,
            trade_date,
            event_count,
            avg_price,
            min_price,
            max_price,
            total_volume,
            last_updated_at
        FROM analytics.daily_stock_summary
        ORDER BY trade_date DESC, ticker
        LIMIT 100;
        """
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {
        "count": len(rows),
        "data": rows,
    }


@app.get("/stocks/{ticker}/summary")
def get_stock_summary(ticker: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ticker,
            trade_date,
            event_count,
            avg_price,
            min_price,
            max_price,
            total_volume,
            last_updated_at
        FROM analytics.daily_stock_summary
        WHERE ticker = %s
        ORDER BY trade_date DESC;
        """,
        (ticker.upper(),),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No summary found for ticker: {ticker.upper()}",
        )

    return {
        "ticker": ticker.upper(),
        "count": len(rows),
        "data": rows,
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)