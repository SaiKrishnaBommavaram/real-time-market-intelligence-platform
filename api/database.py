import asyncio
from contextlib import asynccontextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from api.config import settings


_db_pool = None


def get_db_pool():
    global _db_pool

    if _db_pool is None:
        _db_pool = ThreadedConnectionPool(
            minconn=settings.db_pool_min_size,
            maxconn=settings.db_pool_max_size,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            cursor_factory=RealDictCursor,
        )

    return _db_pool


async def get_db_connection():
    return await asyncio.to_thread(get_db_pool().getconn)


async def release_db_connection(connection, *, close: bool = False):
    await asyncio.to_thread(get_db_pool().putconn, connection, close)


async def close_db_pool():
    global _db_pool

    if _db_pool is not None:
        pool = _db_pool
        _db_pool = None
        await asyncio.to_thread(pool.closeall)


@asynccontextmanager
async def get_db_cursor(*, commit: bool = False):
    connection = await get_db_connection()
    cursor = connection.cursor()

    try:
        yield connection, cursor
        if commit:
            await asyncio.to_thread(connection.commit)
    except Exception:
        if commit:
            await asyncio.to_thread(connection.rollback)
        raise
    finally:
        cursor.close()
        await release_db_connection(connection)
