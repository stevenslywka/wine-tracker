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


def _row_get(row, key):
    if row is None:
        return None
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return None


def _row_keys(row):
    if row is None:
        return set()
    if isinstance(row, dict):
        return set(row.keys())
    if hasattr(row, "keys"):
        return set(row.keys())
    return set()


def _lot_status_for_inventory(status):
    return status if status in ("in_collection", "not_shipped") else None


def _fetch_wine_for_lot_defaults(cur, wine_id):
    p = get_placeholder()
    cur.execute(
        f"""SELECT quantity, status, storage_location, retailer, order_date, unit_price
            FROM wines WHERE id = {p}""",
        (wine_id,)
    )
    return cur.fetchone()


def sync_wine_summary(conn, wine_id):
    """Refresh cached wine inventory fields from current lots in the same transaction."""
    p = get_placeholder()
    cur = conn.cursor()

    cur.execute(
        f"""SELECT storage_location, SUM(quantity) AS qty
            FROM wine_inventory_lots
            WHERE wine_id = {p}
              AND status = 'in_collection'
              AND quantity > 0
            GROUP BY storage_location
            ORDER BY qty DESC, storage_location ASC""",
        (wine_id,)
    )
    location_rows = cur.fetchall()
    available_qty = sum((_row_get(r, "qty") or 0) for r in location_rows)
    primary_location = None
    location_summary = None
    if location_rows:
        primary_location = _row_get(location_rows[0], "storage_location")
        parts = []
        for row in location_rows:
            loc = _row_get(row, "storage_location") or "Unassigned"
            parts.append(f"{loc} {_row_get(row, 'qty') or 0}")
        location_summary = " · ".join(parts)

    cur.execute(
        f"""SELECT COUNT(*) AS cnt
            FROM wine_inventory_lots
            WHERE wine_id = {p}
              AND status = 'not_shipped'
              AND quantity > 0""",
        (wine_id,)
    )
    incoming_count = _row_get(cur.fetchone(), "cnt") or 0
    summary_status = "in_collection" if available_qty > 0 else ("not_shipped" if incoming_count > 0 else "drank")

    cur.execute(
        f"""SELECT retailer, order_date, unit_price
            FROM wine_inventory_lots
            WHERE wine_id = {p}
              AND status = 'in_collection'
              AND quantity > 0
            ORDER BY order_date DESC, created_at DESC, id DESC""",
        (wine_id,)
    )
    latest = cur.fetchone()
    retailer = _row_get(latest, "retailer")
    order_date = _row_get(latest, "order_date")
    unit_price = _row_get(latest, "unit_price")
    if latest is None:
        cur.execute(
            f"""SELECT retailer, order_date, unit_price
                FROM wine_inventory_lots
                WHERE wine_id = {p}
                  AND status = 'not_shipped'
                  AND quantity > 0
                ORDER BY order_date DESC, created_at DESC, id DESC""",
            (wine_id,)
        )
        latest = cur.fetchone()
        retailer = _row_get(latest, "retailer")
        order_date = _row_get(latest, "order_date")
        unit_price = _row_get(latest, "unit_price")
    if latest is None:
        cur.execute(
            f"""SELECT retailer, order_date, unit_price
                FROM wines
                WHERE id = {p}""",
            (wine_id,)
        )
        current_wine = cur.fetchone()
        retailer = _row_get(current_wine, "retailer")
        order_date = _row_get(current_wine, "order_date")
        unit_price = _row_get(current_wine, "unit_price")
    cur.execute(
        f"""SELECT SUM(quantity * unit_price) AS total
            FROM wine_inventory_lots
            WHERE wine_id = {p}
              AND status = 'in_collection'
              AND quantity > 0
              AND unit_price IS NOT NULL""",
        (wine_id,)
    )
    total_row = cur.fetchone()
    total_value = _row_get(total_row, "total")
    total_price = round(float(total_value), 2) if total_value is not None else None

    cur.execute(
        f"""UPDATE wines
            SET quantity = {p},
                status = {p},
                storage_location = {p},
                location_summary = {p},
                retailer = {p},
                order_date = {p},
                unit_price = {p},
                total_price = {p}
            WHERE id = {p}""",
        (available_qty, summary_status, primary_location, location_summary,
         retailer, order_date, unit_price, total_price, wine_id)
    )


