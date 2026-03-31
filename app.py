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
    type_filter = request.args.get("wine_type", "")
    if type_filter:
        query += f" AND wine_type = {p}"
        params.append(type_filter)
    size_filter = request.args.get("size_ml", "")
    if size_filter:
        try:
            query += f" AND size_ml = {p}"
            params.append(int(size_filter))
        except ValueError:
            pass

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
    cur.execute("SELECT DISTINCT size_ml FROM wines WHERE size_ml IS NOT NULL ORDER BY size_ml")
    sizes = [r["size_ml"] for r in cur.fetchall()]

    conn.close()
    return render_template("index.html", wines=wines, stats=stats,
                           search=search, status_filter=status_filter,
                           varietal_filter=varietal_filter, region_filter=region_filter,
                           location_filter=location_filter, color_filter=color_filter,
                           type_filter=type_filter, size_filter=size_filter,
                           vintage_min=vintage_min, vintage_max=vintage_max,
                           price_min=price_min, price_max=price_max,
                           sort=sort, order=order,
                           varietals=varietals, regions=regions,
                           locations=locations, vintages=vintages, sizes=sizes,
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


@app.route("/wine/<int:wine_id>/region", methods=["POST"])
@edit_required
def update_region(wine_id):
    value = request.form.get("region", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET region = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/location", methods=["POST"])
@edit_required
def update_location(wine_id):
    value = request.form.get("location", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET location = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/varietal", methods=["POST"])
@edit_required
def update_varietal(wine_id):
    value = request.form.get("varietal", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET varietal = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/drinking_window", methods=["POST"])
@edit_required
def update_drinking_window(wine_id):
    value = request.form.get("drinking_window", "").strip() or None
    p = ph(); conn = get_db(); cur = conn.cursor()
    cur.execute(f"UPDATE wines SET drinking_window = {p} WHERE id = {p}", (value, wine_id))
    conn.commit(); conn.close()
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

    # Use scan results if provided, otherwise fall back to rule-based enrichment
    scan_varietal        = request.form.get("scan_varietal", "").strip() or None
    scan_region          = request.form.get("scan_region", "").strip() or None
    scan_wine_type       = request.form.get("scan_wine_type", "").strip() or None
    scan_location        = request.form.get("scan_location", "").strip() or None
    scan_drinking_window = request.form.get("scan_drinking_window", "").strip() or None
    color_code           = request.form.get("color_code", "").strip() or None

    varietal  = scan_varietal  or extract_varietal(wine_name)
    region    = scan_region    or extract_region(wine_name, varietal)
    location  = scan_location  or extract_location(region)
    wine_type = scan_wine_type or infer_wine_type(varietal)
    drinking_window = scan_drinking_window or lookup_drinking_window(wine_name, vintage, varietal, region)
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
                 retailer, order_date, status, color_code, drinking_window)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'cellar', {p}, {p})
            RETURNING id
        """, (wine_name, vintage, unit_price, total_price, quantity, notes,
              varietal, region, location, wine_type, size_ml, retailer, order_date, color_code, drinking_window))
        row = cur.fetchone()
        wine_id = row["id"] if row else None
    else:
        cur.execute(f"""
            INSERT INTO wines
                (wine_name, vintage, unit_price, total_price, quantity, notes,
                 varietal, region, location, wine_type, size_ml,
                 retailer, order_date, status, color_code, drinking_window)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 'cellar', {p}, {p})
        """, (wine_name, vintage, unit_price, total_price, quantity, notes,
              varietal, region, location, wine_type, size_ml, retailer, order_date, color_code, drinking_window))
        wine_id = cur.lastrowid

    conn.commit()
    conn.close()

    # Handle image upload or auto-fetch
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
            # Save locally
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

    return redirect(url_for("index"))


def lookup_drinking_window(wine_name, vintage, varietal, region):
    """Ask Claude for the drinking window of a single wine. Returns a string like '2025-2032' or None."""
    import anthropic, json as json_lib
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    client = anthropic.Anthropic(api_key=api_key)
    prompt = (f"What is the estimated drinking window for this wine: {wine_name} "
              f"({vintage or 'NV'}), {varietal or ''}, {region or ''}? "
              f"Return ONLY a JSON object like {{\"window\": \"2025-2032\"}} or {{\"window\": \"Now-2030\"}}. No other text.")
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        window = json_lib.loads(raw.strip()).get("window") or None
        if window:
            window = window.replace("Now", str(date.today().year))
        return window
    except Exception:
        return None


def lookup_receipt(image_data, media_type):
    """Ask Claude to extract wine info from a receipt image. Returns a list of dicts."""
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
@edit_required
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


def _run_enrich_drinking_windows():
    """Background task: fill drinking_window for all wines that are missing it."""
    import anthropic, json as json_lib
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return
    client = anthropic.Anthropic(api_key=api_key)
    p = ph()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, wine_name, vintage, varietal, region FROM wines WHERE drinking_window IS NULL OR drinking_window = ''")
    wines = list(cur.fetchall())
    conn.close()

    batch_size = 10
    for i in range(0, len(wines), batch_size):
        batch = wines[i:i + batch_size]
        lines = "\n".join(
            f"{j+1}. {w['wine_name']} ({w['vintage'] or 'NV'}), {w['varietal'] or ''}, {w['region'] or ''}"
            for j, w in enumerate(batch)
        )
        prompt = (f"For each wine below, provide the estimated drinking window. "
                  f"Return ONLY a JSON array with objects having 'index' (1-based) and 'window' (e.g. '2025-2032' or 'Now-2030') keys.\n\n{lines}")
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            results = json_lib.loads(raw.strip())
            conn = get_db()
            cur = conn.cursor()
            current_year = str(date.today().year)
            for r in results:
                idx = r.get("index", 0) - 1
                if 0 <= idx < len(batch):
                    window = (r.get("window") or "").replace("Now", current_year) or None
                    cur.execute(f"UPDATE wines SET drinking_window = {p} WHERE id = {p}",
                                (window, batch[idx]["id"]))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Enrich batch error: {e}")


@app.route("/wine/enrich-drinking-windows", methods=["POST"])
@edit_required
def enrich_drinking_windows():
    import threading
    threading.Thread(target=_run_enrich_drinking_windows, daemon=True).start()
    return redirect(url_for("index"))


@app.route("/wine/scan-label", methods=["POST"])
@edit_required
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
        # Strip markdown code fences if present
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
