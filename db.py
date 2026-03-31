"""
Database connection helper.
Returns a psycopg2 connection if DATABASE_URL env var is set (Railway/production),
otherwise returns a sqlite3 connection for local development.

Usage:
    from db import get_connection, placeholder

    conn = get_connection()
    ph = placeholder  # '?' for sqlite3, '%s' for psycopg2
    conn.execute(f"SELECT * FROM wines WHERE id = {ph}", (wine_id,))
    conn.commit()
    conn.close()
"""

import os
import sqlite3

DB_FILE = "wines.db"


def get_connection():
    """Return an open DB connection (psycopg2 or sqlite3 depending on env)."""
    url = os.environ.get("DATABASE_URL")
    if url:
        import psycopg2
        import psycopg2.extras
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn


def is_postgres():
    return os.environ.get("DATABASE_URL") is not None


# Evaluated fresh each call so env vars are always current
def get_placeholder():
    return "%s" if is_postgres() else "?"


# Keep 'placeholder' as a callable alias for backwards compat
placeholder = get_placeholder