def upsert_inventory_lot(conn, wine_id, quantity, status="in_collection",
                         storage_location=None, retailer=None, order_date=None,
                         unit_price=None, notes=None):
    """Create or consolidate a current inventory lot, then sync the parent wine."""
    lot_status = _lot_status_for_inventory(status)
    if not lot_status or not quantity or int(quantity) <= 0:
        sync_wine_summary(conn, wine_id)
        return None

    quantity = int(quantity)
    p = get_placeholder()
    cur = conn.cursor()
    cur.execute(
        f"""SELECT id, quantity
            FROM wine_inventory_lots
            WHERE wine_id = {p}
              AND status = {p}
              AND COALESCE(storage_location, '') = COALESCE({p}, '')
              AND COALESCE(retailer, '') = COALESCE({p}, '')
              AND COALESCE(order_date, '') = COALESCE({p}, '')
            ORDER BY id
            LIMIT 1""",
        (wine_id, lot_status, storage_location, retailer, order_date)
    )
    existing = cur.fetchone()
    if existing:
        lot_id = _row_get(existing, "id")
        cur.execute(
            f"""UPDATE wine_inventory_lots
                SET quantity = quantity + {p},
                    unit_price = {p},
                    notes = COALESCE({p}, notes),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = {p}""",
            (quantity, unit_price, notes, lot_id)
        )
    else:
        if is_postgres():
            cur.execute(
                f"""INSERT INTO wine_inventory_lots
                    (wine_id, quantity, status, storage_location, retailer, order_date, unit_price, notes)
                    VALUES ({p},{p},{p},{p},{p},{p},{p},{p})
                    RETURNING id""",
                (wine_id, quantity, lot_status, storage_location, retailer, order_date, unit_price, notes)
            )
            row = cur.fetchone()
            lot_id = _row_get(row, "id")
        else:
            cur.execute(
                f"""INSERT INTO wine_inventory_lots
                    (wine_id, quantity, status, storage_location, retailer, order_date, unit_price, notes)
                    VALUES ({p},{p},{p},{p},{p},{p},{p},{p})""",
                (wine_id, quantity, lot_status, storage_location, retailer, order_date, unit_price, notes)
            )
            lot_id = cur.lastrowid

    sync_wine_summary(conn, wine_id)
    return lot_id


