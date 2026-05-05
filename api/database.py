import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


load_dotenv()


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("MARKET_DB_HOST", "localhost"),
        port=int(os.getenv("MARKET_DB_PORT", "55432")),
        database=os.getenv("MARKET_DB_NAME", "market_data"),
        user=os.getenv("MARKET_DB_USER", "postgres"),
        password=os.getenv("MARKET_DB_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor,
    )
