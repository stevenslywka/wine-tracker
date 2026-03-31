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

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_FILE = "wines.db"

# SQL placeholder character — sqlite3 uses ?, psycopg2 uses %s
placeholder = "%s" if DATABASE_URL else "?"


def get_connection():
    """Return an open DB connection (psycopg2 or sqlite3 depending on env)."""
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        # Railway sometimes provides postgres:// but psycopg2 needs postgresql://
        url = DATABASE_URL
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
    return DATABASE_URL is not None
