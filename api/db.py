import oracledb

from api.config import settings

_pool: oracledb.ConnectionPool | None = None


def _get_pool() -> oracledb.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=settings.oracle_user,
            password=settings.oracle_password,
            dsn=settings.oracle_dsn,
            config_dir=settings.oracle_wallet_dir,
            wallet_location=settings.oracle_wallet_dir,
            wallet_password=settings.oracle_password,
            min=1,
            max=4,
            increment=1,
        )
    return _pool


def get_connection():
    pool = _get_pool()
    conn = pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)
