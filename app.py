"""
Wine Tracker web app. Run with: python app.py
Then open http://localhost:5000 in your browser.
"""

import os
from datetime import date
from dotenv import load_dotenv
load_dotenv()
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   jsonify, session, flash)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

# Run DB migrations on startup
import db as _db_module
_db_module.migrate()

WINE_TYPES = ("Red", "White", "Rose", "Sparkling", "Dessert", "Fortified", "Orange")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            return ("Forbidden", 403)
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    import db as db_module
    return db_module.get_connection()


def ph():
    import db as db_module
    return db_module.get_placeholder()


def is_postgres():
    return _db_module.is_postgres()


def lastrowid(conn, cursor):
    import db as db_module
    if db_module.is_postgres():
        row = cursor.fetchone()
        if row:
            return row["id"]
        return None
    else:
        return cursor.lastrowid


def get_user_by_username(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE username = {ph()}", (username,))
    user = cur.fetchone()
    conn.close()
    return user


def owns_wine(wine_id):
    """Return True if the logged-in user owns wine_id."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT user_id FROM wines WHERE id = {ph()}", (wine_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return row["user_id"] == session.get("user_id")


# ---------------------------------------------------------------------------
# Wine-type inference
# ---------------------------------------------------------------------------

def infer_wine_type(varietal):
    if not varietal:
        return None
    v = varietal.lower()
    if any(x in v for x in ['rosé','rosato','rosado','blush','rosè']):
        return 'Rose'
    if any(x in v for x in ['sparkling','champagne','prosecco','cava','crémant','cremant','sekt','pétillant','petillant','franciacorta','lambrusco']):
        return 'Sparkling'
    if any(x in v for x in ['port','sherry','madeira','marsala','vermouth']):
        return 'Fortified'
    if any(x in v for x in ['sauternes','ice wine','icewine','late harvest','trockenbeerenauslese','beerenauslese','eiswein','tokaj','vin santo']):
        return 'Dessert'
    if any(x in v for x in ['orange wine','skin contact','skin-contact']):
        return 'Orange'
    if any(x in v for x in ['blanc','white wine','chardonnay','riesling','pinot grigio','pinot gris','sauvignon blanc','gewurz','viognier','moscato','grüner','gruner','semillon','trebbiano','vermentino','verdejo','albarino','albariño','torrontes','torrontés','chenin','roussanne','marsanne','grenache blanc','picpoul','assyrtiko','soave','gavi','arneis']):
        return 'White'
    if any(x in v for x in ['cabernet','merlot','pinot noir','syrah','shiraz','zinfandel','malbec','grenache','sangiovese','nebbiolo','tempranillo','barbera','barolo','barbaresco','brunello','amarone','valpolicella','ripasso','aglianico','petite sirah','mourvedre','petite verdot','carmenere','carmén','zweigelt','blaufränkisch','red blend','red wine','roero','lessona','bramaterra','morellino','rosso','rouge','rioja','bourgogne','mercurey','saint-émilion','saint-emilion','saint-chinian','saint-georges','sancerre rouge','vino nobile','premier cru']):
        return 'Red'
    return None


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if username and password:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM users WHERE username = {ph()}", (username,))
            user = cur.fetchone()
            conn.close()
            if user:
                from werkzeug.security import check_password_hash
                if check_password_hash(user["password_hash"], password):
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    session["display_name"] = user["display_name"]
                    session["is_admin"] = bool(user["is_admin"])
                    next_url = request.args.get("next") or url_for("home")
                    return redirect(next_url)
        error = "Incorrect username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"SELECT COUNT(*) as cnt, SUM(CASE WHEN status='cellar' THEN quantity ELSE 0 END) as in_cellar FROM wines WHERE user_id = {ph()}",
        (session["user_id"],)
    )
    row = cur.fetchone()
    conn.close()
    my_stats = {"total": row["cnt"] or 0, "in_cellar": row["in_cellar"] or 0}
    return render_template("home.html", my_stats=my_stats)


@app.route("/friends")
@login_required
def friends():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id != {ph()} ORDER BY username", (session["user_id"],))
    users = cur.fetchall()

    user_stats = {}
    for u in users:
        cur.execute(
            f"SELECT COUNT(*) as cnt, SUM(CASE WHEN status='cellar' THEN quantity ELSE 0 END) as in_cellar FROM wines WHERE user_id = {ph()}",
            (u["id"],)
        )
        row = cur.fetchone()
        user_stats[u["id"]] = {"total": row["cnt"] or 0, "in_cellar": row["in_cellar"] or 0}
    conn.close()
    return render_template("friends.html", users=users, user_stats=user_stats)


# ---------------------------------------------------------------------------
# Admin page
# ---------------------------------------------------------------------------

@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    error = None
    success = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create_user":
            username = request.form.get("username", "").strip().lower()
            display_name = request.form.get("display_name", "").strip()
            password = request.form.get("password", "").strip()
            is_admin_val = 1 if request.form.get("is_admin") else 0
            if not username or not display_name or not password:
                error = "All fields are required."
            else:
                from werkzeug.security import generate_password_hash
                pw_hash = generate_password_hash(password)
                try:
                    conn = get_db()
                    cur = conn.cursor()
                    p = ph()
                    if is_postgres():
                        cur.execute(
                            f"INSERT INTO users (username, display_name, password_hash, is_admin) VALUES ({p},{p},{p},{p})",
                            (username, display_name, pw_hash, bool(is_admin_val))
                        )
                    else:
                        cur.execute(
                            f"INSERT INTO users (username, display_name, password_hash, is_admin) VALUES ({p},{p},{p},{p})",
                            (username, display_name, pw_hash, is_admin_val)
                        )
                    conn.commit()
                    conn.close()
                    success = f"Account created for {display_name} (@{username})."
                except Exception as e:
                    error = f"Could not create user: {e}"
        elif action == "delete_user":
            uid = request.form.get("user_id")
            if uid and int(uid) != session["user_id"]:
                conn = get_db()
                cur = conn.cursor()
                cur.execute(f"DELETE FROM users WHERE id = {ph()}", (int(uid),))
                conn.commit()
                conn.close()
                success = "User deleted."
            else:
                error = "Cannot delete your own account."
        elif action == "reset_password":
            uid = request.form.get("user_id")
            new_pw = request.form.get("new_password", "").strip()
            if uid and new_pw:
                from werkzeug.security import generate_password_hash
                pw_hash = generate_password_hash(new_pw)
                conn = get_db()
                cur = conn.cursor()
                cur.execute(f"UPDATE users SET password_hash = {ph()} WHERE id = {ph()}", (pw_hash, int(uid)))
                conn.commit()
                conn.close()
                success = "Password reset."

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY username")
    users = cur.fetchall()
    conn.close()
    return render_template("admin.html", users=users, error=error, success=success)


# ---------------------------------------------------------------------------
# Cellar (collection) view — the main page per user
# ---------------------------------------------------------------------------

@app.route("/cellar/<username>")
@login_required
def cellar(username):
    cellar_user = get_user_by_username(username)
    if not cellar_user:
        return ("User not found", 404)

    can_edit = (cellar_user["id"] == session["user_id"])
    # access_level kept for template compatibility
    access_level = "edit" if can_edit else "view"

    conn = get_db()
    p = ph()
    search = request.args.get("q", "")
    status_filter = request.args.get("status", "")
    varietal_filter = request.args.get("varietal", "")
    region_filter = request.args.get("region", "")
    origin_filter = request.args.get("origin", "")
    storage_filter = request.args.get("storage_location", "")
    vintage_min = request.args.get("vintage_min", "")
    vintage_max = request.args.get("vintage_max", "")
    price_min = request.args.get("price_min", "")
    price_max = request.args.get("price_max", "")
    sort = request.args.get("sort", "order_date")
    order = request.args.get("order", "desc")

    allowed_sorts = {"order_date", "wine_name", "vintage", "unit_price", "retail_price",
                     "quantity", "color_code", "region", "origin", "storage_location", "varietal",
                     "my_rating", "wine_type", "size_ml", "drinking_window"}
    if sort not in allowed_sorts:
        sort = "order_date"
    if order not in {"asc", "desc"}:
        order = "desc"

    base_query = f"SELECT * FROM wines WHERE user_id = {p}"
    base_params = [cellar_user["id"]]

    if status_filter:
        base_query += f" AND status = {p}"
        base_params.append(status_filter)
    if varietal_filter:
        base_query += f" AND varietal = {p}"
        base_params.append(varietal_filter)
    if region_filter:
        base_query += f" AND region = {p}"
        base_params.append(region_filter)
    if origin_filter:
        base_query += f" AND origin = {p}"
        base_params.append(origin_filter)
    if storage_filter:
        base_query += f" AND storage_location = {p}"
        base_params.append(storage_filter)
    if vintage_min:
        base_query += f" AND vintage >= {p}"
        base_params.append(int(vintage_min))
    if vintage_max:
        base_query += f" AND vintage <= {p}"
        base_params.append(int(vintage_max))
    if price_min:
        base_query += f" AND unit_price >= {p}"
        base_params.append(float(price_min))
    if price_max:
        base_query += f" AND unit_price <= {p}"
        base_params.append(float(price_max))
    color_filter = request.args.get("color_code", "")
    if color_filter:
        base_query += f" AND color_code = {p}"
        base_params.append(color_filter)
    retailer_filter = request.args.get("retailer", "")
    if retailer_filter:
        base_query += f" AND retailer = {p}"
        base_params.append(retailer_filter)
    type_filter = request.args.get("wine_type", "")
    if type_filter:
        base_query += f" AND wine_type = {p}"
        base_params.append(type_filter)
    size_filter = request.args.get("size_ml", "")
    if size_filter:
        try:
            base_query += f" AND size_ml = {p}"
            base_params.append(int(size_filter))
        except ValueError:
            pass

    # Apply search (exact LIKE first)
    if search:
        query  = base_query + f" AND (wine_name LIKE {p} OR varietal LIKE {p} OR region LIKE {p} OR retailer LIKE {p} OR origin LIKE {p} OR wine_type LIKE {p} OR notes LIKE {p})"
        params = base_params + [f"%{search}%"] * 7
    else:
        query, params = base_query, base_params

    if sort == "drinking_window":
        # Sort by status: Red=1, Orange=2, Green=3, Blue=4, Grey=5
        # Extracts start/end year from "YYYY-YYYY" text field
        cur_year = "EXTRACT(YEAR FROM NOW())::INTEGER" if is_postgres() else "CAST(STRFTIME('%Y', 'now') AS INTEGER)"
        start_yr = "CAST(SUBSTRING(drinking_window FROM 1 FOR 4) AS INTEGER)" if is_postgres() else "CAST(SUBSTR(drinking_window, 1, 4) AS INTEGER)"
        end_yr   = "CAST(RIGHT(drinking_window, 4) AS INTEGER)" if is_postgres() else "CAST(SUBSTR(drinking_window, -4) AS INTEGER)"
        dw_sort = (
            f"CASE "
            f"WHEN status = 'drank' OR drinking_window IS NULL OR drinking_window = '' THEN 5 "
            f"WHEN {cur_year} > {end_yr} THEN 1 "
            f"WHEN {cur_year} > ({start_yr} + {end_yr}) / 2 THEN 2 "
            f"WHEN {cur_year} >= {start_yr} THEN 3 "
            f"ELSE 4 "
            f"END"
        )
        query += f" ORDER BY {dw_sort} {'ASC' if order == 'asc' else 'DESC'}"
    else:
        query += f" ORDER BY {sort} {order}"

    cur = conn.cursor()
    cur.execute(query, params)
    wines = cur.fetchall()

    # Fuzzy fallback: if search ≥ 4 chars returned nothing, score against all filtered wines
    fuzzy_used = False
    if search and len(search) >= 4 and len(wines) == 0:
        from difflib import SequenceMatcher
        cur.execute(base_query + f" ORDER BY {sort} {order}", base_params)
        candidates = cur.fetchall()
        term = search.lower()

        def _score(wine):
            name = (wine["wine_name"] or "").lower()
            scores = [SequenceMatcher(None, term, name).ratio()]
            for word in name.split():
                if len(word) >= 3:
                    scores.append(SequenceMatcher(None, term, word).ratio())
            for field in ("varietal", "region", "retailer", "origin", "wine_type"):
                val = (wine[field] or "").lower()
                if val:
                    scores.append(SequenceMatcher(None, term, val).ratio())
            return max(scores)

        scored = sorted(((s, w) for w in candidates if (s := _score(w)) >= 0.7), reverse=True)
        wines = [w for _, w in scored]
        fuzzy_used = bool(wines)

    cur.execute(f"""
        SELECT
            SUM(quantity) as total_bottles,
            COUNT(DISTINCT wine_name) as unique_wines,
            SUM(total_price) as total_spent
        FROM wines WHERE user_id = {p}
    """, (cellar_user["id"],))
    stats = cur.fetchone()

    cur.execute(f"SELECT DISTINCT varietal FROM wines WHERE user_id = {p} AND varietal IS NOT NULL ORDER BY varietal", (cellar_user["id"],))
    varietals = [r["varietal"] for r in cur.fetchall()]
    cur.execute(f"SELECT DISTINCT region FROM wines WHERE user_id = {p} AND region IS NOT NULL ORDER BY region", (cellar_user["id"],))
    regions = [r["region"] for r in cur.fetchall()]
    cur.execute(f"SELECT DISTINCT origin FROM wines WHERE user_id = {p} AND origin IS NOT NULL ORDER BY origin", (cellar_user["id"],))
    origins = [r["origin"] for r in cur.fetchall()]
    cur.execute(f"SELECT name FROM user_locations WHERE user_id = {p} ORDER BY sort_order", (cellar_user["id"],))
    user_locations = [r["name"] for r in cur.fetchall()]
    cur.execute(f"""
        SELECT storage_location, SUM(quantity) as cnt
        FROM wines WHERE user_id = {p} AND status = 'in_collection' AND storage_location IS NOT NULL
        GROUP BY storage_location ORDER BY storage_location
    """, (cellar_user["id"],))
    location_counts = {r["storage_location"]: r["cnt"] for r in cur.fetchall()}
    cur.execute(f"SELECT DISTINCT vintage FROM wines WHERE user_id = {p} AND vintage IS NOT NULL ORDER BY vintage DESC", (cellar_user["id"],))
    vintages = [r["vintage"] for r in cur.fetchall()]
    cur.execute(f"SELECT DISTINCT size_ml FROM wines WHERE user_id = {p} AND size_ml IS NOT NULL ORDER BY size_ml", (cellar_user["id"],))
    sizes = [r["size_ml"] for r in cur.fetchall()]
    cur.execute(f"SELECT DISTINCT retailer FROM wines WHERE user_id = {p} AND retailer IS NOT NULL ORDER BY retailer", (cellar_user["id"],))
    retailers = [r["retailer"] for r in cur.fetchall()]

    conn.close()
    return render_template("index.html", wines=wines, stats=stats,
                           search=search, status_filter=status_filter,
                           varietal_filter=varietal_filter, region_filter=region_filter,
                           origin_filter=origin_filter, storage_filter=storage_filter,
                           color_filter=color_filter,
                           type_filter=type_filter, size_filter=size_filter, retailer_filter=retailer_filter,
                           retailers=retailers,
                           vintage_min=vintage_min, vintage_max=vintage_max,
                           price_min=price_min, price_max=price_max,
                           sort=sort, order=order,
                           varietals=varietals, regions=regions,
                           origins=origins, user_locations=user_locations,
                           location_counts=location_counts,
                           vintages=vintages, sizes=sizes,
                           access_level=access_level,
                           auth_enabled=True,
                           cellar_username=cellar_user["username"],
                           cellar_display_name=cellar_user["display_name"],
                           is_own_cellar=can_edit,
                           fuzzy_used=fuzzy_used)


# Keep /index redirect for backward compat
@app.route("/index")
@login_required
def index():
    return redirect(url_for("cellar", username=session["username"]))


@app.route("/wine/<int:wine_id>")
@login_required
def wine_detail(wine_id):
    conn = get_db()
    p = ph()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM wines WHERE id = {p}", (wine_id,))
    wine = cur.fetchone()
    conn.close()
    if not wine:
        return "Wine not found", 404
    can_edit = (wine["user_id"] == session["user_id"])
    return render_template("detail.html", wine=wine,
                           access_level="edit" if can_edit else "view",
                           auth_enabled=True)


@app.route("/wines/bulk-status", methods=["POST"])
@login_required
def bulk_update_status():
    ids = request.form.getlist("ids")
    new_status = request.form.get("status")
    if new_status not in ("in_collection", "not_shipped", "drank"):
        return ("", 400)
    storage_loc = request.form.get("storage_location", "").strip() or None
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    uid = session["user_id"]
    for id_ in ids:
        if new_status == "in_collection" and storage_loc:
            cur.execute(f"UPDATE wines SET status = {p}, storage_location = {p} WHERE id = {p} AND user_id = {p}", (new_status, storage_loc, id_, uid))
        elif new_status in ("not_shipped", "drank"):
            cur.execute(f"UPDATE wines SET status = {p}, storage_location = NULL WHERE id = {p} AND user_id = {p}", (new_status, id_, uid))
        else:
            cur.execute(f"UPDATE wines SET status = {p} WHERE id = {p} AND user_id = {p}", (new_status, id_, uid))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/status", methods=["POST"])
@login_required
def update_status(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    new_status = request.form.get("status")
    storage_loc = request.form.get("storage_location", "").strip() or None
    if new_status in ("in_collection", "not_shipped", "drank"):
        p = ph()
        conn = get_db()
        cur = conn.cursor()
        if new_status == "in_collection" and storage_loc:
            cur.execute(f"UPDATE wines SET status = {p}, storage_location = {p} WHERE id = {p}", (new_status, storage_loc, wine_id))
        elif new_status in ("not_shipped", "drank"):
            cur.execute(f"UPDATE wines SET status = {p}, storage_location = NULL WHERE id = {p}", (new_status, wine_id))
        else:
            cur.execute(f"UPDATE wines SET status = {p} WHERE id = {p}", (new_status, wine_id))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for("home"))


@app.route("/wine/<int:wine_id>/color", methods=["POST"])
@login_required
def update_color(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    color = request.form.get("color_code", "")
    if color in ("Red", "Blue", "Orange", "Yellow", "Green", ""):
        p = ph()
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE wines SET color_code = {p} WHERE id = {p}", (color or None, wine_id))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for("home"))


BOTTLE_SIZES = (187, 375, 750, 1000, 1500, 3000, 6000)


@app.route("/wine/<int:wine_id>/size", methods=["POST"])
@login_required
def update_size(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    raw = request.form.get("size_ml", "").strip()
    if raw == "":
        size = None
    else:
        try:
            size = int(raw)
            if size not in BOTTLE_SIZES:
                return ("", 400)
        except ValueError:
            return ("", 400)
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE wines SET size_ml = {p} WHERE id = {p}", (size, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/type", methods=["POST"])
@login_required
def update_type(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    wine_type = request.form.get("wine_type", "")
    if wine_type not in WINE_TYPES and wine_type != "":
        return ("", 400)
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE wines SET wine_type = {p} WHERE id = {p}", (wine_type or None, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/rating", methods=["POST"])
@login_required
def update_rating(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    raw = request.form.get("my_rating", "").strip()
    if raw == "":
        rating = None
    else:
        try:
            rating = round(float(raw), 1)
            if not (0.0 <= rating <= 5.0):
                return ("", 400)
        except ValueError:
            return ("", 400)
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE wines SET my_rating = {p} WHERE id = {p}", (rating, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/delete", methods=["POST"])
@login_required
def delete_wine(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM wines WHERE id = {p}", (wine_id,))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/retailer", methods=["POST"])
@login_required
def update_retailer(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    retailer = request.form.get("retailer", "").strip() or None
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE wines SET retailer = {p} WHERE id = {p}", (retailer, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/region", methods=["POST"])
@login_required
def update_region(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    value = request.form.get("region", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET region = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/origin", methods=["POST"])
@login_required
def update_origin(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    value = request.form.get("origin", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET origin = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/storage_location", methods=["POST"])
@login_required
def update_storage_location(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    value = request.form.get("storage_location", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET storage_location = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/varietal", methods=["POST"])
@login_required
def update_varietal(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    value = request.form.get("varietal", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET varietal = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/drinking_window", methods=["POST"])
@login_required
def update_drinking_window(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    value = request.form.get("drinking_window", "").strip() or None
    source = "manual" if value else None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET drinking_window = {p}, drinking_window_source = {p} WHERE id = {p}", (value, source, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/unit_price", methods=["POST"])
@login_required
def update_unit_price(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    raw = request.form.get("unit_price", "").strip()
    try:    unit_price = float(raw) if raw else None
    except ValueError: unit_price = None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"SELECT quantity FROM wines WHERE id = {p}", (wine_id,))
    row = cur.fetchone()
    quantity = row["quantity"] if row else 1
    total_price = round(unit_price * quantity, 2) if unit_price else None
    cur.execute(f"UPDATE wines SET unit_price = {p}, total_price = {p} WHERE id = {p}", (unit_price, total_price, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/retail_price", methods=["POST"])
@login_required
def update_retail_price(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    raw = request.form.get("retail_price", "").strip()
    try:    retail_price = float(raw) if raw else None
    except ValueError: retail_price = None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET retail_price = {p} WHERE id = {p}", (retail_price, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/notes", methods=["POST"])
@login_required
def update_notes(wine_id):
    if not owns_wine(wine_id):
        return ("", 403)
    notes = request.form.get("notes", "")
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE wines SET notes = {p} WHERE id = {p}", (notes, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/add", methods=["POST"])
@login_required
def add_wine():
    from enrich_wines import extract_varietal, extract_region, extract_location, infer_wine_type, infer_size
    from fetch_images import search_and_fetch_image

    wine_name = request.form.get("wine_name", "").strip()
    if not wine_name:
        return redirect(url_for("cellar", username=session["username"]))

    raw_vintage    = request.form.get("vintage", "").strip()
    raw_price      = request.form.get("unit_price", "").strip()
    raw_quantity   = request.form.get("quantity", "1").strip()
    notes          = request.form.get("notes", "").strip() or None
    retailer       = request.form.get("retailer", "").strip() or None
    raw_order_date = request.form.get("order_date", "").strip()
    raw_status       = request.form.get("status", "").strip()
    storage_location = request.form.get("storage_location", "").strip() or None
    if raw_status in ('not_shipped', 'drank'):
        status = raw_status
        storage_location = None
    else:
        status = 'in_collection'

    try:    vintage    = int(raw_vintage)   if raw_vintage   else None
    except ValueError: vintage = None
    try:    unit_price = float(raw_price)   if raw_price     else None
    except ValueError: unit_price = None
    try:    quantity   = max(1, int(raw_quantity)) if raw_quantity else 1
    except ValueError: quantity = 1

    order_date  = raw_order_date if raw_order_date else date.today().isoformat()
    total_price = round(unit_price * quantity, 2) if unit_price else None

    scan_varietal        = request.form.get("scan_varietal", "").strip() or None
    scan_region          = request.form.get("scan_region", "").strip() or None
    scan_wine_type       = request.form.get("scan_wine_type", "").strip() or None
    scan_location        = request.form.get("scan_location", "").strip() or None
    scan_drinking_window = request.form.get("scan_drinking_window", "").strip() or None
    color_code           = request.form.get("color_code", "").strip() or None

    varietal  = scan_varietal  or extract_varietal(wine_name)
    region    = scan_region    or extract_region(wine_name, varietal)
    origin    = scan_location  or extract_location(region)
    wine_type = scan_wine_type or infer_wine_type(varietal)
    size_ml   = infer_size(wine_name)
    drinking_window = scan_drinking_window or lookup_drinking_window(wine_name, vintage, varietal, region, retail_price=unit_price, size_ml=size_ml)
    dw_source = "manual" if scan_drinking_window else ("auto" if drinking_window else None)

    user_id = session["user_id"]
    p = ph()
    conn = get_db()
    cur = conn.cursor()

    if is_postgres():
        cur.execute(f"""
            INSERT INTO wines
                (wine_name, vintage, unit_price, total_price, quantity, notes,
                 varietal, region, origin, wine_type, size_ml,
                 retailer, order_date, status, storage_location, color_code, drinking_window, drinking_window_source, user_id)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
            RETURNING id
        """, (wine_name, vintage, unit_price, total_price, quantity, notes,
              varietal, region, origin, wine_type, size_ml, retailer, order_date, status, storage_location, color_code, drinking_window, dw_source, user_id))
        row = cur.fetchone()
        wine_id = row["id"] if row else None
    else:
        cur.execute(f"""
            INSERT INTO wines
                (wine_name, vintage, unit_price, total_price, quantity, notes,
                 varietal, region, origin, wine_type, size_ml,
                 retailer, order_date, status, storage_location, color_code, drinking_window, drinking_window_source, user_id)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
        """, (wine_name, vintage, unit_price, total_price, quantity, notes,
              varietal, region, origin, wine_type, size_ml, retailer, order_date, status, storage_location, color_code, drinking_window, dw_source, user_id))
        wine_id = cur.lastrowid

    conn.commit()
    conn.close()

    image_url = None
    uploaded = request.files.get("image")
    if uploaded and uploaded.filename:
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
        if cloud_name:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=os.environ.get("CLOUDINARY_API_KEY"),
                api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
            )
            result = cloudinary.uploader.upload(uploaded, folder="wine-tracker")
            image_url = result.get("secure_url")
        else:
            import uuid
            ext = os.path.splitext(uploaded.filename)[1] or ".jpg"
            filename = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(app.root_path, "static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            uploaded.save(os.path.join(upload_dir, filename))
            image_url = f"/static/uploads/{filename}"
    else:
        image_url = search_and_fetch_image(wine_name)

    if image_url and wine_id:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE wines SET image_url = {p} WHERE id = {p}", (image_url, wine_id))
        conn.commit()
        conn.close()

    return redirect(url_for("cellar", username=session["username"]))


_DRINKING_WINDOW_SYSTEM_PROMPT = (
    "You are a wine expert specializing in drinking windows — the range of years during which a wine "
    "is at its best. Your job is to estimate accurate drinking windows based on producer, vintage, "
    "varietal, region, and price.\n\n"
    "Key rules:\n"
    "- The drinking window represents when the wine is IDEALLY consumed. It may start in the past. "
    "Do NOT anchor it to the current year.\n"
    "- NEVER return a single-year window. Minimum span is 2 years.\n"
    "- NEVER return an inverted window where the start year is after the end year.\n"
    "- For rosé, rosato, and entry-level whites (retail price under $25 or varietal contains "
    "Rosé/Rosato/Moscato): window = vintage+1 to vintage+4 max.\n"
    "- For simple unoaked reds under $20 retail: window = vintage+1 to vintage+6 max.\n"
    "- For Barolo, Barbaresco, Brunello di Montalcino, Sagrantino: minimum 15-year total span from "
    "vintage, typically not ready until vintage+5 at earliest.\n"
    "- For classified Bordeaux (Pauillac, Saint-Émilion, Pessac-Léognan, Saint-Julien, Margaux, "
    "Pomerol): minimum 12-year total span from vintage.\n"
    "- For serious Napa Valley Cabernet Sauvignon with retail price $50+: 10-20 year total span from vintage.\n"
    "- For Premier Cru or Grand Cru Burgundy: 12-25 year span from vintage.\n"
    "- For wines from prestigious small producers in otherwise generic appellations (e.g. a top "
    "Côte-Rôtie producer making a Côtes du Rhône, a Burgundy domaine making Jura wine): apply the "
    "producer's typical aging profile, not the appellation baseline.\n"
    "- For 375mL half bottles: shorten the end of the window by 2-3 years versus a 750mL equivalent.\n"
    "- For 1500mL magnums: extend the end of the window by 3-5 years versus a 750mL equivalent.\n"
    "- If vintage is NV or unknown, base the window on the wine's typical style and producer.\n"
    "- If you are uncertain about a specific wine, use vintage + appellation + varietal to estimate "
    "conservatively. Do not guess wildly."
)


def validate_drinking_window(window_str, vintage):
    """Validate a drinking window string before writing to the database. Returns None if invalid."""
    import re
    if not window_str or not isinstance(window_str, str):
        return None
    window_str = window_str.strip()
    if not re.match(r'^\d{4}-\d{4}$', window_str):
        return None
    start, end = int(window_str[:4]), int(window_str[5:])
    if start >= end:
        return None
    if (end - start) < 2:
        return None
    if vintage and isinstance(vintage, int):
        if start > vintage + 30:
            return None
        if end > vintage + 50:
            return None
    return window_str


def lookup_drinking_window(wine_name, vintage, varietal, region, retail_price=None, size_ml=None):
    """Ask Claude for the drinking window of a single wine."""
    import anthropic, json as json_lib
    if len((wine_name or "").strip()) < 5:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    parts = [f"{wine_name} ({vintage or 'NV'})"]
    if varietal:
        parts.append(varietal)
    if region:
        parts.append(region)
    if retail_price:
        parts.append(f"retail: ${retail_price}")
    if size_ml and size_ml != 750:
        parts.append(f"size: {size_ml}mL")
    wine_desc = ", ".join(parts)
    prompt = (f"What is the estimated drinking window for this wine: {wine_desc}? "
              f"Return ONLY a JSON object like {{\"window\": \"2025-2032\"}}. No other text.")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=64,
        system=_DRINKING_WINDOW_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        window = json_lib.loads(raw.strip()).get("window") or None
        return validate_drinking_window(window, vintage)
    except Exception:
        return None


def lookup_receipt(image_data, media_type):
    """Ask Claude to extract wine info from a receipt image."""
    import anthropic, base64, json as json_lib
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": "Look at this receipt and extract all wine purchases. For each wine, return a JSON array of objects with these keys (use null if unknown):\n[{\"wine_name\": \"full name\", \"vintage\": 2019, \"unit_price\": 29.99, \"quantity\": 1, \"retailer\": \"store name\", \"order_date\": \"YYYY-MM-DD\"}]\nReturn only the JSON array, no other text."}
            ]
        }]
    )
    try:
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json_lib.loads(raw.strip())
    except Exception as e:
        print("receipt parse error:", e)
        return None


@app.route("/wine/scan-receipt", methods=["POST"])
@login_required
def scan_receipt():
    import base64
    uploaded = request.files.get("image")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "No image provided"}), 400
    image_data = base64.standard_b64encode(uploaded.read()).decode("utf-8")
    media_type = uploaded.content_type or "image/jpeg"
    results = lookup_receipt(image_data, media_type)
    if results is None:
        return jsonify({"error": "Could not parse receipt"}), 500
    return jsonify(results)


def _run_enrich_drinking_windows(user_id):
    """Background task: fill drinking_window for wines owned by user_id."""
    import anthropic, json as json_lib
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return
    client = anthropic.Anthropic(api_key=api_key)
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, wine_name, vintage, varietal, region, retail_price, unit_price, size_ml "
        f"FROM wines WHERE user_id = {p} AND (drinking_window_source IS NULL OR drinking_window_source = 'auto')",
        (user_id,)
    )
    wines = list(cur.fetchall())
    conn.close()

    batch_size = 10
    for i in range(0, len(wines), batch_size):
        batch = [w for w in wines[i:i + batch_size] if len((w["wine_name"] or "").strip()) >= 5]
        if not batch:
            continue

        def _wine_line(j, w):
            parts = [f"{w['wine_name']} ({w['vintage'] or 'NV'})"]
            if w["varietal"]:
                parts.append(w["varietal"])
            if w["region"]:
                parts.append(w["region"])
            price = w["retail_price"] or w["unit_price"]
            if price:
                parts.append(f"retail: ${price}")
            if w["size_ml"] and w["size_ml"] != 750:
                parts.append(f"size: {w['size_ml']}mL")
            return f"{j+1}. {', '.join(parts)}"

        lines = "\n".join(_wine_line(j, w) for j, w in enumerate(batch))
        prompt = (
            "For each wine below, provide the estimated drinking window. "
            "Return ONLY a JSON array with objects having 'index' (1-based) and 'window' (e.g. '2025-2032') keys.\n\n"
            f"{lines}"
        )

        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=_DRINKING_WINDOW_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            results = json_lib.loads(raw.strip())
        except Exception as e:
            batch_names = [w["wine_name"] for w in batch]
            print(f"Enrich batch parse error: {e} | wines: {batch_names}")
            continue

        passed = failed = 0
        conn = get_db()
        cur = conn.cursor()
        for r in results:
            try:
                idx = r.get("index", 0) - 1
                if not (0 <= idx < len(batch)):
                    failed += 1
                    continue
                w = batch[idx]
                vintage_val = w["vintage"] if isinstance(w["vintage"], int) else None
                window = validate_drinking_window(r.get("window") or "", vintage_val)
                if window:
                    cur.execute(f"UPDATE wines SET drinking_window = {p}, drinking_window_source = 'auto' WHERE id = {p}", (window, w["id"]))
                    passed += 1
                else:
                    failed += 1
            except Exception as item_e:
                print(f"Enrich item error: {item_e}")
                failed += 1
        conn.commit()
        conn.close()
        print(f"Enrich batch {i // batch_size + 1}: {passed} passed, {failed} failed validation")


@app.route("/wine/add-bulk", methods=["POST"])
@login_required
def add_bulk_wines():
    import json as json_lib
    from enrich_wines import extract_varietal, extract_region, extract_location, infer_wine_type, infer_size
    wines_json = request.form.get("wines_json", "[]")
    try:
        wines = json_lib.loads(wines_json)
    except Exception:
        return ("Bad request", 400)
    user_id = session["user_id"]
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    for w in wines:
        wine_name = (w.get("wine_name") or "").strip()
        if not wine_name:
            continue
        try:    vintage    = int(w["vintage"])    if w.get("vintage")    else None
        except: vintage    = None
        try:    unit_price = float(w["unit_price"]) if w.get("unit_price") else None
        except: unit_price = None
        try:    quantity   = max(1, int(w["quantity"])) if w.get("quantity") else 1
        except: quantity   = 1
        retailer   = (w.get("retailer") or "").strip() or None
        order_date = (w.get("order_date") or "").strip() or date.today().isoformat()
        total_price = round(unit_price * quantity, 2) if unit_price else None
        varietal  = extract_varietal(wine_name)
        region    = extract_region(wine_name, varietal)
        origin    = extract_location(region)
        wine_type = infer_wine_type(varietal)
        size_ml   = infer_size(wine_name)
        drinking_window = lookup_drinking_window(wine_name, vintage, varietal, region, retail_price=unit_price, size_ml=size_ml)
        dw_source = "auto" if drinking_window else None
        cur.execute(f"""INSERT INTO wines (wine_name, vintage, unit_price, total_price, quantity,
            varietal, region, origin, wine_type, size_ml, retailer, order_date, status, storage_location, drinking_window, drinking_window_source, user_id)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},'in_collection','Cellar',{p},{p},{p})""",
            (wine_name, vintage, unit_price, total_price, quantity,
             varietal, region, origin, wine_type, size_ml, retailer, order_date, drinking_window, dw_source, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for("cellar", username=session["username"]))


@app.route("/wine/enrich-drinking-windows", methods=["POST"])
@admin_required
def enrich_drinking_windows():
    import threading
    target_user_id = request.form.get("user_id", type=int) or session["user_id"]
    threading.Thread(target=_run_enrich_drinking_windows, args=(target_user_id,), daemon=True).start()
    return redirect(url_for("admin"))


@app.route("/wine/recommend", methods=["POST"])
@login_required
def recommend_wine():
    import anthropic, json as json_lib
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "API key not configured"}), 500

    user_id      = session["user_id"]
    prompt       = request.json.get("prompt", "").strip()
    storage_loc  = request.json.get("storage_location", "")  # e.g. "Cellar", "Apt", or ""
    wine_type    = request.json.get("wine_type", "")
    stickers     = request.json.get("stickers", [])

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    p = ph()
    conn = get_db()
    cur  = conn.cursor()

    query  = f"SELECT wine_name, vintage, varietal, wine_type, region, origin, color_code, drinking_window, notes, quantity FROM wines WHERE user_id = {p} AND status = 'in_collection'"
    params = [user_id]

    if storage_loc:
        query += f" AND storage_location = {p}"
        params.append(storage_loc)
    if wine_type:
        query += f" AND wine_type = {p}"
        params.append(wine_type)
    if stickers:
        placeholders = ",".join([p] * len(stickers))
        query += f" AND color_code IN ({placeholders})"
        params.extend(stickers)

    query += " ORDER BY RANDOM() LIMIT 100" if is_postgres() else " ORDER BY RANDOM() LIMIT 100"

    cur.execute(query, params)
    wines = cur.fetchall()
    conn.close()

    if not wines:
        return jsonify({"error": "No wines match your filters."}), 200

    sticker_guide = (
        "Sticker color meanings for this cellar:\n"
        "🟢 Green = everyday/forgettable, good when you just need a drink\n"
        "🟡 Yellow = solid and enjoyable, reliable everyday wine\n"
        "🟠 Orange = quality/higher-end, good for guests or when wine is part of the occasion\n"
        "🔴 Red = very special/expensive, bring out to impress or for focused appreciation\n"
        "🔵 Blue = sentimental (gift, winery visit, travel) — orange/red quality with personal meaning\n"
        "No sticker = not yet categorized, treat as unknown quality"
    )

    wine_list = []
    for w in wines:
        parts = [w["wine_name"] or "Unknown"]
        if w["vintage"]:        parts.append(f"vintage {w['vintage']}")
        if w["varietal"]:       parts.append(w["varietal"])
        if w["wine_type"]:      parts.append(w["wine_type"])
        if w["region"]:         parts.append(w["region"])
        if w["origin"]:         parts.append(f"origin: {w['origin']}")
        if w["color_code"]:     parts.append(f"sticker: {w['color_code']}")
        if w["drinking_window"]:parts.append(f"drink: {w['drinking_window']}")
        if w["quantity"]:       parts.append(f"qty: {w['quantity']}")
        if w["notes"]:          parts.append(f"notes: {w['notes'][:80]}")
        wine_list.append(" | ".join(parts))

    cellar_text = "\n".join(f"- {w}" for w in wine_list)

    system_prompt = (
        f"{sticker_guide}\n\n"
        "You are a sommelier helping recommend wines from a personal cellar. "
        "Based on the user's description of their mood, occasion, or food, recommend 1–3 wines "
        "from the list below that best match. Be concise — one sentence per wine explaining why it fits. "
        "Return ONLY valid JSON in this format: "
        "{\"recommendations\": [{\"wine_name\": \"...\", \"vintage\": 2019, \"reason\": \"...\"}]} "
        "If vintage is unknown use null. If nothing fits well, return {\"recommendations\": [], \"message\": \"brief explanation\"}. "
        "Only recommend wines from the list provided.\n\n"
        f"Available wines ({len(wines)} bottles):\n{cellar_text}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
        system=system_prompt
    )

    raw = message.content[0].text.strip()
    try:
        data = json_lib.loads(raw)
    except Exception:
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json_lib.loads(m.group()) if m else {"error": "Could not parse response"}

    return jsonify(data)


@app.route("/wine/scan-label", methods=["POST"])
@login_required
def scan_label():
    import anthropic, base64, json as json_lib
    uploaded = request.files.get("image")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "No image provided"}), 400
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500
    image_data = base64.standard_b64encode(uploaded.read()).decode("utf-8")
    media_type = uploaded.content_type or "image/jpeg"
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": "Look at this wine label and extract information. Read all text EXACTLY as it appears on the label — do not guess or correct spelling. For varietal, location, and drinking_window, use your wine knowledge to fill them in even if not printed on the label. Return ONLY a JSON object with these exact keys (use null for anything you cannot determine):\n{\"wine_name\": \"producer + wine name exactly as written\", \"vintage\": 2019, \"region\": \"appellation + broader region when applicable, e.g. Chateauneuf-du-Pape, Rhone or Saint-Emilion, Bordeaux or just Napa Valley if no sub-appellation\", \"varietal\": \"grape variety or blend (infer from appellation if needed)\", \"wine_type\": \"one of: Red, White, Rose, Sparkling, Dessert, Fortified, Orange\", \"location\": \"country (e.g. France, Italy, USA)\", \"drinking_window\": \"estimated drinking window e.g. 2025-2032 or Now-2030\"}\nReturn only the JSON, no other text."}
            ]
        }]
    )
    try:
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json_lib.loads(raw.strip())
    except Exception as e:
        print("scan-label parse error:", e)
        print("raw response:", message.content[0].text)
        return jsonify({"error": "Could not parse AI response"}), 500
    return jsonify(result)


@app.route("/refresh", methods=["POST"])
@login_required
def refresh():
    import threading
    def run_refresh():
        from fetch_emails import fetch_emails
        from parse_emails import parse_all_emails
        from enrich_wines import enrich
        from fetch_images import fetch_all_images
        fetch_emails()
        parse_all_emails()
        enrich()
        fetch_all_images()
    t = threading.Thread(target=run_refresh, daemon=True)
    t.start()
    return redirect(url_for("cellar", username=session["username"]))


@app.route("/api/wines")
@login_required
def api_wines():
    conn = get_db()
    cur = conn.cursor()
    uid = session["user_id"]
    cur.execute(f"SELECT * FROM wines WHERE user_id = {ph()} ORDER BY order_date DESC", (uid,))
    wines = cur.fetchall()
    conn.close()
    return jsonify([dict(w) for w in wines])


@app.route("/export/csv")
@login_required
def export_csv():
    import csv, io
    conn = get_db()
    cur = conn.cursor()
    uid = session["user_id"]
    cur.execute(f"SELECT * FROM wines WHERE user_id = {ph()} ORDER BY order_date DESC", (uid,))
    wines = cur.fetchall()
    conn.close()
    output = io.StringIO()
    fields = ["id","wine_name","vintage","varietal","region","origin","wine_type",
              "unit_price","retail_price","total_price","quantity","size_ml",
              "retailer","order_date","status","storage_location","color_code","drinking_window",
              "my_rating","notes"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for w in wines:
        writer.writerow({f: w[f] if f in w.keys() else "" for f in fields})
    output.seek(0)
    from flask import Response
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=wine-collection.csv"})


@app.route("/analytics")
@login_required
def analytics():
    return redirect(url_for("user_analytics", username=session["username"]))


@app.route("/cellar/<username>/analytics")
@login_required
def user_analytics(username):
    cellar_user = get_user_by_username(username)
    if not cellar_user:
        return ("User not found", 404)
    uid = cellar_user["id"]
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT wine_type, COUNT(*) as count FROM wines WHERE user_id = {p} AND wine_type IS NOT NULL GROUP BY wine_type ORDER BY count DESC", (uid,))
    by_type = cur.fetchall()
    cur.execute(f"SELECT origin, COUNT(*) as count FROM wines WHERE user_id = {p} AND origin IS NOT NULL GROUP BY origin ORDER BY count DESC LIMIT 10", (uid,))
    by_location = cur.fetchall()
    cur.execute(f"SELECT varietal, COUNT(*) as count FROM wines WHERE user_id = {p} AND varietal IS NOT NULL GROUP BY varietal ORDER BY count DESC LIMIT 10", (uid,))
    by_varietal = cur.fetchall()
    if is_postgres():
        cur.execute(f"SELECT EXTRACT(YEAR FROM order_date::date)::text as year, SUM(total_price) as spent FROM wines WHERE user_id = {p} AND order_date IS NOT NULL GROUP BY year ORDER BY year", (uid,))
    else:
        cur.execute(f"SELECT strftime('%Y', order_date) as year, SUM(total_price) as spent FROM wines WHERE user_id = {p} AND order_date IS NOT NULL GROUP BY year ORDER BY year", (uid,))
    by_year = cur.fetchall()
    cur.execute(f"SELECT status, COUNT(*) as count FROM wines WHERE user_id = {p} GROUP BY status", (uid,))
    by_status = cur.fetchall()
    conn.close()
    return render_template("analytics.html",
                           by_type=by_type, by_location=by_location,
                           by_varietal=by_varietal, by_year=by_year,
                           by_status=by_status,
                           auth_enabled=True,
                           cellar_username=username,
                           cellar_display_name=cellar_user["display_name"])


@app.route("/settings/locations", methods=["GET", "POST"])
@login_required
def settings_locations():
    uid = session["user_id"]
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name", "").strip()
            if name:
                cur.execute(f"SELECT COALESCE(MAX(sort_order), -1) + 1 as next_order FROM user_locations WHERE user_id = {p}", (uid,))
                next_order = cur.fetchone()["next_order"]
                cur.execute(f"INSERT INTO user_locations (user_id, name, sort_order) VALUES ({p},{p},{p})", (uid, name, next_order))
                conn.commit()
        elif action == "delete":
            loc_id = request.form.get("loc_id", type=int)
            if loc_id:
                cur.execute(f"DELETE FROM user_locations WHERE id = {p} AND user_id = {p}", (loc_id, uid))
                conn.commit()
        conn.close()
        return redirect(url_for("settings_locations"))
    cur.execute(f"SELECT * FROM user_locations WHERE user_id = {p} ORDER BY sort_order", (uid,))
    locations = cur.fetchall()
    conn.close()
    return render_template("settings_locations.html", locations=locations, auth_enabled=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
