import mysql.connector
from mysql.connector import pooling
from flask import g

_pool = None


def init_pool(app):
    """Create a connection pool once, at app startup."""
    global _pool

    _pool = pooling.MySQLConnectionPool(
        pool_name="lostfound_pool",
        pool_size=5,
        host=app.config["MYSQL_HOST"],
        port=app.config["MYSQL_PORT"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"],
        autocommit=False,
    )


def get_db():
    """Return a pooled connection for the current request context."""
    if "db_conn" not in g:
        if _pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call init_pool(app) first."
            )
        g.db_conn = _pool.get_connection()

    return g.db_conn


def close_db(e=None):
    conn = g.pop("db_conn", None)

    if conn is not None and conn.is_connected():
        conn.close()


def init_app(app):
    init_pool(app)
    app.teardown_appcontext(close_db)


def query(sql, params=None, fetchone=False, commit=False):
    """Small helper to run a query and get dict rows back."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(sql, params or ())

        if commit:
            conn.commit()
            last_id = cursor.lastrowid
            cursor.close()
            return last_id

        result = cursor.fetchone() if fetchone else cursor.fetchall()
        cursor.close()
        return result

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"MySQL Error: {err}")
        raise