def replace_wine_inventory_lot(conn, wine_id, quantity=None, status=None,
                               storage_location=None, retailer=None,
                               order_date=None, unit_price=None):
    """Compatibility helper for old whole-wine inventory edits."""
    p = get_placeholder()
    cur = conn.cursor()
    defaults = _fetch_wine_for_lot_defaults(cur, wine_id)
    if quantity is None:
        quantity = _row_get(defaults, "quantity") or 0
    if status is None:
        status = _row_get(defaults, "status") or "in_collection"
    if storage_location is None:
        storage_location = _row_get(defaults, "storage_location")
    if retailer is None:
        retailer = _row_get(defaults, "retailer")
    if order_date is None:
        order_date = _row_get(defaults, "order_date")
    if unit_price is None:
        unit_price = _row_get(defaults, "unit_price")

    cur.execute(f"DELETE FROM wine_inventory_lots WHERE wine_id = {p}", (wine_id,))
    upsert_inventory_lot(conn, wine_id, quantity, status, storage_location, retailer, order_date, unit_price)


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

    # --- Rename 'location' → 'origin', add 'storage_location' ---
    if pg:
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name='wines' AND column_name='origin'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE wines RENAME COLUMN location TO origin")
        cur.execute("ALTER TABLE wines ADD COLUMN IF NOT EXISTS storage_location TEXT")
    else:
        cur.execute("PRAGMA table_info(wines)")
        cols = {r['name'] for r in cur.fetchall()}
        if 'origin' not in cols and 'location' in cols:
            cur.execute("ALTER TABLE wines RENAME COLUMN location TO origin")
        if 'storage_location' not in cols:
            cur.execute("ALTER TABLE wines ADD COLUMN storage_location TEXT")

    # --- Add cached location summary for lot-aware inventory ---
    if pg:
        cur.execute("ALTER TABLE wines ADD COLUMN IF NOT EXISTS location_summary TEXT")
    else:
        cur.execute("PRAGMA table_info(wines)")
        cols = {r['name'] for r in cur.fetchall()}
        if 'location_summary' not in cols:
            cur.execute("ALTER TABLE wines ADD COLUMN location_summary TEXT")

    # --- Create user_locations table ---
    if pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_locations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)

    # --- Create lot-aware inventory tables ---
    if pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wine_inventory_lots (
                id SERIAL PRIMARY KEY,
                wine_id INTEGER NOT NULL REFERENCES wines(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'in_collection',
                storage_location TEXT,
                retailer TEXT,
                order_date TEXT,
                unit_price REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wine_drink_history (
                id SERIAL PRIMARY KEY,
                wine_id INTEGER NOT NULL REFERENCES wines(id) ON DELETE CASCADE,
                lot_id INTEGER REFERENCES wine_inventory_lots(id) ON DELETE SET NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                drank_date TEXT,
                rating REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wine_inventory_lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wine_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'in_collection',
                storage_location TEXT,
                retailer TEXT,
                order_date TEXT,
                unit_price REAL,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wine_drink_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wine_id INTEGER NOT NULL,
                lot_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 1,
                drank_date TEXT,
                rating REAL,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

    # --- Migrate old location-based statuses → in_collection + storage_location ---
    p2 = "%s" if pg else "?"
    for old_status, new_loc in [('cellar', 'Cellar'), ('apt', 'Apt'), ('house', 'House')]:
        cur.execute(
            f"UPDATE wines SET status = {p2}, storage_location = {p2} WHERE status = {p2} AND storage_location IS NULL",
            ('in_collection', new_loc, old_status)
        )

    # --- Seed default locations for any user with no locations yet ---
    cur.execute("SELECT id FROM users")
    all_users = cur.fetchall()
    for u in all_users:
        uid2 = u['id'] if isinstance(u, dict) else u[0]
        cur.execute(f"SELECT COUNT(*) as cnt FROM user_locations WHERE user_id = {p2}", (uid2,))
        row = cur.fetchone()
        cnt = row['cnt'] if isinstance(row, dict) else row[0]
        if cnt == 0:
            for i, loc_name in enumerate(['Cellar', 'Apt', 'House']):
                cur.execute(
                    f"INSERT INTO user_locations (user_id, name, sort_order) VALUES ({p2},{p2},{p2})",
                    (uid2, loc_name, i)
                )

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

    # --- Seed initial inventory lots from existing wine rows ---
    cur.execute(f"""
        INSERT INTO wine_inventory_lots
            (wine_id, quantity, status, storage_location, retailer, order_date, unit_price)
        SELECT w.id,
               COALESCE(w.quantity, 0),
               w.status,
               w.storage_location,
               w.retailer,
               w.order_date,
               w.unit_price
        FROM wines w
        WHERE w.status IN ('in_collection', 'not_shipped')
          AND COALESCE(w.quantity, 0) > 0
          AND NOT EXISTS (
              SELECT 1 FROM wine_inventory_lots l WHERE l.wine_id = w.id
          )
    """)

    # --- Refresh cached wine summaries from lots ---
    cur.execute("SELECT id FROM wines")
    all_wines = cur.fetchall()
    for w in all_wines:
        wine_id = w["id"] if isinstance(w, dict) else w[0]
        sync_wine_summary(conn, wine_id)

    conn.commit()
    conn.close()
