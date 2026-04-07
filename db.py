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


def migrate():
    """Add any missing columns/tables. Safe to run on every startup."""
    conn = get_connection()
    cur = conn.cursor()
    pg = os.environ.get("DATABASE_URL") is not None

    # --- Create users table ---
    if pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

    # --- Add new columns to wines ---
    new_columns = [
        ("drinking_window", "TEXT"),
        ("drinking_window_source", "TEXT"),
        ("user_id", "INTEGER"),
    ]
    for col, col_type in new_columns:
        try:
            if pg:
                cur.execute(f"ALTER TABLE wines ADD COLUMN IF NOT EXISTS {col} {col_type}")
            else:
                cur.execute(f"ALTER TABLE wines ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # --- Seed steven's account if no users exist ---
    from werkzeug.security import generate_password_hash
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    row = cur.fetchone()
    cnt = row["cnt"] if isinstance(row, dict) else row[0]
    if cnt == 0:
        pw_hash = generate_password_hash("changeme123")
        if pg:
            cur.execute("INSERT INTO users (username, display_name, password_hash, is_admin) VALUES (%s, %s, %s, %s)",
                        ("steven", "Steven", pw_hash, True))
        else:
            cur.execute("INSERT INTO users (username, display_name, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                        ("steven", "Steven", pw_hash, 1))

    # --- Assign all unowned wines to steven ---
    if pg:
        cur.execute("UPDATE wines SET user_id = (SELECT id FROM users WHERE username = 'steven') WHERE user_id IS NULL")
    else:
        cur.execute("UPDATE wines SET user_id = (SELECT id FROM users WHERE username = 'steven') WHERE user_id IS NULL")

    # --- Mark steven's existing drinking windows as manually curated ---
    cur.execute("""
        UPDATE wines SET drinking_window_source = 'manual'
        WHERE drinking_window IS NOT NULL
        AND drinking_window != ''
        AND drinking_window_source IS NULL
        AND user_id = (SELECT id FROM users WHERE username = 'steven')
    """)

    # --- Normalize "Now-XXXX" drinking windows ---
    from datetime import date as _date
    current_year = str(_date.today().year)
    if pg:
        cur.execute("UPDATE wines SET drinking_window = REPLACE(drinking_window, 'Now', %s) WHERE drinking_window LIKE 'Now-%%'", (current_year,))
    else:
        cur.execute("UPDATE wines SET drinking_window = REPLACE(drinking_window, 'Now', ?) WHERE drinking_window LIKE 'Now-%'", (current_year,))

    conn.commit()
    conn.close()
