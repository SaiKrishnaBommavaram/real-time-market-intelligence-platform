import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="market_data",
        user="postgres",
        password="postgres",
        cursor_factory=RealDictCursor,
    )