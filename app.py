"""
Wine Tracker web app. Run with: python app.py
Then open http://localhost:5000 in your browser.
"""

import os
from datetime import date
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   jsonify, session, flash)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

# --- Auth configuration ---
VIEW_PASSWORD = os.environ.get("VIEW_PASSWORD")
EDIT_PASSWORD = os.environ.get("EDIT_PASSWORD")
AUTH_ENABLED = VIEW_PASSWORD is not None  # skip auth entirely in local dev

WINE_TYPES = ("Red", "White", "Rose", "Sparkling", "Dessert", "Fortified", "Orange")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    """Require at least 'view' access level."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        if session.get("access_level") not in ("view", "edit"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def edit_required(f):
    """Require 'edit' access level."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        if session.get("access_level") != "edit":
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    """Return an open DB connection — psycopg2 in prod, sqlite3 locally."""
    import db as db_module
    return db_module.get_connection()


def ph():
    """Return the SQL placeholder character for the current DB backend."""
    import db as db_module
    return db_module.get_placeholder()


def lastrowid(conn, cursor):
    """Return the last inserted row id, handling both psycopg2 and sqlite3."""
    import db as db_module
    if db_module.is_postgres():
        row = cursor.fetchone()
        if row:
            return row["id"]
        return None
    else:
        return cursor.lastrowid


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
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if EDIT_PASSWORD and password == EDIT_PASSWORD:
            session["access_level"] = "edit"
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        elif VIEW_PASSWORD and password == VIEW_PASSWORD:
            session["access_level"] = "view"
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        else:
            error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Main routes
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    conn = get_db()
    p = ph()
    search = request.args.get("q", "")
    status_filter = request.args.get("status", "")
    varietal_filter = request.args.get("varietal", "")
    region_filter = request.args.get("region", "")
    location_filter = request.args.get("location", "")
    vintage_min = request.args.get("vintage_min", "")
    vintage_max = request.args.get("vintage_max", "")
    price_min = request.args.get("price_min", "")
    price_max = request.args.get("price_max", "")
    sort = request.args.get("sort", "order_date")
    order = request.args.get("order", "desc")

    allowed_sorts = {"order_date", "wine_name", "vintage", "unit_price", "retail_price",
                     "quantity", "color_code", "region", "location", "varietal",
                     "my_rating", "wine_type", "size_ml"}
    if sort not in allowed_sorts:
        sort = "order_date"
    if order not in {"asc", "desc"}:
        order = "desc"

    query = "SELECT * FROM wines WHERE 1=1"
    params = []

    if search:
        query += f" AND (wine_name LIKE {p} OR varietal LIKE {p} OR region LIKE {p})"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if status_filter:
        query += f" AND status = {p}"
        params.append(status_filter)
    if varietal_filter:
        query += f" AND varietal = {p}"
        params.append(varietal_filter)
    if region_filter:
        query += f" AND region = {p}"
        params.append(region_filter)
    if location_filter:
        query += f" AND location = {p}"
        params.append(location_filter)
    if vintage_min:
        query += f" AND vintage >= {p}"
        params.append(int(vintage_min))
    if vintage_max:
        query += f" AND vintage <= {p}"
        params.append(int(vintage_max))
    if price_min:
        query += f" AND unit_price >= {p}"
        params.append(float(price_min))
    if price_max:
        query += f" AND unit_price <= {p}"
        params.append(float(price_max))
    color_filter = request.args.get("color_code", "")
    if color_filter:
        query += f" AND color_code = {p}"
        params.append(color_filter)

    query += f" ORDER BY {sort} {order}"

    cur = conn.cursor()
    cur.execute(query, params)
    wines = cur.fetchall()

    cur.execute("""
        SELECT
            SUM(quantity) as total_bottles,
            COUNT(DISTINCT wine_name) as unique_wines,
            SUM(total_price) as total_spent,
            SUM(CASE WHEN status='cellar' THEN quantity ELSE 0 END) as in_cellar
        FROM wines
    """)
    stats = cur.fetchone()

    cur.execute("SELECT DISTINCT varietal FROM wines WHERE varietal IS NOT NULL ORDER BY varietal")
    varietals = [r["varietal"] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT region FROM wines WHERE region IS NOT NULL ORDER BY region")
    regions = [r["region"] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT location FROM wines WHERE location IS NOT NULL ORDER BY location")
    locations = [r["location"] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT vintage FROM wines WHERE vintage IS NOT NULL ORDER BY vintage DESC")
    vintages = [r["vintage"] for r in cur.fetchall()]

    conn.close()
    return render_template("index.html", wines=wines, stats=stats,
                           search=search, status_filter=status_filter,
                           varietal_filter=varietal_filter, region_filter=region_filter,
                           location_filter=location_filter, color_filter=color_filter,
                           vintage_min=vintage_min, vintage_max=vintage_max,
                           price_min=price_min, price_max=price_max,
                           sort=sort, order=order,
                           varietals=varietals, regions=regions,
                           locations=locations, vintages=vintages,
                           access_level=session.get("access_level", "edit"),
                           auth_enabled=AUTH_ENABLED)


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
    return render_template("detail.html", wine=wine,
                           access_level=session.get("access_level", "edit"),
                           auth_enabled=AUTH_ENABLED)


@app.route("/wines/bulk-status", methods=["POST"])
@edit_required
def bulk_update_status():
    ids = request.form.getlist("ids")
    new_status = request.form.get("status")
    if new_status not in ("apt", "house", "not_shipped", "drank"):
        return ("", 400)
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    for id_ in ids:
        cur.execute(f"UPDATE wines SET status = {p} WHERE id = {p}", (new_status, id_))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/status", methods=["POST"])
@edit_required
def update_status(wine_id):
    new_status = request.form.get("status")
    if new_status in ("apt", "house", "not_shipped", "drank"):
        p = ph()
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE wines SET status = {p} WHERE id = {p}", (new_status, wine_id))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for("index"))


@app.route("/wine/<int:wine_id>/color", methods=["POST"])
@edit_required
def update_color(wine_id):
    color = request.form.get("color_code", "")
    if color in ("Red", "Blue", "Orange", "Yellow", "Green", ""):
        p = ph()
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE wines SET color_code = {p} WHERE id = {p}", (color or None, wine_id))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for("index"))


BOTTLE_SIZES = (187, 375, 750, 1000, 1500, 3000, 6000)


@app.route("/wine/<int:wine_id>/size", methods=["POST"])
@edit_required
def update_size(wine_id):
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
@edit_required
def update_type(wine_id):
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
@edit_required
def update_rating(wine_id):
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
@edit_required
def delete_wine(wine_id):
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM wines WHERE id = {p}", (wine_id,))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/retailer", methods=["POST"])
@edit_required
def update_retailer(wine_id):
    retailer = request.form.get("retailer", "").strip() or None
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE wines SET retailer = {p} WHERE id = {p}", (retailer, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/notes", methods=["POST"])
@edit_required
def update_notes(wine_id):
    notes = request.form.get("notes", "")
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE wines SET notes = {p} WHERE id = {p}", (notes, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/add", methods=["POST"])
@edit_required
def add_wine():
    from enrich_wines import extract_varietal, extract_region, extract_location, infer_wine_type, infer_size
    from fetch_images import search_and_fetch_image

    wine_name = request.form.get("wine_name", "").strip()
    if not wine_name:
        return redirect(url_for("index"))

    raw_vintage    = request.form.get("vintage", "").strip()
    raw_price      = request.form.get("unit_price", "").strip()
    raw_quantity   = request.form.get("quantity", "1").strip()
    notes          = request.form.get("notes", "").strip() or None
    retailer       = request.form.get("retailer", "").strip() or None
    raw_order_date = request.form.get("order_date", "").strip()

    try:    vintage    = int(raw_vintage)   if raw_vintage   else None
    except ValueError: vintage = None
    try:    unit_price = float(raw_price)   if raw_price     else None
    except ValueError: unit_price = None
    try:    quantity   = max(1, int(raw_quantity)) if raw_quantity else 1
    except ValueError: quantity = 1

    order_date  = raw_order_date if raw_order_date else date.today().isoformat()
    total_price = round(unit_price * quantity, 2) if unit_price else None

    varietal  = extract_varietal(wine_name)
    region    = extract_region(wine_name, varietal)
    location  = extract_location(region)
    wine_type = infer_wine_type(varietal)
    size_ml   = infer_size(wine_name)

    p = ph()
    conn = get_db()
    cur = conn.cursor()

    import db as db_module
    if db_module.is_postgres():
        cur.execute(f"""
            INSERT INTO wines
                (wine_name, vintage, unit_price, total_price, quantity, notes,
                 varietal, region, location, wine_type, size_ml,
                 retailer, order_date, status)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'cellar')
            RETURNING id
        """, (wine_name, vintage, unit_price, total_price, quantity, notes,
              varietal, region, location, wine_type, size_ml, retailer, order_date))
        row = cur.fetchone()
        wine_id = row["id"] if row else None
    else:
        cur.execute(f"""
            INSERT INTO wines
                (wine_name, vintage, unit_price, total_price, quantity, notes,
                 varietal, region, location, wine_type, size_ml,
                 retailer, order_date, status)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'cellar')
        """, (wine_name, vintage, unit_price, total_price, quantity, notes,
              varietal, region, location, wine_type, size_ml, retailer, order_date))
        wine_id = cur.lastrowid

    conn.commit()
    conn.close()

    # Handle image upload or auto-fetch
    image_url = None
    uploaded = request.files.get("image")
    if uploaded and uploaded.filename:
        # Upload to Cloudinary if configured, otherwise skip
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
        image_url = search_and_fetch_image(wine_name)

    if image_url and wine_id:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE wines SET image_url = {p} WHERE id = {p}", (image_url, wine_id))
        conn.commit()
        conn.close()

    return redirect(url_for("index"))


@app.route("/refresh", methods=["POST"])
@edit_required
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
    return redirect(url_for("index"))


@app.route("/api/wines")
@login_required
def api_wines():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM wines ORDER BY order_date DESC")
    wines = cur.fetchall()
    conn.close()
    return jsonify([dict(w) for w in wines])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
